"""Tests for the explicit OOP contracts used by the Python domain."""

from __future__ import annotations

import unittest

from casino.domain.models import Card, GameResult, Player
from casino.domain.oop import PairMap


class OopContractTests(unittest.TestCase):
    def test_pair_map_uses_mapping_protocol_with_ordered_pairs(self) -> None:
        games = PairMap((("slots", 1), ("roulette", 2)))

        games["slots"] = 3

        self.assertEqual(games["slots"], 3)
        self.assertEqual(list(games), ["slots", "roulette"])
        self.assertEqual(games.entries, (("slots", 3), ("roulette", 2)))
        self.assertEqual(games, PairMap((("slots", 3), ("roulette", 2))))

    def test_domain_entities_have_explicit_comparison_and_display_methods(self) -> None:
        first = Card("A", "♠")
        same = Card("A", "♠")
        later = Card("K", "♣")

        self.assertEqual(first, same)
        self.assertNotEqual(first, later)
        self.assertIsInstance(repr(first), str)
        self.assertIsInstance(str(first), str)

        result = GameResult("slots", "Слоты", "Тест", 10, 0, "—")
        player = Player("Гость", rounds=[result])
        self.assertIn("Гость", str(player))
        self.assertIn("slots", repr(result))


if __name__ == "__main__":
    unittest.main()
