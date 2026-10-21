from __future__ import annotations

import json
import random
import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
from pathlib import Path

import pytest
from casino.application.errors import IdempotencyConflict
from casino.application.queries import blackjack_view
from casino.application.service import CasinoService
from casino.domain.blackjack import Blackjack, BlackjackRules
from casino.domain.core import GameRules
from casino.domain.games import RouletteRules, SlotRules
from casino.domain.ledger import LedgerEntryType, LedgerMovement
from casino.domain.models import Card, GameResult, Player
from casino.domain.shoe import Shoe
from casino.domain.slot_fairness import seed_hash
from casino.persistence.blackjack_codec import BlackjackStateCodec
from casino.persistence.codecs import CasinoSaveCodec
from casino.persistence.sqlite import PlayerRepository


def encode_blackjack_state(game: Blackjack) -> dict | None:
    return BlackjackStateCodec.encode(game.snapshot())


def restore_blackjack_state(game: Blackjack, state: dict | None) -> None:
    game.restore_snapshot(BlackjackStateCodec.decode(state))


def rig(game: Blackjack, draws: list[tuple[str, str]]) -> None:
    shoe = [Card(rank, suit) for _ in range(6) for suit in game.suits for rank in game.ranks]
    selected = []
    for rank, suit in draws:
        card = next(card for card in shoe if card.rank == rank and card.suit == suit)
        shoe.remove(card)
        selected.append(card)
    game._shoe = Shoe(shoe + list(reversed(selected)))


def rig_legacy_service(service: CasinoService, draws: list[tuple[str, str]]) -> None:
    """Use a rigged legacy shoe for application tests unrelated to fairness."""
    rig(service.blackjack, draws)
    fair_start = service.blackjack.start

    def start_from_rig(bet: int, **_: object):
        return fair_start(bet)

    service.blackjack.start = start_from_rig  # type: ignore[method-assign]


def test_profile_decoder_rejects_coercion_and_invalid_history() -> None:
    with pytest.raises(ValueError, match="balance"):
        CasinoSaveCodec.decode_player({"balance": "-5"})
    with pytest.raises(ValueError, match="bet and payout"):
        CasinoSaveCodec.decode_result(
            {
                "game_id": "slots",
                "game_name": "Слоты",
                "message": "Тест",
                "bet": "10",
                "payout": 0,
            }
        )


def test_bet_must_be_exactly_representable_and_rules_reject_invalid_types() -> None:
    game = Blackjack()
    with pytest.raises(ValueError):
        game.start(21)
    with pytest.raises(ValueError):
        game.start(True)
    with pytest.raises(ValueError):
        BlackjackRules(decks=True)
    for invalid_rules in (
        lambda: GameRules(minimum_bet=True),
        lambda: GameRules(maximum_bet=False),
        lambda: RouletteRules(color_return_multiplier=True),
        lambda: SlotRules(pair_multiplier=True),
        lambda: SlotRules(triples=(("7️⃣", True),)),
        lambda: SlotRules(reels=(("🍒",), ("🍒",), [])),
    ):
        with pytest.raises(ValueError):
            invalid_rules()


def test_natural_is_three_to_two_and_split_twenty_one_is_not_natural() -> None:
    game = Blackjack()
    rig(game, [("A", "♠"), ("9", "♣"), ("K", "♠"), ("7", "♣")])
    game.start(20)
    assert game.result().payout == 50
    assert game.hand.status == "won"

    game = Blackjack()
    rig(
        game,
        [("A", "♠"), ("6", "♣"), ("A", "♥"), ("10", "♣"), ("K", "♠"), ("9", "♥"), ("5", "♦")],
    )
    game.start(20)
    game.act("split", balance=1000)
    assert game.hand.status == "lost"
    assert game.result().payout == 20


def test_insurance_pays_two_to_one_and_dealer_peeks() -> None:
    game = Blackjack()
    rig(game, [("8", "♠"), ("A", "♣"), ("8", "♥"), ("K", "♣")])
    game.start(20)
    assert game.hand.status == "insurance"
    assert blackjack_view(game, 10)["available_actions"] == ["insurance", "decline_insurance"]
    game.act("insurance", balance=1000)
    assert game.hand.status == "push"
    assert game.result().bet == 30
    assert game.result().payout == 30


