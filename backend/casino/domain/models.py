from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .rule_metadata import validate_rule_metadata


@dataclass(slots=True)
class GameResult:
    game_id: str
    game_name: str
    message: str
    bet: int
    payout: int
    details: str
    symbols: list[str] | None = None
    reel_stops: list[int] | None = None
    fairness: dict[str, Any] | None = None
    played_at: str = field(
        default_factory=lambda: datetime.now().astimezone().isoformat(timespec="seconds")
    )
    round_id: str | None = None
    rule_version: str | None = None
    rules_fingerprint: str | None = None
    rules_snapshot: dict[str, Any] | None = None
    outcome: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if any(
            type(value) is not str
            for value in (
                self.game_id,
                self.game_name,
                self.message,
                self.details,
                self.played_at,
            )
        ):
            raise ValueError("Текстовые поля результата игры должны быть строками")
        if (
            type(self.bet) is not int
            or self.bet < 1
            or type(self.payout) is not int
            or self.payout < 0
        ):
            raise ValueError(
                "Ставка должна быть положительным целым числом, а выплата — неотрицательным"
            )
        if self.symbols is not None and (
            type(self.symbols) is not list
            or any(type(symbol) is not str for symbol in self.symbols)
        ):
            raise ValueError("Символы результата игры должны быть списком строк")
        if self.reel_stops is not None and (
            type(self.reel_stops) is not list
            or any(type(stop) is not int or stop < 0 for stop in self.reel_stops)
        ):
            raise ValueError(
                "Остановки барабанов слота должны быть неотрицательными целыми числами"
            )
        if self.fairness is not None:
            if type(self.fairness) is not dict:
                raise ValueError("Подтверждение честности раунда должно быть объектом")
            try:
                json.dumps(self.fairness, ensure_ascii=False, allow_nan=False)
            except (TypeError, ValueError) as error:
                raise ValueError("Подтверждение честности должно быть JSON-совместимым") from error
        if self.round_id is not None and (type(self.round_id) is not str or not self.round_id):
            raise ValueError("Идентификатор раунда должен быть непустой строкой")
        validate_rule_metadata(
            self.rule_version,
            self.rules_fingerprint,
            self.rules_snapshot,
            self.outcome,
        )

    @property
    def profit(self) -> int:
        return self.payout - self.bet


@dataclass(slots=True)
class Player:
    name: str = "Гость"
    balance: int = 2500
    rounds: list[GameResult] = field(default_factory=list)

    def __post_init__(self) -> None:
        if type(self.name) is not str or not self.name:
            raise ValueError("Имя игрока должно быть непустой строкой")
        if type(self.balance) is not int or self.balance < 0:
            raise ValueError("Баланс игрока (balance) должен быть неотрицательным целым числом")
        if type(self.rounds) is not list or any(
            not isinstance(round_, GameResult) for round_ in self.rounds
        ):
            raise ValueError("История раундов игрока должна содержать объекты результатов игры")

    def debit(self, amount: int) -> None:
        if type(amount) is not int or amount < 0:
            raise ValueError("Сумма списания должна быть неотрицательным целым числом")
        if amount > self.balance:
            raise ValueError("На балансе недостаточно фишек")
        self.balance -= amount

    def credit(self, amount: int) -> None:
        if type(amount) is not int or amount < 0:
            raise ValueError("Сумма начисления должна быть неотрицательным целым числом")
        self.balance += amount

    @property
    def wins(self) -> int:
        return sum(round_.profit > 0 for round_ in self.rounds)

    @property
    def losses(self) -> int:
        return sum(round_.profit < 0 for round_ in self.rounds)

    @property
    def total_wagered(self) -> int:
        return sum(round_.bet for round_ in self.rounds)


@dataclass(frozen=True, slots=True)
class Card:
    rank: str
    suit: str

    def __post_init__(self) -> None:
        if self.rank not in {"A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"}:
            raise ValueError("Недопустимое достоинство карты")
        if self.suit not in {"♠", "♥", "♣", "♦"}:
            raise ValueError("Недопустимая масть карты")

    @property
    def value(self) -> int:
        if self.rank == "A":
            return 11
        if self.rank in {"J", "Q", "K"}:
            return 10
        return int(self.rank)

    @property
    def label(self) -> str:
        return f"{self.rank}{self.suit}"

    @property
    def is_red(self) -> bool:
        return self.suit in {"♥", "♦"}
