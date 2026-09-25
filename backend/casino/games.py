from __future__ import annotations

import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol

from casino.models import BlackjackHand, Card, GameResult


class RandomSource(Protocol):
    def choice(self, seq): ...
    def randint(self, a: int, b: int) -> int: ...
    def shuffle(self, x: list) -> None: ...


class SecureRandom:
    """Cryptographically secure game randomness, hidden behind an injectable port."""

    def choice(self, seq):
        return secrets.choice(seq)

    def randint(self, a: int, b: int) -> int:
        return secrets.randbelow(b - a + 1) + a

    def shuffle(self, x: list) -> None:
        secrets.SystemRandom().shuffle(x)


@dataclass(frozen=True, slots=True)
class GameRules:
    minimum_bet: int = 10
    maximum_bet: int = 1_000_000

    def __post_init__(self) -> None:
        if (not isinstance(self.minimum_bet, int) or not isinstance(self.maximum_bet, int)
                or self.minimum_bet < 1 or self.maximum_bet < self.minimum_bet):
            raise ValueError("Invalid bet limits")


class CasinoGame(ABC):
    game_id: str
    name: str

    def __init__(self, rng: RandomSource | None = None, rules: GameRules | None = None) -> None:
        self._rng = rng or SecureRandom()
        self.rules = rules or GameRules()

    @property
    def minimum_bet(self) -> int:
        return self.rules.minimum_bet

    @abstractmethod
    def play(self, bet: int, choice: str = "") -> GameResult:
        """Resolve one game round."""


@dataclass(frozen=True, slots=True)
class SlotRules:
    reels: tuple[tuple[str, ...], ...] = (
        ("🍒", "🍒", "🍒", "🍋", "🍋", "🔔", "💎", "7️⃣"),
        ("🍒", "🍒", "🍒", "🍋", "🍋", "🔔", "💎", "7️⃣"),
        ("🍒", "🍒", "🍒", "🍋", "🍋", "🔔", "💎", "7️⃣"),
    )
    triples: tuple[tuple[str, int], ...] = (("7️⃣", 15), ("💎", 9), ("🔔", 6), ("🍒", 4), ("🍋", 2))
    pair_multiplier: int = 1

    def __post_init__(self) -> None:
        if len(self.reels) != 3 or any(not reel for reel in self.reels):
            raise ValueError("Slots require exactly three non-empty reels")
        payout_symbols = [symbol for symbol, _ in self.triples]
        if not payout_symbols or len(set(payout_symbols)) != len(payout_symbols) or any(not symbol for symbol in payout_symbols):
            raise ValueError("Slot paytable symbols must be non-empty and unique")
        if any(multiplier < 1 for _, multiplier in self.triples) or self.pair_multiplier < 0:
            raise ValueError("Invalid slot paytable")
        if any(symbol not in {entry[0] for entry in self.triples} for reel in self.reels for symbol in reel):
            raise ValueError("Every slot symbol must have a configured triple payout")


class SlotMachine(CasinoGame):
    game_id, name = "slots", "Слоты"

    def __init__(self, rng: RandomSource | None = None, rules: GameRules | None = None, slot_rules: SlotRules | None = None):
        super().__init__(rng, rules)
        self.slot_rules = slot_rules or SlotRules()
        self._payouts = dict(self.slot_rules.triples)

    def play(self, bet: int, choice: str = "") -> GameResult:
        result = [self._rng.choice(reel) for reel in self.slot_rules.reels]
        details = "  ·  ".join(result)
        if result[0] == result[1] == result[2]:
            multiplier = self._payouts[result[0]]
            payout, message = bet * multiplier, f"ДЖЕКПОТ · выплата ×{multiplier}"
        elif len(set(result)) == 2:
            payout, message = bet * self.slot_rules.pair_multiplier, "Пара символов · ставка возвращена"
        else:
            payout, message = 0, "Комбинация не собрана"
        return GameResult(self.game_id, self.name, message, bet, payout, details)


RED_NUMBERS = frozenset({1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36})
EUROPEAN_WHEEL = tuple(range(37))


@dataclass(frozen=True, slots=True)
class RouletteRules:
    color_return_multiplier: int = 2
    number_return_multiplier: int = 36

    def __post_init__(self) -> None:
        if self.color_return_multiplier < 1 or self.number_return_multiplier < 1:
            raise ValueError("Roulette return multipliers must be positive")