def test_surrender_returns_half_and_is_loss() -> None:
    game = Blackjack()
    rig(game, [("10", "♠"), ("9", "♣"), ("6", "♥"), ("7", "♣")])
    game.start(20)
    game.act("surrender", balance=1000)
    assert game.hand.status == "lost"
    assert game.hand.hands[0].status == "surrendered"
    assert game.result().payout == 10


def test_domain_transition_reports_extra_stake_and_settlement() -> None:
    game = Blackjack()
    rig(
        game,
        [("8", "♠"), ("6", "♣"), ("8", "♥"), ("10", "♣"), ("2", "♦"), ("3", "♦")],
    )
    game.start(20)
    split = game.act("split", balance=100)
    assert split.ledger_entries == (LedgerMovement(LedgerEntryType.BLACKJACK_SPLIT_STAKE, -20),)
    assert split.result is None
    assert len(game.hand.hands) == 2

    surrender_game = Blackjack()
    rig(surrender_game, [("10", "♠"), ("9", "♣"), ("6", "♥"), ("7", "♣")])
    surrender_game.start(20)
    surrender = surrender_game.act("surrender", balance=100)
    assert surrender.ledger_entries == (LedgerMovement(LedgerEntryType.BLACKJACK_PAYOUT, 10),)
    assert surrender.result.payout == 10


def test_ten_upcard_peeks_before_actions_and_split_aces_get_one_card() -> None:
    game = Blackjack()
    rig(game, [("8", "♠"), ("K", "♣"), ("8", "♥"), ("A", "♣")])
    game.start(20)
    assert game.hand.status == "lost"
    assert game.available_actions() == []

    game = Blackjack()
    rig(
        game,
        [("A", "♠"), ("6", "♣"), ("A", "♥"), ("10", "♣"), ("K", "♠"), ("9", "♥"), ("5", "♦")],
    )
    game.start(20)
    game.act("split", balance=1000)
    assert [len(h.cards) for h in game.hand.hands] == [2, 2]
    assert game.available_actions() == []
    assert game.hand.hands[0].status == "push"


def test_split_double_and_dealer_stands_soft_seventeen() -> None:
    game = Blackjack()
    rig(
        game,
        [("8", "♠"), ("A", "♣"), ("8", "♥"), ("6", "♣"), ("3", "♠"), ("10", "♦"), ("2", "♥")],
    )
    game.start(20)
    game.act("decline_insurance", balance=1000)
    game.act("split", balance=1000)
    assert len(game.hand.hands) == 2
    assert len(game.hand.hands[1].cards) == 1
    game.act("double", balance=1000)
    assert game.hand.active_hand_index == 1
    assert game.hand.hands[0].bet == 40
    game.act("stand", balance=1000)
    assert game.score(game.hand.dealer_cards) == 17
    assert len(game.hand.dealer_cards) == 2
    assert game.result().bet == 60


def test_ten_value_pair_and_sequential_split_dealing() -> None:
    game = Blackjack()
    rig(
        game,
        [("10", "♠"), ("9", "♣"), ("K", "♥"), ("8", "♣"), ("A", "♠"), ("2", "♥"), ("4", "♦")],
    )
    game.start(20)
    assert "split" in game.available_actions()
    game.act("split", balance=1000)
    assert [len(h.cards) for h in game.hand.hands] == [2, 2]
    assert game.hand.active_hand_index == 1
    assert game.hand.hands[0].cards[-1].rank == "A"
    restored = Blackjack()
    restore_blackjack_state(restored, encode_blackjack_state(game))
    restored.act("stand", balance=1000)
    assert restored.hand.hands[1].cards[-1].rank == "2"


def test_resplitting_reaches_the_configured_four_hand_limit() -> None:
    game = Blackjack()
    rig(
        game,
        [
            ("8", "♠"),
            ("6", "♣"),
            ("8", "♥"),
            ("10", "♦"),
            ("8", "♣"),
            ("2", "♠"),
            ("8", "♦"),
            ("3", "♣"),
        ],
    )
    game.start(20)
    game.act("split", balance=1000)
    assert "split" in game.available_actions()

    game.act("split", balance=1000)
    assert len(game.hand.hands) == 3
    game.act("stand", balance=1000)
    assert game.hand.active_hand_index == 1
    assert [card.rank for card in game.hand.hands[1].cards] == ["8", "8"]
    assert "split" in game.available_actions()

    game.act("split", balance=1000)
    assert len(game.hand.hands) == 4
    assert "split" not in game.available_actions()


