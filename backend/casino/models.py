from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class GameResult:
    game_id: str
    game_name: str
    message: str
    bet: int
    payout: int
    details: str
    played_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @property
    def profit(self) -> int:
        return self.payout - self.bet

    def to_dict(self) -> dict:
        return {
            "game_id": self.game_id,
            "game_name": self.game_name,
            "message": self.message,
            "bet": self.bet,
            "payout": self.payout,
            "profit": self.profit,
            "details": self.details,
            "played_at": self.played_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GameResult:
        return cls(
            game_id=str(data["game_id"]),
            game_name=str(data["game_name"]),
            message=str(data["message"]),
            bet=int(data["bet"]),
            payout=int(data["payout"]),
            details=str(data.get("details", "")),
            played_at=str(data.get("played_at", "")),
        )


@dataclass(slots=True)
class Player:
    name: str = "Гость"
    balance: int = 2500
    rounds: list[GameResult] = field(default_factory=list)

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
            "rounds": [round_.to_dict() for round_ in self.rounds[-100:]],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Player:
        return cls(
            name=str(data.get("name", "Гость")),
            balance=max(0, int(data.get("balance", 2500))),
            rounds=[GameResult.from_dict(item) for item in data.get("rounds", [])][-100:],
        )


@dataclass(slots=True)
class Card:
    rank: str
    suit: str

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


@dataclass(slots=True)
class BlackjackHand:
    bet: int
    player_cards: list[Card]
    dealer_cards: list[Card]
    status: str = "playing"
    message: str = "Твой ход"
