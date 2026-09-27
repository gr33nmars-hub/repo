from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from casino.process_lock import BackendProcessLock
from casino.recovery import backup_database, restore_database, validate_database
from casino.session import CasinoSession
from casino.storage import PlayerRepository


class RecoveryTests(unittest.TestCase):
    @staticmethod
    def _create_schema_fixture(path: Path, version: int) -> None:
        fixture_path = Path(__file__).parent / "fixtures" / f"save-v{version}.sql"
        with closing(sqlite3.connect(path)) as db:
            db.executescript(fixture_path.read_text(encoding="utf-8"))
            db.commit()

    def test_schema_fixtures_upgrade_with_verified_pre_migration_backups(self) -> None:
        for version in range(4):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "casino.sqlite3"
                self._create_schema_fixture(path, version)

                PlayerRepository(path)

                with closing(sqlite3.connect(path)) as db:
                    self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 3)
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

                backups = list(Path(directory).glob("casino.pre-migration-*.sqlite3"))
                self.assertEqual(len(backups), 1 if version < 3 else 0)
                if version < 3:
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
                ledger_entries=[("test_setup_adjustment", -2500)],
                response={},
            )
            session = CasinoSession(repository)
            session.refill("refill")

            backup_database(source, backup)
            validate_database(backup)
            restore_database(backup, restored_path)

            restored = CasinoSession(PlayerRepository(restored_path))
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
                CasinoSession(PlayerRepository(destination)).state()["player"]["balance"], 2500
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
                CasinoSession(PlayerRepository(destination)).state()["player"]["balance"], 2500
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
                CasinoSession(PlayerRepository(destination)).state()["player"]["balance"], 2500
            )


if __name__ == "__main__":
    unittest.main()