class Roulette(CasinoGame):
    game_id, name = "roulette", "Рулетка"
    choices = frozenset({"red", "black", "zero"})

    def __init__(self, rng: RandomSource | None = None, rules: GameRules | None = None, roulette_rules: RouletteRules | None = None):
        super().__init__(rng, rules)
        self.roulette_rules = roulette_rules or RouletteRules()

    def play(self, bet: int, choice: str = "red") -> GameResult:
        if choice not in self.choices:
            raise ValueError("Выбери красное, чёрное или зеро")
        number = self._rng.choice(EUROPEAN_WHEEL)
        color = "zero" if number == 0 else "red" if number in RED_NUMBERS else "black"
        colors = {"red": "красное", "black": "чёрное", "zero": "зелёное"}
        multiplier = self.roulette_rules.number_return_multiplier if choice == "zero" else self.roulette_rules.color_return_multiplier
        payout = bet * multiplier if choice == color else 0
        message = "Шарик остановился на твоём секторе" if payout else "Шарик прошёл мимо"
        return GameResult(self.game_id, self.name, message, bet, payout, f"{number} · {colors[color]}")


@dataclass(frozen=True, slots=True)
class BlackjackRules:
    dealer_hits_soft_17: bool = False
    natural_numerator: int = 3
    natural_denominator: int = 2
    allow_double: bool = True

    def __post_init__(self) -> None:
        if self.natural_numerator <= self.natural_denominator or self.natural_denominator < 1:
            raise ValueError("Invalid natural blackjack payout")


