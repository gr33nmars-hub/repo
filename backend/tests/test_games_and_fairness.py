"""
Тесты для проверки объектной модели игр, детерминизма Provably Fair (HMAC-SHA256)
и генератора карт/чисел.
"""

import hashlib
import hmac
import pytest
from games.provably_fair import ProvablyFairEngine
from games.slots import SlotGame
from games.roulette import RouletteGame
from games.blackjack import Card, Hand, Shoe

def test_card_model():
    """Проверка объектной модели игральной карты."""
    card = Card.from_str("10♠")
    assert card.rank == "10"
    assert card.suit == "♠"
    assert card.value == 10

    ace = Card.from_str("A♥")
    assert ace.value == 11

def test_hand_score_calculation():
    """Проверка динамического подсчета очков руки с оптимизацией мягких тузов."""
    hand = Hand(cards=["A♠", "9♦"])
    assert hand.score == 20

    hand_with_two_aces = Hand(cards=["A♠", "A♦", "9♣"])
    # 11 + 1 + 9 = 21
    assert hand_with_two_aces.score == 21

    blackjack_hand = Hand(cards=["A♠", "K♦"])
    assert blackjack_hand.is_blackjack is True

    bust_hand = Hand(cards=["10♠", "8♦", "7♣"])
    assert bust_hand.score == 25

def test_provably_fair_determinism():
    """Проверка детерминизма HMAC-SHA256 генератора."""
    server_seed = "test_server_seed_12345"
    client_seed = "test_client_seed_67890"
    nonce = 42

    val1 = ProvablyFairEngine.get_int(server_seed, client_seed, nonce, 0, 36)
    val2 = ProvablyFairEngine.get_int(server_seed, client_seed, nonce, 0, 36)
    assert val1 == val2
    assert 0 <= val1 <= 36

def test_provably_fair_commitment():
    """Проверка криптографического обязательства SHA-256."""
    seed = ProvablyFairEngine.generate_server_seed()
    expected_hash = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    assert ProvablyFairEngine.hash_seed(seed) == expected_hash

def test_roulette_game_logic():
    """Тестирование правил европейской рулетки."""
    roulette = RouletteGame()
    server_seed = "fixed_seed_roulette"
    client_seed = "client_fixed"
    nonce = 1

    result = roulette.spin(bet=100, choice="red", server_seed=server_seed, client_seed=client_seed, nonce=nonce)
    assert "outcome" in result
    assert "number" in result["outcome"]
    assert 0 <= result["outcome"]["number"] <= 36
    assert result["bet"] == 100

def test_slots_game_logic():
    """Тестирование вращения барабанов и таблицы выплат слотов."""
    slots = SlotGame()
    server_seed = "fixed_seed_slots"
    client_seed = "client_fixed"
    nonce = 1

    result = slots.spin(bet=50, server_seed=server_seed, client_seed=client_seed, nonce=nonce)
    assert len(result["symbols"]) == 3
    assert len(result["reel_stops"]) == 3
    assert result["bet"] == 50
    assert result["payout"] >= 0

def test_shoe_shuffle_determinism():
    """Проверка детерминированного тасования колод Фишера-Йетса."""
    shoe1 = Shoe(decks_count=6)
    shoe2 = Shoe(decks_count=6)

    server_seed = "shoe_seed_abc"
    client_seed = "client_seed_xyz"
    nonce = 7

    shoe1.shuffle_provably_fair(server_seed, client_seed, nonce)
    shoe2.shuffle_provably_fair(server_seed, client_seed, nonce)

    assert shoe1.cards == shoe2.cards
    assert len(shoe1.cards) == 6 * 52
