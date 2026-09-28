from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from casino.application.service import CasinoService
from casino.domain.ledger import LedgerMovement
from casino.persistence.codecs import CasinoSaveCodec
from casino.persistence.migrations import SQLiteSchemaMigrator
from casino.persistence.sqlite import PlayerRepository
from casino.process_lock import BackendProcessLock
from casino.recovery import backup_database, restore_database, validate_database


class RecoveryTests(unittest.TestCase):
    @staticmethod
    def _create_schema_fixture(path: Path, version: int) -> None:
        fixture_path = Path(__file__).parent / "fixtures" / f"save-v{version}.sql"
        with closing(sqlite3.connect(path)) as db:
            db.executescript(fixture_path.read_text(encoding="utf-8"))
            db.commit()

    def test_schema_fixtures_upgrade_with_verified_pre_migration_backups(self) -> None:
        for version in range(5):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "casino.sqlite3"
                self._create_schema_fixture(path, version)

                PlayerRepository(path)

                with closing(sqlite3.connect(path)) as db:
                    self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 4)
                    self.assertEqual(db.execute("SELECT balance FROM profile").fetchone()[0], 2490)
                    self.assertEqual(
                        db.execute("SELECT SUM(delta) FROM ledger").fetchone()[0], 2490
                    )
                    self.assertEqual(
                        db.execute(
                            "SELECT signature FROM processed_requests WHERE request_key='old-key'"
                        ).fetchone()[0],
                        None,
                    )
                    self.assertIsNone(
                        db.execute(
                            "SELECT reason FROM ledger WHERE request_key='legacy-loss'"
                        ).fetchone()[0]
                    )

                backups = list(Path(directory).glob("casino.pre-migration-*.sqlite3"))
                self.assertEqual(len(backups), 1 if version < 4 else 0)
                if version < 4:
                    with closing(sqlite3.connect(backups[0])) as backup:
                        self.assertEqual(backup.execute("PRAGMA quick_check").fetchone()[0], "ok")
                        self.assertEqual(
                            backup.execute("PRAGMA user_version").fetchone()[0], version
                        )

    def test_failed_schema_migration_rolls_back_and_preserves_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "casino.sqlite3"
            self._create_schema_fixture(path, 0)

            with (
                patch.object(
                    PlayerRepository,
                    "_ensure_ledger_baseline",
                    side_effect=RuntimeError("injected migration failure"),
                ),
                self.assertRaisesRegex(RuntimeError, "injected migration failure"),
            ):
                PlayerRepository(path)

            backups = list(Path(directory).glob("casino.pre-migration-*.sqlite3"))
            self.assertEqual(len(backups), 1)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 0)
                self.assertNotIn(
                    "signature",
                    {row[1] for row in db.execute("PRAGMA table_info(processed_requests)")},
                )
                self.assertEqual(db.execute("SELECT balance FROM profile").fetchone()[0], 2490)
            with closing(sqlite3.connect(backups[0])) as backup:
                self.assertEqual(backup.execute("PRAGMA user_version").fetchone()[0], 0)

    def test_each_schema_migration_step_rolls_back_to_the_source_fixture(self) -> None:
        steps = [
            "v1.profile",
            "v1.ledger",
            "v1.processed_requests",
            "v1.metadata",
            "v1.user_version",
            "v2.signature",
            "v2.user_version",
            "v3.round_id",
            "v3.user_version",
            "v4.reason",
            "v4.user_version",
            "final.user_version",
        ]
        original_migrate = SQLiteSchemaMigrator.migrate
        for failed_step in steps:
            with self.subTest(step=failed_step), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "casino.sqlite3"
                self._create_schema_fixture(path, 0)

                def inject_failure(db, version):
                    def after_step(step: str) -> None:
                        if step == failed_step:
                            raise RuntimeError(f"injected at {step}")

                    original_migrate(db, version, after_step=after_step)

                with (
                    patch.object(SQLiteSchemaMigrator, "migrate", side_effect=inject_failure),
                    self.assertRaisesRegex(RuntimeError, f"injected at {failed_step}"),
                ):
                    PlayerRepository(path)

                with closing(sqlite3.connect(path)) as db:
                    self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 0)
                    self.assertEqual(db.execute("SELECT balance FROM profile").fetchone()[0], 2490)
                    self.assertNotIn(
                        "signature",
                        {row[1] for row in db.execute("PRAGMA table_info(processed_requests)")},
                    )
                    ledger_columns = {row[1] for row in db.execute("PRAGMA table_info(ledger)")}
                    self.assertNotIn("round_id", ledger_columns)
                    self.assertNotIn("reason", ledger_columns)

    def test_legacy_json_is_backed_up_before_import(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            legacy_path = Path(directory) / "player.json"
            original = b'{"name":"Guest","balance":1200,"rounds":[]}'
            legacy_path.write_bytes(original)
            with patch.dict("os.environ", {"NOIR_CASINO_SAVE_PATH": str(legacy_path)}):
                repository = PlayerRepository()

            backups = list(Path(directory).glob("player.pre-migration-*.json"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), original)
            self.assertEqual(repository.load().balance, 1200)

    def test_backup_and_restore_preserve_profile_and_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "casino.sqlite3"
            backup = root / "casino-backup.sqlite3"
            restored_path = root / "restored.sqlite3"
            repository = PlayerRepository(source)
            player = repository.load()
            player.balance = 0
            repository.save(
                player,
                request_key="test-adjust-balance",
                signature="test.adjust-balance",
                ledger_entries=[LedgerMovement.adjustment(-2500, "test fixture balance")],
                response={},
            )
            session = CasinoService(repository)
            session.refill("refill")

            backup_database(source, backup)
            validate_database(backup)
            restore_database(backup, restored_path)

            restored = CasinoService(PlayerRepository(restored_path))
            self.assertEqual(restored.state()["player"]["balance"], 1000)
            db = sqlite3.connect(restored_path)
            try:
                self.assertEqual(db.execute("SELECT SUM(delta) FROM ledger").fetchone()[0], 1000)
            finally:
                db.close()

    def test_invalid_restore_keeps_existing_destination_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "bad.sqlite3"
            destination = root / "destination.sqlite3"
            PlayerRepository(source)
            PlayerRepository(destination)

            db = sqlite3.connect(source)
            try:
                db.execute("UPDATE profile SET rounds_json='{' WHERE id=1")
                db.commit()
            finally:
                db.close()

            with self.assertRaises((ValueError, RuntimeError)):
                restore_database(source, destination, replace=True)
            self.assertEqual(
                CasinoService(PlayerRepository(destination)).state()["player"]["balance"], 2500
            )

    def test_restore_backs_up_corrupted_destination_before_replacing_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "good.sqlite3"
            destination = root / "destination.sqlite3"
            PlayerRepository(source)
            PlayerRepository(destination)
            db = sqlite3.connect(destination)
            try:
                db.execute("UPDATE ledger SET balance_after=balance_after+1 WHERE id=0")
                db.commit()
            finally:
                db.close()

            restore_database(source, destination, replace=True)

            backups = list(root.glob("destination.pre-restore-*.sqlite3"))
            self.assertEqual(len(backups), 1)
            db = sqlite3.connect(backups[0])
            try:
                self.assertEqual(db.execute("PRAGMA quick_check").fetchone()[0], "ok")
            finally:
                db.close()
            self.assertEqual(
                CasinoService(PlayerRepository(destination)).state()["player"]["balance"], 2500
            )

    def test_restore_preserves_committed_wal_and_refuses_a_pinned_reader(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.sqlite3"
            destination = root / "destination.sqlite3"
            source_state = CasinoService(PlayerRepository(source)).state()
            PlayerRepository(destination)
            writer = sqlite3.connect(destination)
            writer.execute("PRAGMA journal_mode = WAL")
            writer.execute(
                "UPDATE metadata SET value=? WHERE key='slots_server_seed'",
                ("ab" * 32,),
            )
            writer.commit()
            reader = sqlite3.connect(destination)
            reader.execute("BEGIN")
            self.assertEqual(
                reader.execute(
                    "SELECT value FROM metadata WHERE key='slots_server_seed'"
                ).fetchone()[0],
                "ab" * 32,
            )
            writer.close()

            with self.assertRaisesRegex(RuntimeError, "WAL is busy"):
                restore_database(source, destination, replace=True)

            reader.close()
            restore_database(source, destination, replace=True)
            restored = CasinoService(PlayerRepository(destination)).state()
            self.assertEqual(
                restored["slots_server_seed_hash"], source_state["slots_server_seed_hash"]
            )
            backups = list(root.glob("destination.pre-restore-*.sqlite3"))
            self.assertEqual(len(backups), 2)
            with closing(sqlite3.connect(backups[0])) as db:
                self.assertEqual(
                    db.execute(
                        "SELECT value FROM metadata WHERE key='slots_server_seed'"
                    ).fetchone()[0],
                    "ab" * 32,
                )

    def test_restore_refuses_to_replace_a_save_owned_by_the_backend(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "backup.sqlite3"
            destination = root / "casino.sqlite3"
            PlayerRepository(source)
            PlayerRepository(destination)

            with BackendProcessLock(destination):
                with self.assertRaisesRegex(RuntimeError, "owns this save"):
                    restore_database(source, destination, replace=True)
                attempt = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        "import sys; from pathlib import Path; "
                        "from casino.process_lock import BackendProcessLock; "
                        "lock = BackendProcessLock(Path(sys.argv[1])); "
                        "\ntry: lock.acquire()\nexcept RuntimeError: sys.exit(0)\n"
                        "sys.exit(1)",
                        str(destination),
                    ],
                    cwd=Path(__file__).parents[1],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(attempt.returncode, 0, attempt.stderr)

            self.assertEqual(
                CasinoService(PlayerRepository(destination)).state()["player"]["balance"], 2500
            )

    def test_two_processes_commit_distinct_game_actions_without_lost_updates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shared.sqlite3"
            PlayerRepository(path)
            child_code = (
                "import sys; from pathlib import Path; "
                "from casino.domain.models import GameResult; "
                "from casino.application.service import CasinoService; "
                "from casino.persistence.sqlite import PlayerRepository; "
                "path=Path(sys.argv[1]); key=sys.argv[2]; "
                "session=CasinoService(PlayerRepository(path)); "
                "session.games['slots'].play_at_stops="
                "lambda bet,stops: GameResult('slots','Слоты','Проигрыш',bet,0,'fixture loss'); "
                "session.play('slots',10,'',key)"
            )
            children = [
                subprocess.Popen(
                    [sys.executable, "-c", child_code, str(path), key],
                    cwd=Path(__file__).parents[1],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for key in ("process-a", "process-b")
            ]
            for child in children:
                stdout, stderr = child.communicate(timeout=30)
                self.assertEqual(child.returncode, 0, f"stdout={stdout}\nstderr={stderr}")

            restored = CasinoService(PlayerRepository(path))
            self.assertEqual(restored.state()["player"]["balance"], 2480)
            self.assertEqual(restored.state()["player"]["rounds_played"], 2)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute("SELECT SUM(delta) FROM ledger").fetchone()[0], 2480)
                self.assertEqual(
                    db.execute("SELECT COUNT(*) FROM processed_requests").fetchone()[0], 2
                )

    def test_two_processes_retry_same_action_and_commit_one_settlement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shared.sqlite3"
            PlayerRepository(path)
            child_code = (
                "import sys; from pathlib import Path; "
                "from casino.domain.models import GameResult; "
                "from casino.application.service import CasinoService; "
                "from casino.persistence.sqlite import PlayerRepository; "
                "path=Path(sys.argv[1]); key=sys.argv[2]; "
                "session=CasinoService(PlayerRepository(path)); "
                "session.games['slots'].play_at_stops="
                "lambda bet,stops: GameResult('slots','Слоты','Проигрыш',bet,0,'fixture loss'); "
                "session.play('slots',10,'',key)"
            )
            children = [
                subprocess.Popen(
                    [sys.executable, "-c", child_code, str(path), "same-process-request"],
                    cwd=Path(__file__).parents[1],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for _ in range(2)
            ]
            for child in children:
                stdout, stderr = child.communicate(timeout=30)
                self.assertEqual(child.returncode, 0, f"stdout={stdout}\nstderr={stderr}")

            state = CasinoService(PlayerRepository(path)).state()
            self.assertEqual(state["player"]["balance"], 2490)
            self.assertEqual(state["player"]["rounds_played"], 1)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(
                    db.execute(
                        "SELECT COUNT(*) FROM processed_requests WHERE request_key=?",
                        ("same-process-request",),
                    ).fetchone()[0],
                    1,
                )
                self.assertEqual(
                    db.execute(
                        "SELECT COUNT(*) FROM ledger WHERE request_key=?",
                        ("same-process-request",),
                    ).fetchone()[0],
                    2,
                )

    def test_sql_failure_rolls_back_profile_ledger_and_cached_response(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rollback.sqlite3"
            repository = PlayerRepository(path)
            session = CasinoService(repository)
            before_state = session.state()
            with closing(sqlite3.connect(path)) as db:
                db.execute(
                    "CREATE TRIGGER fail_selected_ledger_insert "
                    "BEFORE INSERT ON ledger WHEN NEW.request_key='sql-failure' "
                    "BEGIN SELECT RAISE(ABORT, 'injected ledger insert failure'); END"
                )
                db.commit()

            with self.assertRaisesRegex(sqlite3.IntegrityError, "injected ledger insert failure"):
                session.play("roulette", 10, "red", "sql-failure")

            self.assertEqual(session.state(), before_state)
            self.assertIsNone(repository.get_request_response("sql-failure"))
            reloaded = CasinoService(PlayerRepository(path))
            self.assertEqual(reloaded.state()["player"], before_state["player"])
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(
                    db.execute(
                        "SELECT COUNT(*) FROM ledger WHERE request_key='sql-failure'"
                    ).fetchone()[0],
                    0,
                )
                self.assertEqual(
                    db.execute(
                        "SELECT COUNT(*) FROM processed_requests WHERE request_key='sql-failure'"
                    ).fetchone()[0],
                    0,
                )

    def test_history_serialization_failure_rolls_back_game_state_and_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "serialization-failure.sqlite3"
            repository = PlayerRepository(path)
            session = CasinoService(repository)
            before_state = session.state()
            with (
                patch.object(
                    CasinoSaveCodec,
                    "encode_history",
                    side_effect=ValueError("injected history serialization failure"),
                ),
                self.assertRaisesRegex(ValueError, "history serialization"),
            ):
                session.play("roulette", 10, "red", "serialization-failure")

            self.assertEqual(session.state(), before_state)
            self.assertEqual(CasinoService(PlayerRepository(path)).state(), before_state)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(
                    db.execute(
                        "SELECT COUNT(*) FROM processed_requests WHERE request_key=?",
                        ("serialization-failure",),
                    ).fetchone()[0],
                    0,
                )

    def test_commit_failure_rolls_back_profile_ledger_and_cached_response(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "commit-failure.sqlite3"
            repository = PlayerRepository(path)
            session = CasinoService(repository)
            before_state = session.state()
            fail_commit = True
            original_connect = repository._connect

            class CommitFaultConnection:
                def __init__(self, connection: sqlite3.Connection) -> None:
                    self.connection = connection

                def __getattr__(self, name: str):
                    return getattr(self.connection, name)

                def commit(self) -> None:
                    nonlocal fail_commit
                    if fail_commit:
                        fail_commit = False
                        raise sqlite3.OperationalError("injected commit failure")
                    self.connection.commit()

            with (
                patch.object(
                    repository,
                    "_connect",
                    side_effect=lambda: CommitFaultConnection(original_connect()),
                ),
                self.assertRaisesRegex(sqlite3.OperationalError, "commit failure"),
            ):
                session.play("roulette", 10, "red", "commit-failure")

            self.assertEqual(session.state(), before_state)
            self.assertEqual(CasinoService(PlayerRepository(path)).state(), before_state)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(
                    db.execute(
                        "SELECT COUNT(*) FROM processed_requests WHERE request_key=?",
                        ("commit-failure",),
                    ).fetchone()[0],
                    0,
                )


if __name__ == "__main__":
    unittest.main()