class Blackjack(CasinoGame):
    """Stateful blackjack round with explicit legal-action checks."""

    game_id, name = "blackjack", "Блэкджек"
    suits = ("♠", "♥", "♣", "♦")
    ranks = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")

    def __init__(self, rng: RandomSource | None = None, rules: GameRules | None = None, blackjack_rules: BlackjackRules | None = None):
        super().__init__(rng, rules)
        self.blackjack_rules = blackjack_rules or BlackjackRules()
        self.hand: BlackjackHand | None = None
        self.deck: list[Card] = []
        self.natural = False

    @staticmethod
    def score(cards: list[Card]) -> int:
        total = sum(card.value for card in cards)
        aces = sum(card.rank == "A" for card in cards)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    @staticmethod
    def _soft(cards: list[Card]) -> bool:
        return any(card.rank == "A" for card in cards) and sum(1 if card.rank == "A" else card.value for card in cards) + 10 <= 21

    def _draw(self) -> Card:
        if not self.deck:
            raise ValueError("В колоде не осталось карт")
        return self.deck.pop()

    def start(self, bet: int) -> BlackjackHand:
        if self.hand is not None and self.hand.status == "playing":
            raise ValueError("Сначала закончи текущую раздачу")
        self.deck = [Card(rank, suit) for suit in self.suits for rank in self.ranks]
        self._rng.shuffle(self.deck)
        self.hand = BlackjackHand(bet, [self._draw(), self._draw()], [self._draw(), self._draw()])
        player_natural = self.score(self.hand.player_cards) == 21
        dealer_natural = self.score(self.hand.dealer_cards) == 21
        self.natural = player_natural and len(self.hand.player_cards) == 2
        if player_natural or dealer_natural:
            if player_natural and dealer_natural:
                self.hand.status, self.hand.message = "push", "Блэкджек у обоих · ничья"
            elif player_natural:
                self.hand.status, self.hand.message = "won", "Блэкджек · натуральная выплата 3:2"
            else:
                self.hand.status, self.hand.message = "lost", "У дилера натуральный блэкджек"
        return self.hand

    def hit(self) -> BlackjackHand:
        hand = self._require_active()
        hand.player_cards.append(self._draw())
        player_score = self.score(hand.player_cards)
        if player_score > 21:
            hand.status, hand.message = "lost", "Перебор · дилер забирает раунд"
        elif player_score == 21:
            self.stand()
        return hand

    def stand(self) -> BlackjackHand:
        hand = self._require_active()
        while self.score(hand.dealer_cards) < 17 or (self.blackjack_rules.dealer_hits_soft_17 and self.score(hand.dealer_cards) == 17 and self._soft(hand.dealer_cards)):
            hand.dealer_cards.append(self._draw())
        player_score, dealer_score = self.score(hand.player_cards), self.score(hand.dealer_cards)
        if dealer_score > 21 or player_score > dealer_score:
            hand.status, hand.message = "won", "Ты обыграл дилера"
        elif player_score == dealer_score:
            hand.status, hand.message = "push", "Ничья · ставка возвращена"
        else:
            hand.status, hand.message = "lost", "Дилер оказался ближе к 21"
        return hand

    def double(self) -> BlackjackHand:
        hand = self._require_active()
        if not self.blackjack_rules.allow_double or len(hand.player_cards) != 2:
            raise ValueError("Удвоить можно только на первых двух картах")
        hand.bet *= 2
        hand.player_cards.append(self._draw())
        if self.score(hand.player_cards) > 21:
            hand.status, hand.message = "lost", "Перебор после удвоения"
        else:
            self.stand()
        return hand

    def play(self, bet: int, choice: str = "") -> GameResult:
        hand = self.start(bet)
        while hand.status == "playing" and self.score(hand.player_cards) < 17:
            self.hit()
        if hand.status == "playing":
            self.stand()
        return self.result()

    def result(self) -> GameResult:
        hand = self.hand
        if hand is None or hand.status == "playing":
            raise ValueError("Раунд ещё не завершён")
        if hand.status == "won" and self.natural:
            payout = hand.bet * (self.blackjack_rules.natural_denominator + self.blackjack_rules.natural_numerator) // self.blackjack_rules.natural_denominator
        elif hand.status == "won":
            payout = hand.bet * 2
        elif hand.status == "push":
            payout = hand.bet
        else:
            payout = 0
        details = (f"Твои карты: {' '.join(card.label for card in hand.player_cards)} ({self.score(hand.player_cards)})"
                   f"  ·  Дилер: {' '.join(card.label for card in hand.dealer_cards)} ({self.score(hand.dealer_cards)})")
        return GameResult(self.game_id, self.name, hand.message, hand.bet, payout, details)

    def state(self) -> dict | None:
        hand = self.hand
        if hand is None:
            return None
        active, reveal = hand.status == "playing", hand.status != "playing"
        return {"bet": hand.bet, "player_cards": [c.label for c in hand.player_cards],
                "dealer_cards": [c.label for c in hand.dealer_cards] if reveal else [hand.dealer_cards[0].label, "hidden"],
                "player_score": self.score(hand.player_cards), "dealer_score": self.score(hand.dealer_cards) if reveal else None,
                "status": hand.status, "message": hand.message, "can_double": active and len(hand.player_cards) == 2 and self.blackjack_rules.allow_double}

    def dump_state(self) -> dict | None:
        if self.hand is None:
            return None
        if self.hand.status != "playing":
            return {"bet": self.hand.bet, "player_cards": [c.label for c in self.hand.player_cards],
                    "dealer_cards": [c.label for c in self.hand.dealer_cards], "deck": [c.label for c in self.deck],
                    "status": self.hand.status, "message": self.hand.message, "natural": self.natural}
        return {"bet": self.hand.bet, "player_cards": [c.label for c in self.hand.player_cards],
                "dealer_cards": [c.label for c in self.hand.dealer_cards], "deck": [c.label for c in self.deck],
                "status": "playing", "message": self.hand.message, "natural": self.natural}

    def restore_state(self, state: dict | None) -> None:
        if not state:
            self.hand, self.deck, self.natural = None, [], False
            return
        self.hand = BlackjackHand(int(state["bet"]), [self._parse_card(x) for x in state["player_cards"]],
                                  [self._parse_card(x) for x in state["dealer_cards"]], str(state["status"]), str(state.get("message", "Твой ход")))
        self.deck = [self._parse_card(x) for x in state["deck"]]
        all_cards = self.hand.player_cards + self.hand.dealer_cards + self.deck
        labels = [card.label for card in all_cards]
        if (self.hand.bet < 1 or self.hand.status not in {"playing", "won", "lost", "push"}
                or len(labels) != 52 or len(set(labels)) != 52):
            self.hand, self.deck = None, []
            raise ValueError("Некорректная колода в сохранённой раздаче блэкджека")
        self.natural = bool(state.get("natural", False))

    def _parse_card(self, label: str) -> Card:
        if len(label) < 2 or label[:-1] not in self.ranks or label[-1] not in self.suits:
            raise ValueError("Некорректное сохранённое состояние блэкджека")
        return Card(label[:-1], label[-1])

    def _require_active(self) -> BlackjackHand:
        if self.hand is None or self.hand.status != "playing":
            raise ValueError("Сейчас нет активной раздачи")
        return self.hand
