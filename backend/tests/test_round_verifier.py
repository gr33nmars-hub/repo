from __future__ import annotations

import unittest
from itertools import product

from casino.domain.blackjack import Blackjack, BlackjackRules
from casino.domain.games import RED_NUMBERS, Roulette, SlotMachine, SlotRules
from casino.domain.models import Card, GameResult
from casino.domain.round_verifier import verification_status, verify_recorded_round
from casino.domain.slot_fairness import reel_stops, seed_hash


class FixedRandom:
    def __init__(self, value: int) -> None:
        self.value = value

    def choice(self, values):
        return self.value

    def shuffle(self, values: list) -> None:
        return None


class RoundVerifierTests(unittest.TestCase):
    @staticmethod
    def _blackjack_with_draws(
        draws: list[tuple[str, str]], *, dealer_hits_soft_17: bool = False
    ) -> Blackjack:
        game = Blackjack(blackjack_rules=BlackjackRules(dealer_hits_soft_17=dealer_hits_soft_17))
        shoe = [Card(rank, suit) for _ in range(6) for suit in game.suits for rank in game.ranks]
        selected = []
        for rank, suit in draws:
            card = next(card for card in shoe if card.rank == rank and card.suit == suit)
            shoe.remove(card)
            selected.append(card)
        game.deck = shoe + list(reversed(selected))
        game.start(20)
        return game

    def test_slot_history_verifies_against_its_saved_rules_after_catalog_changes(self) -> None:
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
        serialized = result.to_dict()

        self.assertTrue(verify_recorded_round(serialized))
        changed_catalog = SlotRules(
            reels=tuple(tuple(reversed(reel)) for reel in rules.reels),
            triples=rules.triples,
            pair_multiplier=rules.pair_multiplier,
        )
        self.assertNotEqual(changed_catalog.snapshot(), serialized["rules_snapshot"])
        self.assertTrue(verify_recorded_round(serialized))

        tampered = {**serialized, "payout": serialized["payout"] + 1}
        tampered["profit"] += 1
        self.assertFalse(verify_recorded_round(tampered))

    def test_roulette_records_machine_readable_pocket_and_payout(self) -> None:
        result = Roulette(rng=FixedRandom(1)).play(25, "red").to_dict()
        self.assertEqual(result["outcome"], {"number": 1, "color": "red", "choice": "red"})
        self.assertEqual(result["rules_snapshot"]["red_numbers"], sorted(RED_NUMBERS))
        self.assertTrue(verify_recorded_round(result))

        result["outcome"]["number"] = 2
        self.assertFalse(verify_recorded_round(result))

    def test_verifier_matches_independent_oracle_for_every_roulette_pocket(self) -> None:
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
        for number in range(37):
            for choice in ("red", "black", "zero"):
                with self.subTest(number=number, choice=choice):
                    recorded = Roulette(rng=FixedRandom(number)).play(25, choice).to_dict()
                    actual_color = (
                        "zero" if number == 0 else "red" if number in expected_red else "black"
                    )
                    multiplier = 36 if choice == "zero" else 2
                    expected_payout = 25 * multiplier if choice == actual_color else 0
                    self.assertEqual(recorded["payout"], expected_payout)
                    self.assertTrue(verify_recorded_round(recorded))

    def test_verifier_and_independent_oracle_cover_all_512_slot_stops(self) -> None:
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
            recorded = recorded_result.to_dict()
            symbols = [reel[stop] for reel, stop in zip(rules.reels, stops, strict=True)]
            expected_multiplier = (
                expected_triples[symbols[0]]
                if symbols[0] == symbols[1] == symbols[2]
                else 1
                if len(set(symbols)) == 2
                else 0
            )
            self.assertEqual(recorded["payout"], 10 * expected_multiplier)
            self.assertTrue(verify_recorded_round(recorded))
            verified_stops.add(stops)

        self.assertEqual(verified_stops, target_stops)

    def test_blackjack_natural_result_records_settlement_inputs(self) -> None:
        game = Blackjack()
        shoe = [Card(rank, suit) for _ in range(6) for suit in game.suits for rank in game.ranks]
        draws = [("A", "♠"), ("9", "♣"), ("K", "♠"), ("7", "♣")]
        selected = []
        for rank, suit in draws:
            card = next(card for card in shoe if card.rank == rank and card.suit == suit)
            shoe.remove(card)
            selected.append(card)
        game.deck = shoe + list(reversed(selected))
        game.start(20)
        result = game.result().to_dict()

        self.assertEqual(result["payout"], 50)
        self.assertEqual(result["rule_version"], "blackjack-v1")
        self.assertTrue(verify_recorded_round(result))

        tampered = {
            **result,
            "rules_snapshot": {**result["rules_snapshot"], "natural_numerator": 1},
        }
        self.assertEqual(verification_status(tampered), "invalid")

    def test_blackjack_verifier_covers_insurance_surrender_double_split_and_soft_17(self) -> None:
        scenarios = {
            "insurance-dealer-natural": (
                [("10", "♠"), ("A", "♣"), ("6", "♥"), ("K", "♦")],
                ["insurance"],
            ),
            "late-surrender": (
                [("10", "♠"), ("9", "♣"), ("6", "♥"), ("7", "♦")],
                ["surrender"],
            ),
            "double": (
                [("5", "♠"), ("10", "♣"), ("6", "♥"), ("6", "♦"), ("10", "♣"), ("2", "♥")],
                ["double"],
            ),
            "split": (
                [
                    ("8", "♠"),
                    ("6", "♣"),
                    ("8", "♥"),
                    ("9", "♦"),
                    ("3", "♠"),
                    ("2", "♥"),
                    ("5", "♣"),
                ],
                ["split", "stand", "stand"],
            ),
            "dealer-soft-17-stands": (
                [("10", "♠"), ("6", "♣"), ("8", "♥"), ("A", "♦")],
                ["stand"],
            ),
        }
        for label, (draws, actions) in scenarios.items():
            with self.subTest(scenario=label):
                game = self._blackjack_with_draws(draws)
                for action in actions:
                    game.act(action, 1000)
                recorded = game.result().to_dict()
                self.assertTrue(verify_recorded_round(recorded))

    def test_old_history_is_explicitly_unverified(self) -> None:
        legacy = GameResult("roulette", "Рулетка", "Победа", 10, 20, "Красное").to_dict()
        self.assertEqual(verification_status(legacy), "legacy-unverified")

    def test_legacy_round_with_rule_data_is_checked_before_unverified_status(self) -> None:
        legacy = Roulette(rng=FixedRandom(1)).play(25, "red").to_dict()
        self.assertEqual(verification_status(legacy), "legacy-unverified")

        legacy["outcome"]["number"] = 2
        self.assertEqual(verification_status(legacy), "invalid")

    def test_blackjack_proof_binds_recorded_draw_order_to_seed(self) -> None:
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
        recorded = game.result().to_dict()

        self.assertEqual(verification_status(recorded), "verified")
        tampered = {**recorded, "outcome": {**recorded["outcome"]}}
        tampered["outcome"]["draw_order"] = list(recorded["outcome"]["draw_order"])
        tampered["outcome"]["draw_order"][0] = (
            "A♠" if tampered["outcome"]["draw_order"][0] != "A♠" else "K♠"
        )
        self.assertEqual(verification_status(tampered), "invalid")

    def test_corrupt_blackjack_hand_is_invalid_instead_of_raising(self) -> None:
        game = self._blackjack_with_draws([("A", "♠"), ("9", "♣"), ("K", "♠"), ("7", "♣")])
        recorded = game.result().to_dict()
        recorded["outcome"]["hands"] = [None]

        self.assertEqual(verification_status(recorded), "invalid")

    def test_surrender_with_more_than_two_cards_is_invalid(self) -> None:
        game = self._blackjack_with_draws([("10", "♠"), ("9", "♣"), ("6", "♥"), ("7", "♦")])
        game.act("surrender", 1000)
        recorded = game.result().to_dict()
        recorded["outcome"]["hands"][0]["cards"].append("2♣")

        self.assertFalse(verify_recorded_round(recorded))

    def test_dealer_cannot_draw_after_reaching_standing_total(self) -> None:
        game = self._blackjack_with_draws(
            [
                ("10", "♠"),
                ("6", "♣"),
                ("9", "♠"),
                ("10", "♣"),
                ("2", "♥"),
            ]
        )
        game.act("stand", 1000)
        recorded = game.result().to_dict()
        recorded["outcome"]["dealer_cards"].append("2♦")
        recorded["outcome"]["hands"][0]["status"] = "lost"
        recorded["payout"] = 0
        recorded["profit"] = -recorded["bet"]

        self.assertFalse(verify_recorded_round(recorded))

    def test_h17_dealer_does_not_draw_when_player_has_natural(self) -> None:
        game = self._blackjack_with_draws(
            [("A", "♠"), ("A", "♥"), ("K", "♠"), ("6", "♦")],
            dealer_hits_soft_17=True,
        )
        game.act("decline_insurance", 1000)

        self.assertEqual(game.result().outcome["dealer_cards"], ["A♥", "6♦"])
        self.assertTrue(verify_recorded_round(game.result().to_dict()))


if __name__ == "__main__":
    unittest.main()