def test_split_twenty_one_stands_and_never_gets_natural_blackjack_payout() -> None:
    game = Blackjack()
    rig(
        game,
        [("10", "♠"), ("6", "♣"), ("K", "♥"), ("7", "♣"), ("A", "♠"), ("2", "♥"), ("10", "♦")],
    )
    game.start(20)
    game.act("split", balance=1000)
    assert game.hand.hands[0].status == "standing"
    assert "blackjack" not in [hand.status for hand in game.hand.hands]
    assert game.hand.active_hand_index == 1
    game.act("stand", balance=1000)
    assert game.result().payout == 80


def test_restore_rejects_nonconserving_shoe_and_inconsistent_live_round() -> None:
    game = Blackjack()
    rig(game, [("10", "♠"), ("9", "♣"), ("6", "♥"), ("7", "♣")])
    game.start(20)
    state = encode_blackjack_state(game)

    missing_card = deepcopy(state)
    missing_card["deck"].pop()
    with pytest.raises(ValueError):
        restore_blackjack_state(Blackjack(), missing_card)

    invalid_active_hand = deepcopy(state)
    invalid_active_hand["hands"][0]["status"] = "standing"
    with pytest.raises(ValueError):
        restore_blackjack_state(Blackjack(), invalid_active_hand)

    forged_natural = deepcopy(state)
    forged_natural["hands"][0]["status"] = "blackjack"
    with pytest.raises(ValueError):
        restore_blackjack_state(Blackjack(), forged_natural)

    forged_payout = deepcopy(state)
    forged_payout["hands"][0]["status"] = "won"
    with pytest.raises(ValueError):
        restore_blackjack_state(Blackjack(), forged_payout)


def test_natural_blackjack_state_restores_only_for_original_two_card_natural() -> None:
    game = Blackjack()
    rig(game, [("A", "♠"), ("9", "♣"), ("K", "♠"), ("7", "♣")])
    game.start(20)
    restored = Blackjack()
    restore_blackjack_state(restored, encode_blackjack_state(game))
    assert restored.hand.hands[0].status == "blackjack"
    assert restored.result().payout == 50


def test_version_two_save_remains_restorable_after_schema_upgrade() -> None:
    game = Blackjack()
    rig(game, [("10", "♠"), ("9", "♣"), ("6", "♥"), ("7", "♣")])
    game.start(20)
    old_state = encode_blackjack_state(game)
    old_state["version"] = 2
    old_state.pop("initial_bet")
    old_state.pop("discarded_cards")
    restored = Blackjack()
    restore_blackjack_state(restored, old_state)
    assert restored.hand.initial_bet == 20
    assert blackjack_view(restored, 1000)["status"] == "playing"


def test_version_three_save_remains_restorable_after_schema_upgrade() -> None:
    game = Blackjack()
    rig(game, [("10", "♠"), ("9", "♣"), ("6", "♥"), ("7", "♣")])
    game.start(20)
    old_state = encode_blackjack_state(game)
    old_state["version"] = 3
    old_state.pop("discarded_cards")

    restored = Blackjack()
    restore_blackjack_state(restored, old_state)
    assert restored.hand.initial_bet == 20
    assert encode_blackjack_state(restored)["version"] == 5


def test_legacy_active_round_can_be_resaved_in_current_format() -> None:
    game = Blackjack()
    rig(game, [("10", "♠"), ("9", "♣"), ("6", "♥"), ("7", "♣")])
    game.start(20)
    old_state = encode_blackjack_state(game)
    old_state["version"] = 4
    old_state.pop("round_id")

    restored = Blackjack()
    restore_blackjack_state(restored, old_state)
    current_state = encode_blackjack_state(restored)
    assert current_state["round_id"] is None
    reloaded = Blackjack()
    restore_blackjack_state(reloaded, current_state)
    assert blackjack_view(reloaded, 1000)["status"] == "playing"


