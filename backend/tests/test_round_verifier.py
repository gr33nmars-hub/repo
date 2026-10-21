from __future__ import annotations

from itertools import product

import pytest
from casino.application.queries import game_result_view
from casino.domain.blackjack import Blackjack, BlackjackRules
from casino.domain.games import RED_NUMBERS, Roulette, SlotMachine, SlotRules
from casino.domain.models import Card, GameResult
from casino.domain.round_verifier import verification_status, verify_recorded_round
from casino.domain.shoe import Shoe
from casino.domain.slot_fairness import reel_stops, seed_hash


class FixedRandom:
    def __init__(self, value: int) -> None:
        self.value = value

    def choice(self, values):
        return self.value

    def shuffle(self, values: list) -> None:
        return None


def blackjack_with_draws(
    draws: list[tuple[str, str]], *, dealer_hits_soft_17: bool = False
) -> Blackjack:
    game = Blackjack(blackjack_rules=BlackjackRules(dealer_hits_soft_17=dealer_hits_soft_17))
    shoe = [Card(rank, suit) for _ in range(6) for suit in game.suits for rank in game.ranks]
    selected = []
    for rank, suit in draws:
        card = next(card for card in shoe if card.rank == rank and card.suit == suit)
        shoe.remove(card)
        selected.append(card)
    game._shoe = Shoe(shoe + list(reversed(selected)))
    game.start(20)
    return game


def test_slot_history_verifies_against_its_saved_rules_after_catalog_changes() -> None:
    game = SlotMachine()
    rules = game.slot_rules
    server_seed = "00" * 32
    client_seed = "client-0"
    stops = reel_stops(server_seed, client_seed, [len(reel) for reel in rules.reels])
    result = game.play_at_stops(10, stops)
    result.fairness = {
        "server_seed": server_seed,
        "server_seed_hash": seed_hash(server_seed),
        "client_seed": client_seed,
        "nonce": 0,
    }
    serialized = game_result_view(result)

    assert verify_recorded_round(serialized)
    changed_catalog = SlotRules(
        reels=tuple(tuple(reversed(reel)) for reel in rules.reels),
        triples=rules.triples,
        pair_multiplier=rules.pair_multiplier,
    )
    assert changed_catalog.snapshot() != serialized["rules_snapshot"]
    assert verify_recorded_round(serialized)

    for nonce in (True, 0.0):
        tampered_proof = {**serialized, "fairness": {**serialized["fairness"], "nonce": nonce}}
        assert not verify_recorded_round(tampered_proof)

    tampered = {**serialized, "payout": serialized["payout"] + 1}
    tampered["profit"] += 1
    assert not verify_recorded_round(tampered)


def test_roulette_records_machine_readable_pocket_and_payout() -> None:
    result = game_result_view(Roulette(rng=FixedRandom(1)).play(25, "red"))
    assert result["outcome"] == {"number": 1, "color": "red", "choice": "red"}
    assert result["rules_snapshot"]["red_numbers"] == sorted(RED_NUMBERS)
    assert verify_recorded_round(result)

    result["outcome"]["number"] = 2
    assert not verify_recorded_round(result)


@pytest.mark.parametrize(("number", "choice"), list(product(range(37), ("red", "black", "zero"))))
def test_verifier_matches_independent_oracle_for_every_roulette_pocket(
    number: int, choice: str
) -> None:
    expected_red = {
        1,
        3,
        5,
        7,
        9,
        12,
        14,
        16,
        18,
        19,
        21,
        23,
        25,
        27,
        30,
        32,
        34,
        36,
    }
    recorded = game_result_view(Roulette(rng=FixedRandom(number)).play(25, choice))
    actual_color = "zero" if number == 0 else "red" if number in expected_red else "black"
    multiplier = 36 if choice == "zero" else 2
    expected_payout = 25 * multiplier if choice == actual_color else 0
    assert recorded["payout"] == expected_payout
    assert verify_recorded_round(recorded)


def test_verifier_and_independent_oracle_cover_all_512_slot_stops() -> None:
    game = SlotMachine()
    rules = game.slot_rules
    target_count = 1
    for reel in rules.reels:
        target_count *= len(reel)
    expected_triples = {"🍒": 4, "🍋": 4, "🔔": 8, "💎": 12, "7️⃣": 24}
    target_stops = set(product(*(range(len(reel)) for reel in rules.reels)))
    verified_stops: set[tuple[int, int, int]] = set()
    seed_counter = 0

    while len(verified_stops) < target_count:
        server_seed = f"{seed_counter:064x}"
        client_seed = "exhaustive-slot-oracle"
        stops = tuple(reel_stops(server_seed, client_seed, [len(reel) for reel in rules.reels]))
        seed_counter += 1
        if stops in verified_stops:
            continue
        recorded_result = game.play_at_stops(10, list(stops))
        recorded_result.fairness = {
            "server_seed": server_seed,
            "server_seed_hash": seed_hash(server_seed),
            "client_seed": client_seed,
            "nonce": 0,
        }
        recorded = game_result_view(recorded_result)
        symbols = [reel[stop] for reel, stop in zip(rules.reels, stops, strict=True)]
        expected_multiplier = (
            expected_triples[symbols[0]]
            if symbols[0] == symbols[1] == symbols[2]
            else 1
            if len(set(symbols)) == 2
            else 0
        )
        assert recorded["payout"] == 10 * expected_multiplier
        assert verify_recorded_round(recorded)
        verified_stops.add(stops)

    assert verified_stops == target_stops


