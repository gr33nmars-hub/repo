from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .oop import ComparableEntity
from .rule_metadata import validate_rule_metadata


@dataclass(slots=True, eq=False)
class GameResult(ComparableEntity):
    game_id: str
    game_name: str
    message: str
    bet: int
    payout: int
    details: str
    symbols: list[str] | None = None
    reel_stops: list[int] | None = None
    fairness: dict | None = None
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
            raise ValueError("Game result text fields must be strings")
        if (
            type(self.bet) is not int
            or self.bet < 1
            or type(self.payout) is not int
            or self.payout < 0
        ):
            raise ValueError(
                "Game result requires a positive integer bet and non-negative integer payout"
            )
        if self.symbols is not None and (
            type(self.symbols) is not list
            or any(type(symbol) is not str for symbol in self.symbols)
        ):
            raise ValueError("Game result symbols must be a list of strings")
        if self.reel_stops is not None and (
            type(self.reel_stops) is not list
            or any(type(stop) is not int or stop < 0 for stop in self.reel_stops)
        ):
            raise ValueError("Game result reel stops must be non-negative integers")
        if self.round_id is not None and (type(self.round_id) is not str or not self.round_id):
            raise ValueError("Game result round id must be a non-empty string")
        validate_rule_metadata(
            self.rule_version,
            self.rules_fingerprint,
            self.rules_snapshot,
            self.outcome,
        )

    def comparison_key(self) -> tuple[object, ...]:
        return (
            self.round_id or "",
            self.played_at,
            self.game_id,
            self.game_name,
            self.bet,
            self.payout,
            self.details,
        )

    @property
    def profit(self) -> int:
        return self.payout - self.bet

    def to_dict(self) -> dict:
        result = {
            "game_id": self.game_id,
            "game_name": self.game_name,
            "message": self.message,
            "bet": self.bet,
            "payout": self.payout,
            "profit": self.profit,
            "details": self.details,
            "played_at": self.played_at,
        }
        if self.symbols is not None:
            result["symbols"] = self.symbols
        if self.reel_stops is not None:
            result["reel_stops"] = self.reel_stops
        if self.fairness is not None:
            result["fairness"] = self.fairness
        if self.round_id is not None:
            result["round_id"] = self.round_id
        if self.rule_version is not None:
            result["rule_version"] = self.rule_version
            result["rules_fingerprint"] = self.rules_fingerprint
            result["rules_snapshot"] = self.rules_snapshot
            result["outcome"] = self.outcome
        return result

    @classmethod
    def from_dict(cls, data: dict) -> GameResult:
        if not isinstance(data, dict):
            raise ValueError("Game result must be an object")
        required_text = ("game_id", "game_name", "message")
        if any(type(data.get(key)) is not str for key in required_text):
            raise ValueError("Game result is missing required text fields")
        if type(data.get("bet")) is not int or type(data.get("payout")) is not int:
            raise ValueError("Game result bet and payout must be integers")
        if "details" in data and type(data["details"]) is not str:
            raise ValueError("Game result details must be a string")
        if "played_at" in data and type(data["played_at"]) is not str:
            raise ValueError("Game result timestamp must be a string")
        if data.get("symbols") is not None and (
            type(data["symbols"]) is not list
            or any(type(symbol) is not str for symbol in data["symbols"])
        ):
            raise ValueError("Game result symbols must be a list of strings")
        if data.get("reel_stops") is not None and (
            type(data["reel_stops"]) is not list
            or any(type(stop) is not int or stop < 0 for stop in data["reel_stops"])
        ):
            raise ValueError("Game result reel stops must be non-negative integers")
        if data.get("fairness") is not None and type(data["fairness"]) is not dict:
            raise ValueError("Game result fairness proof must be an object")
        for key in ("rule_version", "rules_fingerprint"):
            if key in data and data[key] is not None and type(data[key]) is not str:
                raise ValueError(f"Game result {key} must be a string")
        if (
            "round_id" in data
            and data["round_id"] is not None
            and type(data["round_id"]) is not str
        ):
            raise ValueError("Game result round_id must be a string")
        for key in ("rules_snapshot", "outcome"):
            if key in data and data[key] is not None and type(data[key]) is not dict:
                raise ValueError(f"Game result {key} must be an object")
        return cls(
            game_id=data["game_id"],
            game_name=data["game_name"],
            message=data["message"],
            bet=data["bet"],
            payout=data["payout"],
            details=data.get("details", ""),
            symbols=data.get("symbols"),
            reel_stops=data.get("reel_stops"),
            fairness=data.get("fairness"),
            played_at=data.get("played_at", ""),
            round_id=data.get("round_id"),
            rule_version=data.get("rule_version"),
            rules_fingerprint=data.get("rules_fingerprint"),
            rules_snapshot=data.get("rules_snapshot"),
            outcome=data.get("outcome"),
        )


@dataclass(slots=True, eq=False)
class Player(ComparableEntity):
    name: str = "Гость"
    balance: int = 2500
    rounds: list[GameResult] = field(default_factory=list)

    def __post_init__(self) -> None:
        if type(self.name) is not str or not self.name:
            raise ValueError("Player name must be a non-empty string")
        if type(self.balance) is not int or self.balance < 0:
            raise ValueError("Player balance must be a non-negative integer")
        if type(self.rounds) is not list or any(
            not isinstance(round_, GameResult) for round_ in self.rounds
        ):
            raise ValueError("Player rounds must contain game results")

    def comparison_key(self) -> tuple[object, ...]:
        return (self.name, self.balance, tuple(self.rounds))

    def debit(self, amount: int) -> None:
        if type(amount) is not int or amount < 0:
            raise ValueError("Debit must be a non-negative integer")
        if amount > self.balance:
            raise ValueError("На балансе недостаточно фишек")
        self.balance -= amount

    def credit(self, amount: int) -> None:
        if type(amount) is not int or amount < 0:
            raise ValueError("Credit must be a non-negative integer")
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

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "balance": self.balance,
            "rounds": [round_.to_dict() for round_ in self.rounds],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Player:
        if not isinstance(data, dict):
            raise ValueError("Player profile must be an object")
        name = data.get("name", "Гость")
        balance = data.get("balance", 2500)
        rounds = data.get("rounds", [])
        if type(name) is not str or not name:
            raise ValueError("Player name must be a non-empty string")
        if type(balance) is not int or balance < 0:
            raise ValueError("Player balance must be a non-negative integer")
        if type(rounds) is not list:
            raise ValueError("Player history must be a list")
        return cls(
            name=name,
            balance=balance,
            rounds=[GameResult.from_dict(item) for item in data.get("rounds", [])],
        )


@dataclass(frozen=True, slots=True, eq=False)
class Card(ComparableEntity):
    rank: str
    suit: str

    def __post_init__(self) -> None:
        if self.rank not in {"A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"}:
            raise ValueError("Invalid card rank")
        if self.suit not in {"♠", "♥", "♣", "♦"}:
            raise ValueError("Invalid card suit")

    def comparison_key(self) -> tuple[object, ...]:
        return (self.rank, self.suit)

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
