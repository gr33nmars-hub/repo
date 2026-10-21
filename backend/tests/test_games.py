from fractions import Fraction
from itertools import product

import pytest
from casino.application.queries import game_catalog_item, game_result_view
from casino.domain.core import GameRules
from casino.domain.errors import InvalidCasinoCommand
from casino.domain.games import RED_NUMBERS, Roulette, SlotMachine, SlotRules


class FixedRandom:
    def __init__(self, values: list[object]) -> None:
        self.values = iter(values)

    def choice(self, seq):
        value = next(self.values)
        assert value in seq
        return value

    def shuffle(self, x: list) -> None:
        pass


@pytest.mark.parametrize("bet", [0, True, 10.0, 1_000_001])
def test_slots_validate_bets_before_drawing_or_settling(bet: int | float | bool) -> None:
    game = SlotMachine(rng=FixedRandom([]), rules=GameRules(minimum_bet=1))

    with pytest.raises(InvalidCasinoCommand):
        game.play(bet)
    with pytest.raises(InvalidCasinoCommand):
        game.play_at_stops(bet, [0, 0, 0])


@pytest.mark.parametrize("bet", [0, True, 10.0, 1_000_001])
def test_roulette_validates_bets_before_drawing_or_settling(bet: int | float | bool) -> None:
    game = Roulette(rng=FixedRandom([]), rules=GameRules(minimum_bet=1))

    with pytest.raises(InvalidCasinoCommand):
        game.play(bet)
    with pytest.raises(InvalidCasinoCommand):
        game.play_at_number(bet, "red", 1)


def test_slot_paytable_rtp_matches_exhaustive_reel_outcomes() -> None:
    rules = SlotRules()
    payout = 0
    counts = {"triple": 0, "pair": 0, "loss": 0}
    multipliers = dict(rules.triples)
    for result in product(*rules.reels):
        if result[0] == result[1] == result[2]:
            counts["triple"] += 1
            payout += multipliers[result[0]]
        elif len(set(result)) == 2:
            counts["pair"] += 1
            payout += rules.pair_multiplier
        else:
            counts["loss"] += 1

    assert counts == {"triple": 38, "pair": 270, "loss": 204}
    assert Fraction(payout, len(list(product(*rules.reels)))) == Fraction(454, 512)
    assert rules.theoretical_return_percent == 88.7


def test_european_roulette_has_18_red_18_black_and_one_zero() -> None:
    outcomes = [
        "zero" if number == 0 else "red" if number in RED_NUMBERS else "black"
        for number in range(37)
    ]
    assert outcomes.count("red") == 18
    assert outcomes.count("black") == 18
    assert outcomes.count("zero") == 1
    for choice in ("red", "black", "zero"):
        total_return = sum(
            Roulette(rng=FixedRandom([number])).play(10, choice).payout for number in range(37)
        )
        assert Fraction(total_return, 37 * 10) == Fraction(36, 37)


@pytest.mark.parametrize(
    ("symbols", "expected"),
    [(["7️⃣", "7️⃣", "7️⃣"], 240), (["🍒", "🍒", "💎"], 10), (["🍒", "🍋", "💎"], 0)],
)
def test_slots_pay_triple_pair_and_loss(symbols: list[str], expected: int) -> None:
    rules = SlotRules()
    stops = [reel.index(symbol) for reel, symbol in zip(rules.reels, symbols, strict=True)]
    result = SlotMachine(rng=FixedRandom(stops), slot_rules=rules).play(10)

    assert result.payout == expected
    assert result.reel_stops == stops
    assert result.symbols == [reel[stop] for reel, stop in zip(rules.reels, stops)]
    assert game_result_view(result)["reel_stops"] == stops


def test_slot_reel_strips_keep_original_symbol_frequencies() -> None:
    rules = SlotRules()
    for reel in rules.reels:
        assert {symbol: reel.count(symbol) for symbol in set(reel)} == {
            "🍒": 3,
            "🍋": 2,
            "🔔": 1,
            "💎": 1,
            "7️⃣": 1,
        }
    assert game_catalog_item(SlotMachine(slot_rules=rules))["reel_strips"] == [
        list(reel) for reel in rules.reels
    ]


@pytest.mark.parametrize(
    ("number", "choice", "expected"), [(0, "zero", 360), (1, "red", 20), (2, "red", 0)]
)
def test_roulette_pays_zero_and_color(number: int, choice: str, expected: int) -> None:
    result = Roulette(rng=FixedRandom([number])).play(10, choice)
    assert result.payout == expected


@pytest.mark.parametrize(("number", "choice"), list(product(range(37), ("red", "black", "zero"))))
def test_committed_roulette_number_uses_same_settlement_without_changing_rng(
    number: int, choice: str
) -> None:
    rng = FixedRandom([number])
    game = Roulette(rng=rng)
    committed = game.play_at_number(10, choice, number)

    assert game._rng is rng
    ordinary = game.play(10, choice)
    assert committed.outcome == ordinary.outcome
    assert committed.payout == ordinary.payout
    assert committed.message == ordinary.message