def test_blackjack_natural_result_records_settlement_inputs() -> None:
    game = Blackjack()
    shoe = [Card(rank, suit) for _ in range(6) for suit in game.suits for rank in game.ranks]
    draws = [("A", "♠"), ("9", "♣"), ("K", "♠"), ("7", "♣")]
    selected = []
    for rank, suit in draws:
        card = next(card for card in shoe if card.rank == rank and card.suit == suit)
        shoe.remove(card)
        selected.append(card)
    game._shoe = Shoe(shoe + list(reversed(selected)))
    game.start(20)
    result = game_result_view(game.result())

    assert result["payout"] == 50
    assert result["rule_version"] == "blackjack-v1"
    assert verify_recorded_round(result)

    tampered = {
        **result,
        "rules_snapshot": {**result["rules_snapshot"], "natural_numerator": 1},
    }
    assert verification_status(tampered) == "invalid"


@pytest.mark.parametrize(
    ("draws", "actions"),
    [
        ([("10", "♠"), ("A", "♣"), ("6", "♥"), ("K", "♦")], ["insurance"]),
        ([("10", "♠"), ("9", "♣"), ("6", "♥"), ("7", "♦")], ["surrender"]),
        ([("5", "♠"), ("10", "♣"), ("6", "♥"), ("6", "♦"), ("10", "♣"), ("2", "♥")], ["double"]),
        (
            [("8", "♠"), ("6", "♣"), ("8", "♥"), ("9", "♦"), ("3", "♠"), ("2", "♥"), ("5", "♣")],
            ["split", "stand", "stand"],
        ),
        ([("10", "♠"), ("6", "♣"), ("8", "♥"), ("A", "♦")], ["stand"]),
    ],
    ids=["insurance", "surrender", "double", "split", "soft-17"],
)
def test_blackjack_verifier_covers_actions_and_soft_17(
    draws: list[tuple[str, str]], actions: list[str]
) -> None:
    game = blackjack_with_draws(draws)
    for action in actions:
        game.act(action, 1000)
    recorded = game_result_view(game.result())
    assert verify_recorded_round(recorded)


def test_old_history_is_explicitly_unverified() -> None:
    legacy = game_result_view(GameResult("roulette", "Рулетка", "Победа", 10, 20, "Красное"))
    assert verification_status(legacy) == "legacy-unverified"


def test_legacy_round_with_rule_data_is_checked_before_unverified_status() -> None:
    legacy = game_result_view(Roulette(rng=FixedRandom(1)).play(25, "red"))
    assert verification_status(legacy) == "legacy-unverified"

    legacy["outcome"]["number"] = 2
    assert verification_status(legacy) == "invalid"


def test_blackjack_proof_binds_recorded_draw_order_to_seed() -> None:
    server_seed = "00" * 32
    game = Blackjack()
    game.start(
        20,
        fairness={
            "server_seed": server_seed,
            "server_seed_hash": seed_hash(server_seed),
            "client_seed": "round-verifier-test",
            "nonce": 0,
        },
        server_seed=server_seed,
        client_seed="round-verifier-test",
    )
    while game.hand and game.hand.status in {"playing", "insurance"}:
        action = "decline_insurance" if game.hand.status == "insurance" else "stand"
        game.act(action, 1000)
    recorded = game_result_view(game.result())

    assert verification_status(recorded) == "verified"
    tampered = {**recorded, "outcome": {**recorded["outcome"]}}
    tampered["outcome"]["draw_order"] = list(recorded["outcome"]["draw_order"])
    tampered["outcome"]["draw_order"][0] = (
        "A♠" if tampered["outcome"]["draw_order"][0] != "A♠" else "K♠"
    )
    assert verification_status(tampered) == "invalid"
    reassigned = {**recorded, "outcome": {**recorded["outcome"]}}
    reassigned["outcome"]["draw_events"] = [
        {**event, "target": "dealer" if event["target"] != "dealer" else "hand:0"}
        for event in recorded["outcome"]["draw_events"]
    ]
    assert verification_status(reassigned) == "invalid"


def test_corrupt_blackjack_hand_is_invalid_instead_of_raising() -> None:
    game = blackjack_with_draws([("A", "♠"), ("9", "♣"), ("K", "♠"), ("7", "♣")])
    recorded = game_result_view(game.result())
    recorded["outcome"]["hands"] = [None]

    assert verification_status(recorded) == "invalid"


def test_surrender_with_more_than_two_cards_is_invalid() -> None:
    game = blackjack_with_draws([("10", "♠"), ("9", "♣"), ("6", "♥"), ("7", "♦")])
    game.act("surrender", 1000)
    recorded = game_result_view(game.result())
    recorded["outcome"]["hands"][0]["cards"].append("2♣")

    assert not verify_recorded_round(recorded)


def test_dealer_cannot_draw_after_reaching_standing_total() -> None:
    game = blackjack_with_draws(
        [
            ("10", "♠"),
            ("6", "♣"),
            ("9", "♠"),
            ("10", "♣"),
            ("2", "♥"),
        ]
    )
    game.act("stand", 1000)
    recorded = game_result_view(game.result())
    recorded["outcome"]["dealer_cards"].append("2♦")
    recorded["outcome"]["hands"][0]["status"] = "lost"
    recorded["payout"] = 0
    recorded["profit"] = -recorded["bet"]

    assert not verify_recorded_round(recorded)


def test_h17_dealer_does_not_draw_when_player_has_natural() -> None:
    game = blackjack_with_draws(
        [("A", "♠"), ("A", "♥"), ("K", "♠"), ("6", "♦")],
        dealer_hits_soft_17=True,
    )
    game.act("decline_insurance", 1000)

    assert game.result().outcome["dealer_cards"] == ["A♥", "6♦"]
    assert verify_recorded_round(game_result_view(game.result()))
