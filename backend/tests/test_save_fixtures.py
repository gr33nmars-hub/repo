from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from casino.application.service import CasinoService
from casino.domain.blackjack import Blackjack
from casino.persistence.sqlite import PlayerRepository

FIXTURES = Path(__file__).parent / "fixtures"


class SavedDataFixtureTests(unittest.TestCase):
    def test_saved_json_columns_reject_valid_json_with_wrong_top_level_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "casino.sqlite3"
            repository = PlayerRepository(path)
            with closing(sqlite3.connect(path)) as db:
                db.execute("UPDATE profile SET rounds_json='{}' WHERE id=1")
                db.commit()

            with self.assertRaisesRegex(ValueError, "history must be a list"):
                repository.load()

            with closing(sqlite3.connect(path)) as db:
                db.execute("UPDATE profile SET rounds_json='[null]' WHERE id=1")
                db.commit()

            with self.assertRaisesRegex(ValueError, "history must be a list of objects"):
                repository.load()

            with closing(sqlite3.connect(path)) as db:
                db.execute("UPDATE profile SET rounds_json='[]', blackjack_json='[]' WHERE id=1")
                db.execute(
                    "INSERT INTO processed_requests(request_key,response_json,signature) "
                    "VALUES('bad-response','[]','test')"
                )
                db.commit()

            with self.assertRaisesRegex(ValueError, "blackjack state must be an object"):
                repository.load_blackjack()

            with self.assertRaisesRegex(ValueError, "Saved response must be an object"):
                repository.get_request_response("bad-response", signature="test")

    def test_blackjack_v2_through_v5_fixtures_restore_and_continue(self) -> None:
        for version in range(2, 6):
            with self.subTest(version=version):
                snapshot = json.loads(
                    (FIXTURES / f"blackjack-v{version}.json").read_text(encoding="utf-8")
                )
                game = Blackjack()
                game.restore_state(snapshot)

                self.assertEqual(game.hand.status, "playing")
                self.assertEqual(game.hand.bet, 20)
                self.assertEqual(game.hand.dealer_cards[0].label, "9♣")
                self.assertEqual(game.hand.hands[0].cards[0].label, "K♠")
                self.assertEqual(len(game.deck), 308)
                self.assertEqual(len(game.discarded_cards), 0)
                self.assertEqual(len(game.dump_state()["deck"]), 308)

    def test_legacy_json_fixture_imports_history_and_active_hand_with_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "player.json"
            source = FIXTURES / "player-legacy.json"
            original = source.read_bytes()
            save_path.write_bytes(original)

            with patch.dict(os.environ, {"NOIR_CASINO_SAVE_PATH": str(save_path)}):
                repository = PlayerRepository()
                session = CasinoService(repository)

            self.assertEqual(session.state()["player"]["balance"], 2480)
            self.assertEqual(session.state()["player"]["rounds_played"], 1)
            self.assertEqual(session.state()["blackjack"]["status"], "playing")
            backups = list(Path(directory).glob("player.pre-migration-*.json"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), original)
            self.assertEqual(save_path.read_bytes(), original)

    def test_corrupt_legacy_json_is_backed_up_and_rejected_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "player.json"
            original = (FIXTURES / "player-corrupt.json").read_bytes()
            save_path.write_bytes(original)

            with (
                patch.dict(os.environ, {"NOIR_CASINO_SAVE_PATH": str(save_path)}),
                self.assertRaisesRegex(RuntimeError, "безопасно импортировать"),
            ):
                PlayerRepository()

            backups = list(Path(directory).glob("player.pre-migration-*.json"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), original)
            self.assertEqual(save_path.read_bytes(), original)
            database_path = save_path.with_suffix(".sqlite3")
            with closing(sqlite3.connect(database_path)) as db:
                self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 0)
                self.assertEqual(
                    db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(), []
                )

    def test_corrupt_saved_history_is_rejected_without_rewriting_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "casino.sqlite3"
            repository = PlayerRepository(path)
            with closing(sqlite3.connect(path)) as db:
                db.execute("UPDATE profile SET rounds_json='{' WHERE id=1")
                db.commit()
                before = db.execute("SELECT balance,rounds_json FROM profile WHERE id=1").fetchone()
                ledger_before = db.execute("SELECT SUM(delta) FROM ledger").fetchone()[0]

            with self.assertRaises(json.JSONDecodeError):
                repository.load()

            with closing(sqlite3.connect(path)) as db:
                after = db.execute("SELECT balance,rounds_json FROM profile WHERE id=1").fetchone()
                self.assertEqual(tuple(after), tuple(before))
                self.assertEqual(
                    db.execute("SELECT SUM(delta) FROM ledger").fetchone()[0], ledger_before
                )

    def test_corrupt_active_blackjack_proof_is_rejected_without_rewriting_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "casino.sqlite3"
            repository = PlayerRepository(path)
            session = CasinoService(repository)
            session.start_blackjack(20, "proof-snapshot")

            with closing(sqlite3.connect(path)) as db:
                snapshot_json = db.execute(
                    "SELECT blackjack_json FROM profile WHERE id=1"
                ).fetchone()[0]
                snapshot = json.loads(snapshot_json)
                snapshot["draw_order"][0], snapshot["draw_order"][1] = (
                    snapshot["draw_order"][1],
                    snapshot["draw_order"][0],
                )
                corrupted_json = json.dumps(snapshot, ensure_ascii=False)
                db.execute("UPDATE profile SET blackjack_json=? WHERE id=1", (corrupted_json,))
                db.commit()
                profile_before = db.execute(
                    "SELECT balance,rounds_json,blackjack_json FROM profile WHERE id=1"
                ).fetchone()
                ledger_before = db.execute("SELECT SUM(delta) FROM ledger").fetchone()[0]

            with self.assertRaises(ValueError):
                CasinoService(PlayerRepository(path))

            with closing(sqlite3.connect(path)) as db:
                profile_after = db.execute(
                    "SELECT balance,rounds_json,blackjack_json FROM profile WHERE id=1"
                ).fetchone()
                self.assertEqual(tuple(profile_after), tuple(profile_before))
                self.assertEqual(
                    db.execute("SELECT SUM(delta) FROM ledger").fetchone()[0], ledger_before
                )

    def test_new_one_shot_round_history_must_match_its_ledger_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "casino.sqlite3"
            session = CasinoService(PlayerRepository(path))
            session.play("roulette", 10, "red", "linked-round")

            with closing(sqlite3.connect(path)) as db:
                saved = json.loads(
                    db.execute("SELECT rounds_json FROM profile WHERE id=1").fetchone()[0]
                )
                self.assertTrue(saved[0]["round_id"])
                self.assertEqual(
                    db.execute(
                        "SELECT COUNT(*) FROM ledger WHERE round_id=?", (saved[0]["round_id"],)
                    ).fetchone()[0],
                    2,
                )
                saved[0]["payout"] += 1
                db.execute("UPDATE profile SET rounds_json=? WHERE id=1", (json.dumps(saved),))
                db.commit()

            with self.assertRaisesRegex(RuntimeError, "history does not match"):
                CasinoService(PlayerRepository(path))

            with closing(sqlite3.connect(path)) as db:
                saved[0]["payout"] -= 1
                db.execute("UPDATE profile SET rounds_json='[]' WHERE id=1")
                db.commit()

            with self.assertRaisesRegex(RuntimeError, "history does not match"):
                CasinoService(PlayerRepository(path))


if __name__ == "__main__":
    unittest.main()
