from __future__ import annotations

import pytest
from casino.domain.blackjack import Blackjack
from casino.domain.errors import InvalidCasinoCommand
from casino.domain.models import Card
from casino.domain.shoe import Shoe


def rig_pair_of_eights(game: Blackjack) -> None:
    cards = [Card(rank, suit) for _ in range(6) for suit in game.suits for rank in game.ranks]
    selected = []
    for rank, suit in (("8", "♠"), ("6", "♣"), ("8", "♥"), ("10", "♣")):
        card = next(card for card in cards if card.rank == rank and card.suit == suit)
        cards.remove(card)
        selected.append(card)
    game._shoe = Shoe(cards + list(reversed(selected)))


def test_hand_property_returns_detached_state() -> None:
    game = Blackjack()
    game.start(20)

    exposed_hand = game.hand
    assert exposed_hand is not None
    exposed_hand.hands[0].cards.clear()

    assert len(game.hand.hands[0].cards) == 2


@pytest.mark.parametrize("action", ["double", "split"])
def test_additional_stake_actions_reject_insufficient_balance_without_mutation(
    action: str,
) -> None:
    game = Blackjack()
    rig_pair_of_eights(game)
    game.start(20)
    before = game.hand

    assert not hasattr(game, "double")
    assert not hasattr(game, "split")
    with pytest.raises(InvalidCasinoCommand):
        game.act(action, balance=19)

    assert game.hand == before


def test_action_rejects_missing_or_wrong_phase_round() -> None:
    game = Blackjack()

    with pytest.raises(InvalidCasinoCommand):
        game.act("hit", balance=100)

    game.start(20)
    if game.hand.status == "insurance":
        game.act("decline_insurance", balance=100)
    if game.hand.status == "playing":
        game.act("stand", balance=100)
    with pytest.raises(InvalidCasinoCommand):
        game.act("hit", balance=100)


def test_shoe_returns_immutable_card_sequence_and_fair_shuffle_is_repeatable() -> None:
    first = Shoe.full(6, Blackjack.suits, Blackjack.ranks)
    second = Shoe.full(6, Blackjack.suits, Blackjack.ranks)

    first.shuffle_fair("01" * 32, "client", 0)
    second.shuffle_fair("01" * 32, "client", 0)
    remaining = first.remaining_cards

    assert len(remaining) == 312
    assert remaining == second.remaining_cards
    assert isinstance(remaining, tuple)
    with pytest.raises(AttributeError):
        remaining.append(Card("A", "♠"))
    assert first.draw() == remaining[-1]
    assert first.remaining_count == 311
