from __future__ import annotations

import secrets
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar

from .models import GameResult

T = TypeVar("T")


class RandomSource(Protocol):
    def choice(self, seq: Sequence[T]) -> T: ...
    def shuffle(self, x: list[T]) -> None: ...


class GameCatalogItem(Protocol):
    def catalog_info(self) -> dict[str, object]: ...


class SecureRandom:
    def choice(self, seq: Sequence[T]) -> T:
        return secrets.choice(seq)

    def shuffle(self, x: list[T]) -> None:
        secrets.SystemRandom().shuffle(x)


@dataclass(frozen=True, slots=True)
class GameRules:
    minimum_bet: int = 10
    maximum_bet: int = 1_000_000

    def __post_init__(self) -> None:
        if (
            type(self.minimum_bet) is not int
            or type(self.maximum_bet) is not int
            or self.minimum_bet < 1
            or self.maximum_bet < self.minimum_bet
        ):
            raise ValueError("Invalid bet limits")


class CasinoGame(ABC):
    game_id: str
    name: str

    def __init__(self, rng: RandomSource | None = None, rules: GameRules | None = None) -> None:
        self._rng = rng if rng is not None else SecureRandom()
        self.rules = rules if rules is not None else GameRules()

    @property
    def minimum_bet(self) -> int:
        return self.rules.minimum_bet

    @abstractmethod
    def play(self, bet: int, choice: str = "") -> GameResult:
        pass

    def catalog_info(self) -> dict[str, object]:
        return {
            "id": self.game_id,
            "name": self.name,
            "minimum_bet": self.minimum_bet,
            "maximum_bet": self.rules.maximum_bet,
        }