def test_legacy_shoe_restores_cards_spent_in_completed_rounds() -> None:
    game = Blackjack()
    rig(
        game,
        [
            ("8", "♠"),
            ("K", "♣"),
            ("8", "♥"),
            ("7", "♣"),
            ("10", "♠"),
            ("9", "♦"),
            ("6", "♥"),
            ("7", "♦"),
        ],
    )
    game.start(20)
    game.act("stand", balance=1000)
    game.start(20)

    legacy = encode_blackjack_state(game)
    legacy["version"] = 2
    legacy.pop("initial_bet")
    legacy.pop("discarded_cards")
    restored = Blackjack()
    restore_blackjack_state(restored, legacy)

    upgraded = encode_blackjack_state(restored)
    assert upgraded["version"] == 5
    assert (
        len(upgraded["deck"])
        + len(upgraded["discarded_cards"])
        + len(upgraded["dealer_cards"])
        + sum(len(hand["cards"]) for hand in upgraded["hands"])
        == 312
    )
    assert blackjack_view(restored, 1000)["status"] == "playing"


def test_current_save_restores_after_several_rounds() -> None:
    game = Blackjack()
    rig(
        game,
        [
            ("8", "♠"),
            ("K", "♣"),
            ("8", "♥"),
            ("7", "♣"),
            ("10", "♠"),
            ("9", "♦"),
            ("6", "♥"),
            ("7", "♦"),
        ],
    )
    game.start(20)
    game.act("stand", balance=1000)
    game.start(20)
    saved = encode_blackjack_state(game)
    assert saved["version"] == 5
    assert len(saved["discarded_cards"]) == 4

    restored = Blackjack()
    restore_blackjack_state(restored, saved)
    assert encode_blackjack_state(restored) == saved


def test_fair_snapshot_rejects_tampered_draw_order_and_unknown_version() -> None:
    server_seed = "00" * 32
    game = Blackjack()
    game.start(
        20,
        fairness={
            "server_seed": server_seed,
            "server_seed_hash": seed_hash(server_seed),
            "client_seed": "restore-test",
            "nonce": 0,
        },
        server_seed=server_seed,
        client_seed="restore-test",
    )
    saved = encode_blackjack_state(game)
    assert saved is not None

    restored = Blackjack()
    restore_blackjack_state(restored, saved)
    assert encode_blackjack_state(restored) == saved

    tampered = dict(saved)
    tampered["draw_order"] = list(saved["draw_order"])
    tampered["draw_order"][0] = "A♠" if tampered["draw_order"][0] != "A♠" else "K♠"
    with pytest.raises(ValueError):
        restore_blackjack_state(Blackjack(), tampered)

    unsupported = dict(saved)
    unsupported["version"] = 6
    with pytest.raises(ValueError):
        restore_blackjack_state(Blackjack(), unsupported)


def test_mixed_split_result_even_when_net_is_push() -> None:
    game = Blackjack()
    rig(game, [("8", "♠"), ("9", "♣"), ("8", "♥"), ("8", "♣"), ("10", "♦"), ("2", "♥")])
    game.start(20)
    game.act("split", balance=1000)
    game.act("stand", balance=1000)
    game.act("stand", balance=1000)
    assert [h.status for h in game.hand.hands] == ["won", "lost"]
    assert game.result().profit == 0
    assert game.hand.status == "mixed"


def test_restore_active_round_and_idempotent_session_accounting() -> None:
    with tempfile.TemporaryDirectory() as directory:
        session = CasinoService(PlayerRepository(Path(directory) / "test.sqlite3"))
        rig_legacy_service(session, [("10", "♠"), ("9", "♣"), ("6", "♥"), ("7", "♣")])
        started = session.start_blackjack(20, "start")
        assert started["player"]["balance"] == 2480
        assert session.start_blackjack(20, "start") == started
        restored = CasinoService(PlayerRepository(Path(directory) / "test.sqlite3"))
        assert restored.state()["blackjack"]["status"] == "playing"
        settled = restored.blackjack_action("surrender", "action")
        assert settled["player"]["balance"] == 2490
        assert restored.blackjack_action("surrender", "action") == settled


