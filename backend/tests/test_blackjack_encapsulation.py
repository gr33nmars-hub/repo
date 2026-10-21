from __future__ import annotations

import pytest
from casino.domain.blackjack import Blackjack
from casino.domain.errors import InvalidCasinoCommand
from casino.domain.models import Card
from casino.domain.provably_fair import seed_hash
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
    exposed_cards = exposed_hand.hands[0].cards
    assert isinstance(exposed_cards, tuple)
    with pytest.raises(AttributeError):
        exposed_cards.clear()

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


def test_blackjack_fairness_data_does_not_leak_through_start_or_result() -> None:
    server_seed = "01" * 32
    proof = {
        "server_seed": server_seed,
        "server_seed_hash": seed_hash(server_seed),
        "client_seed": "client",
        "nonce": 0,
    }
    game = Blackjack()
    game.start(20, fairness=proof, server_seed=server_seed, client_seed="client")

    proof["client_seed"] = "changed after start"
    assert game.hand is not None
    assert game.hand.fairness == {**proof, "client_seed": "client"}

    while game.hand and game.hand.status in {"insurance", "playing"}:
        action = "decline_insurance" if game.hand.status == "insurance" else "stand"
        game.act(action, balance=100)

    result = game.result()
    assert result.fairness is not None
    result.fairness["client_seed"] = "changed after result"
    assert result.outcome is not None
    draw_order = result.outcome["draw_order"]
    draw_events = result.outcome["draw_events"]
    assert isinstance(draw_order, list)
    assert isinstance(draw_events, list)
    original_draw = draw_order[0]
    draw_order[0] = "A♠" if original_draw != "A♠" else "K♠"
    original_target = draw_events[0]["target"]
    draw_events[0]["target"] = "dealer" if original_target != "dealer" else "hand:0"
    assert game.hand is not None
    assert game.hand.fairness == {**proof, "client_seed": "client"}
    assert game.hand.draw_order is not None
    assert game.hand.draw_order[0] == original_draw
    assert game.hand.draw_events is not None
    assert game.hand.draw_events[0]["target"] == original_target


def test_restore_rejects_doubled_wager_without_a_double_action() -> None:
    game = Blackjack()
    rig_pair_of_eights(game)
    game.start(20)
    snapshot = game.snapshot()
    assert snapshot.hand is not None
    snapshot.hand.hands[0].bet *= 2

    with pytest.raises(ValueError, match="Некорректное состояние раздачи"):
        Blackjack().restore_snapshot(snapshot)
