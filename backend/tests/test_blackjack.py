from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from casino.blackjack import Blackjack
from casino.models import Card
from casino.session import CasinoSession
from casino.storage import PlayerRepository


def rig(game: Blackjack, draws: list[tuple[str, str]]) -> None:
    shoe = [Card(rank, suit) for _ in range(6) for suit in game.suits for rank in game.ranks]
    selected = []
    for rank, suit in draws:
        card = next(card for card in shoe if card.rank == rank and card.suit == suit)
        shoe.remove(card)
        selected.append(card)
    game.deck = shoe + list(reversed(selected))


class BlackjackRulesTests(unittest.TestCase):
    def test_natural_is_three_to_two_and_split_twenty_one_is_not_natural(self) -> None:
        game = Blackjack()
        rig(game, [("A", "♠"), ("9", "♣"), ("K", "♠"), ("7", "♣")])
        game.start(20)
        self.assertEqual(game.result().payout, 50)
        self.assertEqual(game.hand.status, "won")

        game = Blackjack()
        rig(game, [("A", "♠"), ("6", "♣"), ("A", "♥"), ("10", "♣"), ("K", "♠"), ("9", "♥"), ("5", "♦")])
        game.start(20)
        game.split()
        self.assertEqual(game.hand.status, "lost")
        self.assertEqual(game.result().payout, 20)

    def test_insurance_pays_two_to_one_and_dealer_peeks(self) -> None:
        game = Blackjack()
        rig(game, [("8", "♠"), ("A", "♣"), ("8", "♥"), ("K", "♣")])
        game.start(20)
        self.assertEqual(game.hand.status, "insurance")
        self.assertEqual(game.state(10)["available_actions"], ["insurance", "decline_insurance"])
        game.insurance(True)
        self.assertEqual(game.hand.status, "push")
        self.assertEqual(game.result().bet, 30)
        self.assertEqual(game.result().payout, 30)

    def test_surrender_returns_half_and_is_loss(self) -> None:
        game = Blackjack()
        rig(game, [("10", "♠"), ("9", "♣"), ("6", "♥"), ("7", "♣")])
        game.start(20)
        game.surrender()
        self.assertEqual(game.hand.status, "lost")
        self.assertEqual(game.hand.hands[0].status, "surrendered")
        self.assertEqual(game.result().payout, 10)

    def test_ten_upcard_peeks_before_actions_and_split_aces_get_one_card(self) -> None:
        game = Blackjack()
        rig(game, [("8", "♠"), ("K", "♣"), ("8", "♥"), ("A", "♣")])
        game.start(20)
        self.assertEqual(game.hand.status, "lost")
        self.assertEqual(game.available_actions(), [])

        game = Blackjack()
        rig(game, [("A", "♠"), ("6", "♣"), ("A", "♥"), ("10", "♣"), ("K", "♠"), ("9", "♥"), ("5", "♦")])
        game.start(20)
        game.split()
        self.assertEqual([len(h.cards) for h in game.hand.hands], [2, 2])
        self.assertEqual(game.available_actions(), [])
        self.assertEqual(game.hand.hands[0].status, "push")

    def test_split_double_and_dealer_stands_soft_seventeen(self) -> None:
        game = Blackjack()
        rig(game, [("8", "♠"), ("A", "♣"), ("8", "♥"), ("6", "♣"), ("3", "♠"), ("10", "♦"), ("2", "♥")])
        game.start(20)
        game.insurance(False)
        game.split()
        self.assertEqual(len(game.hand.hands), 2)
        self.assertEqual(len(game.hand.hands[1].cards), 1)
        game.double()
        self.assertEqual(game.hand.active_hand_index, 1)
        self.assertEqual(game.hand.hands[0].bet, 40)
        game.stand()
        self.assertEqual(game.score(game.hand.dealer_cards), 17)
        self.assertEqual(len(game.hand.dealer_cards), 2)
        self.assertEqual(game.result().bet, 60)

    def test_ten_value_pair_and_sequential_split_dealing(self) -> None:
        game = Blackjack()
        rig(game, [("10", "♠"), ("9", "♣"), ("K", "♥"), ("8", "♣"), ("A", "♠"), ("2", "♥"), ("4", "♦")])
        game.start(20)
        self.assertIn("split", game.available_actions())
        game.split()
        self.assertEqual([len(h.cards) for h in game.hand.hands], [2, 1])
        self.assertEqual(game.hand.hands[0].cards[-1].rank, "A")
        restored = Blackjack()
        restored.restore_state(game.dump_state())
        restored.stand()
        self.assertEqual(restored.hand.hands[1].cards[-1].rank, "2")

    def test_mixed_split_result_even_when_net_is_push(self) -> None:
        game = Blackjack()
        rig(game, [("8", "♠"), ("9", "♣"), ("8", "♥"), ("8", "♣"), ("10", "♦"), ("2", "♥")])
        game.start(20)
        game.split()
        game.stand()
        game.stand()
        self.assertEqual([h.status for h in game.hand.hands], ["won", "lost"])
        self.assertEqual(game.result().profit, 0)
        self.assertEqual(game.hand.status, "mixed")

    def test_restore_active_round_and_idempotent_session_accounting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            session = CasinoSession(PlayerRepository(Path(directory) / "test.sqlite3"))
            rig(session.blackjack, [("10", "♠"), ("9", "♣"), ("6", "♥"), ("7", "♣")])
            started = session.start_blackjack(20, "start")
            self.assertEqual(started["player"]["balance"], 2480)
            self.assertEqual(session.start_blackjack(20, "start"), started)
            restored = CasinoSession(PlayerRepository(Path(directory) / "test.sqlite3"))
            self.assertEqual(restored.state()["blackjack"]["status"], "playing")
            settled = restored.blackjack_action("surrender", "action")
            self.assertEqual(settled["player"]["balance"], 2490)
            self.assertEqual(restored.blackjack_action("surrender", "action"), settled)


if __name__ == "__main__":
    unittest.main()