def test_active_blackjack_snapshot_must_match_durable_round_stakes() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "casino.sqlite3"
        session = CasinoService(PlayerRepository(path))
        rig_legacy_service(session, [("10", "♠"), ("9", "♣"), ("6", "♥"), ("7", "♣")])
        session.start_blackjack(20, "start")

        db = sqlite3.connect(path)
        try:
            saved = json.loads(
                db.execute("SELECT blackjack_json FROM profile WHERE id=1").fetchone()[0]
            )
            saved["insurance_bet"] = 10
            db.execute(
                "UPDATE profile SET blackjack_json=? WHERE id=1",
                (json.dumps(saved),),
            )
            db.commit()
        finally:
            db.close()

        with pytest.raises(RuntimeError, match="wagers do not match"):
            CasinoService(PlayerRepository(path))


def test_split_stakes_restore_against_round_ledger() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "casino.sqlite3"
        session = CasinoService(PlayerRepository(path))
        rig_legacy_service(
            session,
            [("8", "♠"), ("6", "♣"), ("8", "♥"), ("7", "♣"), ("2", "♦")],
        )
        session.start_blackjack(20, "start")
        session.blackjack_action("split", "split")

        restored = CasinoService(PlayerRepository(path))
        assert restored.blackjack.hand.bet == 40
        db = sqlite3.connect(path)
        try:
            stakes = db.execute(
                "SELECT entry_type,delta,round_id FROM ledger "
                "WHERE entry_type LIKE 'blackjack%stake' ORDER BY id"
            ).fetchall()
        finally:
            db.close()
        assert [(entry, delta) for entry, delta, _ in stakes] == [
            ("blackjack_stake", -20),
            ("blackjack_split_stake", -20),
        ]
        assert len({round_id for _, _, round_id in stakes}) == 1


def test_failed_blackjack_save_restores_hand_and_shoe() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repository = PlayerRepository(Path(directory) / "casino.sqlite3")
        session = CasinoService(repository)
        rig_legacy_service(
            session,
            [("10", "♠"), ("9", "♣"), ("6", "♥"), ("7", "♣"), ("2", "♦")],
        )
        session.start_blackjack(20, "start")
        before_state = encode_blackjack_state(session.blackjack)
        before_balance = session.player.balance

        def fail_save(*args, **kwargs):
            raise OSError("disk unavailable")

        repository.save = fail_save
        with pytest.raises(OSError, match="disk unavailable"):
            session.blackjack_action("hit", "hit-request")

        assert encode_blackjack_state(session.blackjack) == before_state
        assert session.player.balance == before_balance
        assert repository.get_request_response("hit-request") is None


def test_deterministic_action_traces_preserve_wallet_and_restore_invariants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "casino.sqlite3"
        server_seed = "0" * 62 + "26"
        monkeypatch.setattr("secrets.token_hex", lambda _: server_seed)

        def reload_session() -> CasinoService:
            return CasinoService(PlayerRepository(path))

        session = reload_session()
        action_count = 0
        seen_actions = set()
        trace_seeds = (7, 11, 29, 47, 73, 101, 251, 91827)
        for trace_seed in trace_seeds:
            chooser = random.Random(trace_seed)
            for round_number in range(8):
                request_id = f"{trace_seed}-{round_number}"
                session.start_blackjack(10, f"trace-start-{request_id}")
                session = reload_session()
                while session.blackjack.hand and session.blackjack.hand.status in {
                    "playing",
                    "insurance",
                }:
                    actions = session.blackjack.available_actions(session.player.balance)
                    assert actions
                    action = "insurance" if "insurance" in actions else chooser.choice(actions)
                    seen_actions.add(action)
                    session.blackjack_action(action, f"trace-action-{action_count}")
                    action_count += 1
                    previous_state = session.state()
                    session = reload_session()
                    assert session.state() == previous_state
                assert session.player.balance >= 0
                assert session.blackjack.hand is not None
                assert session.blackjack.hand.status not in {"playing", "insurance"}

        db = sqlite3.connect(path)
        try:
            ledger_total = db.execute("SELECT SUM(delta) FROM ledger").fetchone()[0]
            saved_balance = db.execute("SELECT balance FROM profile WHERE id=1").fetchone()[0]
        finally:
            db.close()
        assert ledger_total == saved_balance
        assert session.player.balance == saved_balance
        assert len(session.player.rounds) == len(trace_seeds) * 8
        assert "insurance" in seen_actions


