from __future__ import annotations

import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol

from casino.models import Card, GameResult


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


from casino.blackjack import Blackjack, BlackjackRules  # noqa: E402
