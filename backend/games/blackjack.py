"""
Объектно-ориентированная модель Блэкджека (American Blackjack, башмак из 6 колод).

Архитектура:
- Card: неизменяемая сущность карты со строгой типизацией масти и ранга
- Shoe: карточный башмак с детерминированным тасованием Фишера-Йетса через HMAC-SHA256
- Hand: рука игрока или дилера с инкапсулированным подсчетом очков и мягких тузов
- BlackjackGame: конечный автомат (FSM) раунда блэкджека
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict
from uuid import uuid4
from games.provably_fair import ProvablyFairEngine

SUITS = ["♠", "♥", "♣", "♦"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

RULES = {
    "dealer_soft_17": "stand",
    "blackjack_payout": "3:2",
    "insurance_payout": "2:1",
    "decks": 6
}

@dataclass(frozen=True)
class Card:
    """Сущность игральной карты."""
    rank: str
    suit: str

    @property
    def value(self) -> int:
        """Базовое очковое значение карты."""
        if self.rank in ("J", "Q", "K"):
            return 10
        if self.rank == "A":
            return 11
        return int(self.rank)

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"

    @classmethod
    def from_str(cls, card_str: str) -> "Card":
        """Парсинг строки вида '10♠' или 'A♥'."""
        if not card_str:
            raise ValueError("Пустая строка карты")
        rank = card_str[:-1]
        suit = card_str[-1]
        return cls(rank=rank, suit=suit)


class Hand:
    """
    Сущность руки в блэкджеке.
    Инкапсулирует вычисление очков, учет мягких тузов и статус.
    """
    def __init__(self, cards: Optional[List[str]] = None, bet: int = 0, from_split: bool = False, doubled: bool = False):
        self.cards: List[str] = cards or []
        self.bet: int = bet
        self.from_split: bool = from_split
        self.doubled: bool = doubled
        self.status: str = "playing"
        self.message: str = "Твой ход"

    @property
    def score(self) -> int:
        """Динамический расчет очков с оптимизацией тузов (11 -> 1)."""
        card_objs = [Card.from_str(c) for c in self.cards if c != "hidden"]
        total = sum(c.value for c in card_objs)
        aces = sum(1 for c in card_objs if c.rank == "A")
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        return total

    @property
    def is_blackjack(self) -> bool:
        """Натуральный блэкджек (21 с первых двух карт без сплита)."""
        return len(self.cards) == 2 and self.score == 21 and not self.from_split

    def to_dict(self) -> dict:
        return {
            "cards": self.cards,
            "score": self.score,
            "bet": self.bet,
            "status": self.status,
            "message": self.message,
            "from_split": self.from_split,
            "doubled": self.doubled
        }


class Shoe:
    """Карточный башмак из N колод."""
    def __init__(self, decks_count: int = 6):
        self.decks_count = decks_count
        self.cards: List[str] = [
            f"{rank}{suit}" for _ in range(decks_count) for suit in SUITS for rank in RANKS
        ]

    def shuffle_provably_fair(self, server_seed: str, client_seed: str, nonce: int):
        """Тасование башмака с криптографическим подтверждением честности."""
        self.cards = ProvablyFairEngine.shuffle_list(self.cards, server_seed, client_seed, nonce)

    def draw(self) -> str:
        """Сдача одной карты из башмака."""
        if not self.cards:
            raise RuntimeError("Башмак пуст")
        return self.cards.pop()


def get_blackjack_info() -> dict:
    return {
        "id": "blackjack",
        "name": "Блэкджек",
        "minimum_bet": 20,
        "maximum_bet": 2000,
        "rules": RULES
    }

def card_value(card: str) -> int:
    return Card.from_str(card).value

def calculate_score(cards: list[str]) -> int:
    hand = Hand(cards=cards)
    return hand.score

def is_blackjack(cards: list[str]) -> bool:
    hand = Hand(cards=cards)
    return hand.is_blackjack

def start_blackjack_round(bet: int, balance: int, server_seed: str = None, client_seed: str = "default_client", nonce: int = 1) -> dict:
    if server_seed is None:
        server_seed = ProvablyFairEngine.generate_server_seed()

    shoe = Shoe(decks_count=6)
    shoe.shuffle_provably_fair(server_seed, client_seed, nonce)

    player_cards = [shoe.draw(), shoe.draw()]
    dealer_cards = [shoe.draw(), shoe.draw()]

    player_hand = Hand(cards=player_cards, bet=bet)
    dealer_upcard = dealer_cards[0]
    dealer_upcard_is_ace = Card.from_str(dealer_upcard).rank == "A"

    initial_status = "insurance" if dealer_upcard_is_ace else "playing"
    initial_message = "Предложена страховка" if dealer_upcard_is_ace else "Твой ход"
    player_hand.message = initial_message

    can_split = (Card.from_str(player_cards[0]).value == Card.from_str(player_cards[1]).value) and (balance >= bet * 2)
    can_double = balance >= bet * 2
    can_surrender = True

    hands = [player_hand.to_dict()]

    available_actions = ["insurance", "decline_insurance"] if dealer_upcard_is_ace else ["hit", "stand"]
    if not dealer_upcard_is_ace:
        if can_double:
            available_actions.append("double")
        if can_split:
            available_actions.append("split")
        if can_surrender:
            available_actions.append("surrender")

    round_id = str(uuid4())
    state = {
        "round_id": round_id,
        "bet": bet,
        "deck": shoe.cards,
        "dealer_cards": dealer_cards,
        "hands": hands,
        "active_hand_index": 0,
        "status": initial_status,
        "message": initial_message,
        "can_double": can_double and not dealer_upcard_is_ace,
        "can_split": can_split and not dealer_upcard_is_ace,
        "can_surrender": can_surrender and not dealer_upcard_is_ace,
        "available_actions": available_actions,
        "insurance_bet": 0,
        "insurance_payout": 0,
        "rules": RULES,
        "fairness": {
            "server_seed": server_seed,
            "server_seed_hash": ProvablyFairEngine.hash_seed(server_seed),
            "client_seed": client_seed,
            "nonce": nonce
        }
    }

    if not dealer_upcard_is_ace and player_hand.is_blackjack:
        return finish_round(state)

    return state

def perform_action(state: dict, action: str, balance: int) -> Tuple[dict, int]:
    status = state["status"]
    if status not in ("playing", "insurance"):
        return state, 0

    deck = state["deck"]
    hands = state["hands"]
    idx = state["active_hand_index"]
    hand = hands[idx]
    dealer_cards = state["dealer_cards"]

    additional_bet = 0

    if action == "insurance":
        ins_bet = hand["bet"] // 2
        state["insurance_bet"] = ins_bet
        additional_bet += ins_bet
        dealer_hand = Hand(cards=dealer_cards)
        if dealer_hand.is_blackjack:
            state["insurance_payout"] = ins_bet * 3
            return finish_round(state), additional_bet
        else:
            state["status"] = "playing"
            state["message"] = "У дилера нет блэкджека"
            _update_available_actions(state, balance - additional_bet)
            return state, additional_bet

    elif action == "decline_insurance":
        dealer_hand = Hand(cards=dealer_cards)
        if dealer_hand.is_blackjack:
            return finish_round(state), 0
        state["status"] = "playing"
        state["message"] = "Твой ход"
        _update_available_actions(state, balance)
        return state, 0

    elif action == "surrender":
        hand["status"] = "surrendered"
        hand["message"] = "Сдача"
        state["status"] = "lost"
        state["message"] = "Сдача половины ставки"
        return finish_round(state), 0

    elif action == "hit":
        new_card = deck.pop()
        hand["cards"].append(new_card)
        hand_obj = Hand(cards=hand["cards"])
        hand["score"] = hand_obj.score

        if hand["score"] > 21:
            hand["status"] = "bust"
            hand["message"] = "Перебор"
            return _advance_or_finish(state), 0
        elif hand["score"] == 21:
            hand["status"] = "standing"
            hand["message"] = "Ожидает дилера"
            return _advance_or_finish(state), 0
        else:
            hand["status"] = "playing"
            state["can_double"] = False
            state["can_split"] = False
            state["can_surrender"] = False
            state["available_actions"] = ["hit", "stand"]
            return state, 0

    elif action == "stand":
        hand["status"] = "standing"
        hand["message"] = "Ожидает дилера"
        return _advance_or_finish(state), 0

    elif action == "double":
        add_bet = hand["bet"]
        hand["bet"] *= 2
        hand["doubled"] = True
        new_card = deck.pop()
        hand["cards"].append(new_card)
        hand_obj = Hand(cards=hand["cards"])
        hand["score"] = hand_obj.score
        if hand["score"] > 21:
            hand["status"] = "bust"
            hand["message"] = "Перебор"
        else:
            hand["status"] = "standing"
            hand["message"] = "Ожидает дилера"
        return _advance_or_finish(state), add_bet

    elif action == "split":
        add_bet = hand["bet"]
        card1 = hand["cards"][0]
        card2 = hand["cards"][1]

        h1 = Hand(cards=[card1, deck.pop()], bet=hand["bet"], from_split=True)
        h2 = Hand(cards=[card2, deck.pop()], bet=hand["bet"], from_split=True)
        h1_dict = h1.to_dict()
        h2_dict = h2.to_dict()
        h2_dict["message"] = "Вторая рука"

        hands[idx] = h1_dict
        hands.insert(idx + 1, h2_dict)
        _update_available_actions(state, balance - add_bet)
        return state, add_bet

    return state, 0

def _advance_or_finish(state: dict) -> dict:
    idx = state["active_hand_index"]
    hands = state["hands"]
    if idx + 1 < len(hands):
        state["active_hand_index"] = idx + 1
        hands[idx + 1]["status"] = "playing"
        hands[idx + 1]["message"] = "Твой ход"
        state["available_actions"] = ["hit", "stand"]
        return state
    return finish_round(state)

def finish_round(state: dict) -> dict:
    deck = state["deck"]
    dealer_cards = state["dealer_cards"]
    hands = state["hands"]

    non_bust_hands = [h for h in hands if h["status"] not in ("bust", "surrendered")]

    dealer_hand = Hand(cards=dealer_cards)
    if non_bust_hands:
        while dealer_hand.score < 17:
            new_card = deck.pop()
            dealer_cards.append(new_card)
            dealer_hand = Hand(cards=dealer_cards)

    dealer_score = dealer_hand.score
    dealer_bust = dealer_score > 21
    dealer_has_bj = dealer_hand.is_blackjack

    total_payout = state.get("insurance_payout", 0)
    outcomes = []

    for h in hands:
        h_obj = Hand(cards=h["cards"], bet=h["bet"], from_split=h.get("from_split", False))
        if h["status"] == "surrendered":
            payout = h["bet"] // 2
            outcomes.append("lost")
        elif h["status"] == "bust":
            payout = 0
            outcomes.append("lost")
        elif h_obj.is_blackjack:
            if dealer_has_bj:
                payout = h["bet"]
                h["message"] = "Ничья (у обоих блэкджек)"
                h["status"] = "push"
                outcomes.append("push")
            else:
                payout = int(h["bet"] * 2.5)
                h["message"] = "Натуральный блэкджек"
                h["status"] = "blackjack"
                outcomes.append("won")
        elif dealer_has_bj:
            payout = 0
            h["message"] = "У дилера блэкджек"
            h["status"] = "lost"
            outcomes.append("lost")
        elif dealer_bust:
            payout = h["bet"] * 2
            h["message"] = "У дилера перебор"
            h["status"] = "won"
            outcomes.append("won")
        elif h_obj.score > dealer_score:
            payout = h["bet"] * 2
            h["message"] = f"Победа ({h_obj.score} против {dealer_score})"
            h["status"] = "won"
            outcomes.append("won")
        elif h_obj.score == dealer_score:
            payout = h["bet"]
            h["message"] = f"Ничья ({h_obj.score})"
            h["status"] = "push"
            outcomes.append("push")
        else:
            payout = 0
            h["message"] = f"Проигрыш ({h_obj.score} против {dealer_score})"
            h["status"] = "lost"
            outcomes.append("lost")

        total_payout += payout

    if all(o == "won" for o in outcomes):
        state_status = "won"
        state_message = "Победа в раздаче"
    elif all(o == "lost" for o in outcomes):
        state_status = "lost"
        state_message = "Проигрыш в раздаче"
    elif all(o == "push" for o in outcomes):
        state_status = "push"
        state_message = "Ничья"
    else:
        state_status = "mixed"
        state_message = "Раунд завершён"

    state["status"] = state_status
    state["message"] = state_message
    state["available_actions"] = []
    state["can_double"] = False
    state["can_split"] = False
    state["can_surrender"] = False
    state["total_payout"] = total_payout
    return state

def _update_available_actions(state: dict, balance: int):
    hands = state["hands"]
    idx = state["active_hand_index"]
    hand = hands[idx]
    actions = ["hit", "stand"]
    can_double = len(hand["cards"]) == 2 and balance >= hand["bet"]
    can_split = (len(hand["cards"]) == 2 and 
                 Card.from_str(hand["cards"][0]).value == Card.from_str(hand["cards"][1]).value and 
                 balance >= hand["bet"] and len(hands) < 4)
    can_surrender = len(hand["cards"]) == 2 and len(hands) == 1

    if can_double:
        actions.append("double")
    if can_split:
        actions.append("split")
    if can_surrender:
        actions.append("surrender")

    state["can_double"] = can_double
    state["can_split"] = can_split
    state["can_surrender"] = can_surrender
    state["available_actions"] = actions

def get_public_state(state: dict | None) -> dict | None:
    if not state:
        return None
    hands = state.get("hands", [])
    idx = min(state.get("active_hand_index", 0), len(hands) - 1) if hands else 0
    active_hand = hands[idx] if hands else None

    is_active = state.get("status") in ("playing", "insurance")
    dealer_cards = state.get("dealer_cards", [])
    dealer_cards_display = [dealer_cards[0], "hidden"] if (is_active and len(dealer_cards) > 0) else dealer_cards
    
    dealer_score_display = (
        Card.from_str(dealer_cards[0]).value 
        if (is_active and len(dealer_cards) > 0) 
        else Hand(cards=dealer_cards).score
    )

    return {
        "bet": state.get("bet", 0),
        "player_cards": active_hand["cards"] if active_hand else [],
        "dealer_cards": dealer_cards_display,
        "player_score": active_hand["score"] if active_hand else 0,
        "dealer_score": dealer_score_display,
        "status": state.get("status", "playing"),
        "message": state.get("message", ""),
        "can_double": state.get("can_double", False),
        "can_split": state.get("can_split", False),
        "can_surrender": state.get("can_surrender", False),
        "active_hand_index": state.get("active_hand_index", 0),
        "available_actions": state.get("available_actions", []),
        "hands": hands,
        "insurance_bet": state.get("insurance_bet", 0),
        "insurance_payout": state.get("insurance_payout", 0),
        "rules": state.get("rules", RULES),
        "fairness": state.get("fairness")
    }