def test_two_sessions_serialize_wallet_updates_without_lost_rounds() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "shared.sqlite3"
        first = CasinoService(PlayerRepository(path))
        second = CasinoService(PlayerRepository(path))
        for session in (first, second):
            session.games["slots"].play_at_stops = lambda bet, stops: GameResult(
                "slots", "Слоты", "Проигрыш", bet, 0, "детерминированный проигрыш"
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            first_result = pool.submit(first.play, "slots", 10, "", "first-request")
            second_result = pool.submit(second.play, "slots", 10, "", "second-request")
            first_result.result()
            second_result.result()

        player = CasinoService(PlayerRepository(path)).state()["player"]
        assert player["balance"] == 2480
        assert player["rounds_played"] == 2
        db = sqlite3.connect(path)
        try:
            assert db.execute("SELECT COUNT(*) FROM ledger").fetchone()[0] == 5
            assert (
                db.execute("SELECT balance_after FROM ledger ORDER BY id DESC LIMIT 1").fetchone()[
                    0
                ]
                == 2480
            )
        finally:
            db.close()


def test_concurrent_retries_with_same_key_settle_once() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "shared.sqlite3"
        first = CasinoService(PlayerRepository(path))
        second = CasinoService(PlayerRepository(path))
        for session in (first, second):
            session.games["slots"].play_at_stops = lambda bet, stops: GameResult(
                "slots", "Слоты", "Проигрыш", bet, 0, "детерминированный проигрыш"
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            first_result = pool.submit(first.play, "slots", 10, "", "same-request")
            second_result = pool.submit(second.play, "slots", 10, "", "same-request")
            assert first_result.result() == second_result.result()

        player = CasinoService(PlayerRepository(path)).state()["player"]
        assert player["balance"] == 2490
        assert player["rounds_played"] == 1
        db = sqlite3.connect(path)
        try:
            assert (
                db.execute(
                    "SELECT COUNT(*) FROM ledger WHERE request_key='same-request'"
                ).fetchone()[0]
                == 2
            )
        finally:
            db.close()


def test_profile_balance_change_requires_conserving_ledger_entries() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repository = PlayerRepository(Path(directory) / "casino.sqlite3")
        player = repository.load()
        player.balance -= 1

        with pytest.raises(TypeError):
            repository.save(player)  # Every persisted profile write needs an operation record.

        with pytest.raises(ValueError, match="Ledger movements"):
            repository.save(
                player,
                request_key="invalid-movement",
                signature="test",
                ledger_entries=[],
                response={},
            )

        with pytest.raises(ValueError, match="Typed ledger movements"):
            repository.save(
                player,
                request_key="untyped-movement",
                signature="test",
                ledger_entries=[("profile_adjustment", -1)],
                response={},
            )
        with pytest.raises(ValueError, match="non-empty reason"):
            LedgerMovement.adjustment(-1, " ")

        assert repository.load().balance == 2500
        assert repository.get_request_response("invalid-movement") is None


def test_startup_rejects_corrupted_ledger_balance_chain() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "casino.sqlite3"
        repository = PlayerRepository(path)
        player = repository.load()
        player.balance -= 10
        repository.save(
            player,
            request_key="loss",
            signature="test",
            ledger_entries=[LedgerMovement(LedgerEntryType.BET_STAKE, -10)],
            response={},
        )
        db = sqlite3.connect(path)
        try:
            db.execute(
                "UPDATE ledger SET balance_after=balance_after+1 "
                "WHERE request_key='loss' AND entry_type='bet_stake'"
            )
            db.commit()
        finally:
            db.close()

        with pytest.raises(RuntimeError, match="Ledger balance chain"):
            PlayerRepository(path)


def test_legacy_ledger_gets_a_verified_opening_balance() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "legacy.sqlite3"
        db = sqlite3.connect(path)
        try:
            db.executescript("""
                CREATE TABLE profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1), name TEXT NOT NULL,
                    balance INTEGER NOT NULL, rounds_json TEXT NOT NULL, blackjack_json TEXT
                );
                INSERT INTO profile VALUES (1, 'Гость', 2490, '[]', NULL);
                CREATE TABLE ledger (
                    id INTEGER PRIMARY KEY, request_key TEXT NOT NULL, entry_type TEXT NOT NULL,
                    delta INTEGER NOT NULL, balance_after INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                INSERT INTO ledger(request_key,entry_type,delta,balance_after)
                VALUES ('old-loss','bet_stake',-10,2490), ('old-loss','game_payout',0,2490);
                CREATE TABLE processed_requests (
                    request_key TEXT PRIMARY KEY, response_json TEXT NOT NULL
                );
            """)
            db.commit()
        finally:
            db.close()

        PlayerRepository(path)
        db = sqlite3.connect(path)
        try:
            assert db.execute("PRAGMA user_version").fetchone()[0] == 4
            rows = db.execute(
                "SELECT entry_type,delta,balance_after FROM ledger ORDER BY id"
            ).fetchall()
            assert rows == [
                ("opening_balance", 2500, 2500),
                ("bet_stake", -10, 2490),
                ("game_payout", 0, 2490),
            ]
        finally:
            db.close()


def test_refill_is_rejected_during_an_active_blackjack_round() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repository = PlayerRepository(Path(directory) / "casino.sqlite3")
        player = repository.load()
        player.balance = 10
        repository.save(
            player,
            request_key="test-adjust-balance",
            signature="test.adjust-balance",
            ledger_entries=[LedgerMovement.adjustment(-2490, "test fixture balance")],
            response={},
        )
        with closing(sqlite3.connect(repository.path)) as db:
            adjustment = db.execute(
                "SELECT entry_type,delta,reason FROM ledger WHERE request_key='test-adjust-balance'"
            ).fetchone()
        assert adjustment == ("profile_adjustment", -2490, "test fixture balance")
        session = CasinoService(repository)
        rig_legacy_service(session, [("10", "♠"), ("9", "♣"), ("6", "♥"), ("7", "♣")])
        session.start_blackjack(10, "start")

        with pytest.raises(ValueError, match="после завершения"):
            session.refill("refill-during-hand")
        assert session.player.balance == 0
        assert repository.get_request_response("refill-during-hand") is None


def test_idempotency_key_is_bound_to_operation_and_payload() -> None:
    with tempfile.TemporaryDirectory() as directory:
        session = CasinoService(PlayerRepository(Path(directory) / "test.sqlite3"))
        session.start_blackjack(20, "shared-key")
        with pytest.raises(ValueError, match="другой операции"):
            session.blackjack_action("stand", "shared-key")
        with pytest.raises(ValueError, match="другой операции"):
            session.start_blackjack(22, "shared-key")


def test_session_charges_each_resplit_and_records_the_round_once() -> None:
    with tempfile.TemporaryDirectory() as directory:
        session = CasinoService(PlayerRepository(Path(directory) / "test.sqlite3"))
        rig_legacy_service(
            session,
            [
                ("8", "♠"),
                ("6", "♣"),
                ("8", "♥"),
                ("10", "♦"),
                ("8", "♣"),
                ("2", "♠"),
                ("8", "♦"),
                ("3", "♣"),
                ("7", "♠"),
                ("7", "♦"),
                ("2", "♦"),
            ],
        )
        session.start_blackjack(20, "start-resplit")
        session.blackjack_action("split", "split-one")
        session.blackjack_action("split", "split-two")
        assert session.state()["player"]["balance"] == 2440

        session.blackjack_action("stand", "stand-one")
        assert "split" in session.state()["blackjack"]["available_actions"]
        session.blackjack_action("split", "split-three")
        session.blackjack_action("stand", "stand-two")
        session.blackjack_action("stand", "stand-three")
        settled = session.blackjack_action("stand", "stand-four")

        assert settled["player"]["balance"] == 2420
        assert settled["player"]["rounds_played"] == 1
        assert settled["player"]["losses"] == 1
        assert settled["player"]["total_wagered"] == 80
        assert settled["history"][0]["bet"] == 80
        assert settled["history"][0]["payout"] == 0


def test_session_rolls_back_wallet_and_hand_when_card_draw_fails() -> None:
    def fail_draw() -> Card:
        raise RuntimeError("simulated shoe failure")

    with tempfile.TemporaryDirectory() as directory:
        start_session = CasinoService(PlayerRepository(Path(directory) / "start.sqlite3"))
        rig_legacy_service(start_session, [("8", "♠"), ("6", "♣"), ("8", "♥"), ("7", "♣")])
        start_shoe = start_session.blackjack._shoe.remaining_cards
        start_session.blackjack._draw = fail_draw
        with pytest.raises(RuntimeError, match="simulated shoe failure"):
            start_session.start_blackjack(20, "failed-start")
        assert start_session.player.balance == 2500
        assert start_session.blackjack.hand is None
        assert start_session.blackjack._shoe.remaining_cards == start_shoe

        action_session = CasinoService(PlayerRepository(Path(directory) / "action.sqlite3"))
        rig_legacy_service(action_session, [("8", "♠"), ("6", "♣"), ("8", "♥"), ("7", "♣")])
        started = action_session.start_blackjack(20, "start")
        before_action = encode_blackjack_state(action_session.blackjack)
        action_session.blackjack._draw = fail_draw
        with pytest.raises(RuntimeError, match="simulated shoe failure"):
            action_session.blackjack_action("double", "failed-double")
        assert action_session.player.balance == started["player"]["balance"]
        assert encode_blackjack_state(action_session.blackjack) == before_action
        assert action_session.repository.get_request_response("failed-double") is None


def test_history_and_statistics_continue_past_one_hundred_rounds() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repository = PlayerRepository(Path(directory) / "test.sqlite3")
        player = Player(
            rounds=[GameResult("roulette", "Рулетка", "Победа", 10, 20, "Тест") for _ in range(125)]
        )
        repository.save(
            player,
            request_key="test-seed-history",
            signature="test.seed-history",
            ledger_entries=[],
            response={},
        )
        restored = repository.load()
        assert len(restored.rounds) == 125
        assert restored.wins == 125
        assert restored.total_wagered == 1250


def test_old_idempotency_rows_are_reported_as_ambiguous_on_retry() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "legacy.sqlite3"
        db = sqlite3.connect(path)
        try:
            db.executescript("""
                CREATE TABLE profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1), name TEXT NOT NULL,
                    balance INTEGER NOT NULL, rounds_json TEXT NOT NULL, blackjack_json TEXT
                );
                INSERT INTO profile VALUES (1, 'Гость', 2500, '[]', NULL);
                CREATE TABLE processed_requests (
                    request_key TEXT PRIMARY KEY, response_json TEXT NOT NULL
                );
            """)
            db.execute(
                "INSERT INTO processed_requests VALUES (?, ?)",
                ("legacy-key", json.dumps({"balance": 7})),
            )
            db.commit()
        finally:
            db.close()
        repository = PlayerRepository(path)
        with pytest.raises(IdempotencyConflict, match="старой версии"):
            repository.get_request_response("legacy-key", signature="wallet.refill")
        with pytest.raises(IdempotencyConflict, match="старой версии"):
            repository.get_request_response("legacy-key", signature="blackjack.start")
        db = sqlite3.connect(path)
        try:
            signature = db.execute(
                "SELECT signature FROM processed_requests WHERE request_key='legacy-key'"
            ).fetchone()[0]
            assert signature is None
        finally:
            db.close()


def test_old_blackjack_start_signature_replays_for_legacy_payload() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "legacy-signature.sqlite3"
        repository = PlayerRepository(path)
        service = CasinoService(repository)
        response = {"player": {"balance": 1234}}
        legacy_signature = service._request_signature("blackjack.start", bet=20)
        with repository.write_transaction() as unit_of_work:
            unit_of_work.save(
                service.player,
                None,
                request_key="old-blackjack-start",
                signature=legacy_signature,
                ledger_entries=[],
                response=response,
            )

        assert (
            service.start_blackjack(20, "old-blackjack-start", legacy_signature_compatible=True)
            == response
        )
        with pytest.raises(IdempotencyConflict):
            service.start_blackjack(20, "old-blackjack-start", "new-seed")
