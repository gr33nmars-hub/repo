import unittest
from fractions import Fraction
from itertools import product

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


class PayoutTests(unittest.TestCase):
    def test_slot_paytable_rtp_matches_exhaustive_reel_outcomes(self) -> None:
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

        self.assertEqual(counts, {"triple": 38, "pair": 270, "loss": 204})
        self.assertEqual(Fraction(payout, len(list(product(*rules.reels)))), Fraction(454, 512))
        self.assertEqual(rules.theoretical_return_percent, 88.7)

    def test_european_roulette_has_18_red_18_black_and_one_zero(self) -> None:
        outcomes = [
            "zero" if number == 0 else "red" if number in RED_NUMBERS else "black"
            for number in range(37)
        ]
        self.assertEqual(outcomes.count("red"), 18)
        self.assertEqual(outcomes.count("black"), 18)
        self.assertEqual(outcomes.count("zero"), 1)
        for choice in ("red", "black", "zero"):
            total_return = 0
            for number in range(37):
                result = Roulette(rng=FixedRandom([number])).play(10, choice)
                total_return += result.payout
            self.assertEqual(Fraction(total_return, 37 * 10), Fraction(36, 37))

    def test_slots_pay_triple_pair_and_loss(self) -> None:
        rules = SlotRules()
        for symbols, expected in [
            (["7️⃣", "7️⃣", "7️⃣"], 240),
            (["🍒", "🍒", "💎"], 10),
            (["🍒", "🍋", "💎"], 0),
        ]:
            with self.subTest(symbols=symbols):
                stops = [
                    reel.index(symbol) for reel, symbol in zip(rules.reels, symbols, strict=True)
                ]
                result = SlotMachine(rng=FixedRandom(stops), slot_rules=rules).play(10)
                self.assertEqual(result.payout, expected)
                self.assertEqual(result.reel_stops, stops)
                self.assertEqual(
                    result.symbols, [reel[stop] for reel, stop in zip(rules.reels, stops)]
                )
                self.assertEqual(result.to_dict()["reel_stops"], stops)

    def test_slot_reel_strips_keep_original_symbol_frequencies(self) -> None:
        rules = SlotRules()
        for reel in rules.reels:
            self.assertEqual(
                {symbol: reel.count(symbol) for symbol in set(reel)},
                {"🍒": 3, "🍋": 2, "🔔": 1, "💎": 1, "7️⃣": 1},
            )
        self.assertEqual(
            SlotMachine(slot_rules=rules).catalog_info()["reel_strips"],
            [list(reel) for reel in rules.reels],
        )

    def test_roulette_pays_zero_and_color(self) -> None:
        for number, choice, expected in [
            (0, "zero", 360),
            (1, "red", 20),
            (2, "red", 0),
        ]:
            with self.subTest(number=number, choice=choice):
                result = Roulette(rng=FixedRandom([number])).play(10, choice)
                self.assertEqual(result.payout, expected)

    def test_committed_roulette_number_uses_same_settlement_without_changing_rng(self) -> None:
        for number in range(37):
            for choice in ("red", "black", "zero"):
                with self.subTest(number=number, choice=choice):
                    rng = FixedRandom([number])
                    game = Roulette(rng=rng)
                    committed = game.play_at_number(10, choice, number)
                    self.assertIs(game._rng, rng)
                    ordinary = game.play(10, choice)
                    self.assertEqual(committed.outcome, ordinary.outcome)
                    self.assertEqual(committed.payout, ordinary.payout)
                    self.assertEqual(committed.message, ordinary.message)


if __name__ == "__main__":
    unittest.main()
