from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import pytest
from casino.application.service import CasinoService
from casino.domain.blackjack import Blackjack
from casino.persistence.blackjack_codec import BlackjackStateCodec
from casino.persistence.sqlite import PlayerRepository

FIXTURES = Path(__file__).parent / "fixtures"


def encode_blackjack_state(game: Blackjack) -> dict | None:
    return BlackjackStateCodec.encode(game.snapshot())


def restore_blackjack_state(game: Blackjack, state: dict | None) -> None:
    game.restore_snapshot(BlackjackStateCodec.decode(state))


def test_saved_json_columns_reject_valid_json_with_wrong_top_level_shape(
    tmp_path: Path,
) -> None:
    path = tmp_path / "casino.sqlite3"
    repository = PlayerRepository(path)
    with closing(sqlite3.connect(path)) as db:
        db.execute("UPDATE profile SET rounds_json='{}' WHERE id=1")
        db.commit()

    with pytest.raises(ValueError, match="history must be a list"):
        repository.load()

    with closing(sqlite3.connect(path)) as db:
        db.execute("UPDATE profile SET rounds_json='[null]' WHERE id=1")
        db.commit()

    with pytest.raises(ValueError, match="history must be a list of objects"):
        repository.load()

    with closing(sqlite3.connect(path)) as db:
        db.execute("UPDATE profile SET rounds_json='[]', blackjack_json='[]' WHERE id=1")
        db.execute(
            "INSERT INTO processed_requests(request_key,response_json,signature) "
            "VALUES('bad-response','[]','test')"
        )
        db.commit()

    with pytest.raises(ValueError, match="blackjack state must be an object"):
        repository.load_blackjack()

    with pytest.raises(ValueError, match="Saved response must be an object"):
        repository.get_request_response("bad-response", signature="test")


@pytest.mark.parametrize("version", range(2, 6))
def test_blackjack_v2_through_v5_fixtures_restore_and_continue(version: int) -> None:
    snapshot = json.loads((FIXTURES / f"blackjack-v{version}.json").read_text(encoding="utf-8"))
    game = Blackjack()
    restore_blackjack_state(game, snapshot)

    assert game.hand.status == "playing"
    assert game.hand.bet == 20
    assert game.hand.dealer_cards[0].label == "9♣"
    assert game.hand.hands[0].cards[0].label == "K♠"
    assert game._shoe.remaining_count == 308
    assert len(game._shoe.discarded_cards) == 0
    assert len(encode_blackjack_state(game)["deck"]) == 308


def test_legacy_json_fixture_imports_history_and_active_hand_with_backup(tmp_path: Path) -> None:
    save_path = tmp_path / "player.json"
    original = (FIXTURES / "player-legacy.json").read_bytes()
    save_path.write_bytes(original)

    with patch.dict(os.environ, {"ASTORIA_CASINO_SAVE_PATH": str(save_path)}):
        repository = PlayerRepository()
        session = CasinoService(repository)

    assert session.state()["player"]["balance"] == 2480
    assert session.state()["player"]["rounds_played"] == 1
    assert session.state()["blackjack"]["status"] == "playing"
    backups = list(tmp_path.glob("player.pre-migration-*.json"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == original
    assert save_path.read_bytes() == original


def test_corrupt_legacy_json_is_backed_up_and_rejected_without_overwrite(
    tmp_path: Path,
) -> None:
    save_path = tmp_path / "player.json"
    original = (FIXTURES / "player-corrupt.json").read_bytes()
    save_path.write_bytes(original)

    with (
        patch.dict(os.environ, {"ASTORIA_CASINO_SAVE_PATH": str(save_path)}),
        pytest.raises(RuntimeError, match="безопасно импортировать"),
    ):
        PlayerRepository()

    backups = list(tmp_path.glob("player.pre-migration-*.json"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == original
    assert save_path.read_bytes() == original
    database_path = save_path.with_suffix(".sqlite3")
    with closing(sqlite3.connect(database_path)) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 0
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []


def test_corrupt_saved_history_is_rejected_without_rewriting_database(tmp_path: Path) -> None:
    path = tmp_path / "casino.sqlite3"
    repository = PlayerRepository(path)
    with closing(sqlite3.connect(path)) as db:
        db.execute("UPDATE profile SET rounds_json='{' WHERE id=1")
        db.commit()
        before = db.execute("SELECT balance,rounds_json FROM profile WHERE id=1").fetchone()
        ledger_before = db.execute("SELECT SUM(delta) FROM ledger").fetchone()[0]

    with pytest.raises(json.JSONDecodeError):
        repository.load()

    with closing(sqlite3.connect(path)) as db:
        after = db.execute("SELECT balance,rounds_json FROM profile WHERE id=1").fetchone()
        assert tuple(after) == tuple(before)
        assert db.execute("SELECT SUM(delta) FROM ledger").fetchone()[0] == ledger_before


def test_corrupt_active_blackjack_proof_is_rejected_without_rewriting_database(
    tmp_path: Path,
) -> None:
    path = tmp_path / "casino.sqlite3"
    repository = PlayerRepository(path)
    session = CasinoService(repository)
    session.start_blackjack(20, "proof-snapshot")

    with closing(sqlite3.connect(path)) as db:
        snapshot_json = db.execute("SELECT blackjack_json FROM profile WHERE id=1").fetchone()[0]
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

    with pytest.raises(ValueError):
        CasinoService(PlayerRepository(path))

    with closing(sqlite3.connect(path)) as db:
        profile_after = db.execute(
            "SELECT balance,rounds_json,blackjack_json FROM profile WHERE id=1"
        ).fetchone()
        assert tuple(profile_after) == tuple(profile_before)
        assert db.execute("SELECT SUM(delta) FROM ledger").fetchone()[0] == ledger_before


def test_new_one_shot_round_history_must_match_its_ledger_entries(tmp_path: Path) -> None:
    path = tmp_path / "casino.sqlite3"
    session = CasinoService(PlayerRepository(path))
    session.play("roulette", 10, "red", "linked-round")

    with closing(sqlite3.connect(path)) as db:
        saved = json.loads(db.execute("SELECT rounds_json FROM profile WHERE id=1").fetchone()[0])
        assert saved[0]["round_id"]
        assert (
            db.execute(
                "SELECT COUNT(*) FROM ledger WHERE round_id=?", (saved[0]["round_id"],)
            ).fetchone()[0]
            == 2
        )
        saved[0]["payout"] += 1
        db.execute("UPDATE profile SET rounds_json=? WHERE id=1", (json.dumps(saved),))
        db.commit()

    with pytest.raises(RuntimeError, match="history does not match"):
        CasinoService(PlayerRepository(path))

    with closing(sqlite3.connect(path)) as db:
        db.execute("UPDATE profile SET rounds_json='[]' WHERE id=1")
        db.commit()

    with pytest.raises(RuntimeError, match="history does not match"):
        CasinoService(PlayerRepository(path))
