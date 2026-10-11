from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from casino.domain.blackjack import BlackjackAction


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class PlayRequest(StrictRequest):
    bet: int = Field(gt=0)
    choice: str = ""
    client_seed: str = Field(default="", max_length=128)
    expected_server_seed_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    idempotency_key: str = Field(min_length=1, max_length=128)


class BlackjackActionRequest(StrictRequest):
    action: BlackjackAction
    idempotency_key: str = Field(min_length=1, max_length=128)


class IdempotencyRequest(StrictRequest):
    idempotency_key: str = Field(min_length=1, max_length=128)


class PlayerResponse(BaseModel):
    name: str
    balance: int
    rounds_played: int
    wins: int
    losses: int
    win_rate: int
    total_wagered: int


class GameInfoResponse(BaseModel):
    id: str
    name: str
    minimum_bet: int
    maximum_bet: int
    paytable: list[dict[str, Any]] | None = None
    pair_multiplier: int | None = None
    theoretical_return_percent: float | None = None
    reel_strips: list[list[str]] | None = None


class RoundResultResponse(BaseModel):
    game_id: str
    game_name: str
    message: str
    bet: int
    payout: int
    profit: int
    details: str
    played_at: str
    symbols: list[str] | None = None
    reel_stops: list[int] | None = None
    fairness: dict[str, Any] | None = None
    rule_version: str | None = None
    rules_fingerprint: str | None = None
    rules_snapshot: dict[str, Any] | None = None
    outcome: dict[str, Any] | None = None
    verification_status: str | None = None


class BlackjackPlayerHandResponse(BaseModel):
    cards: list[str]
    score: int
    bet: int
    status: str
    message: str
    from_split: bool
    doubled: bool


class BlackjackStateResponse(BaseModel):
    bet: int
    player_cards: list[str]
    dealer_cards: list[str]
    player_score: int
    dealer_score: int | None
    status: str
    message: str
    can_double: bool
    can_split: bool
    can_surrender: bool
    available_actions: list[str]
    active_hand_index: int
    insurance_bet: int
    insurance_payout: int
    hands: list[BlackjackPlayerHandResponse]
    rules: dict[str, Any]


class CasinoStateResponse(BaseModel):
    player: PlayerResponse
    games: list[GameInfoResponse]
    history: list[RoundResultResponse]
    blackjack: BlackjackStateResponse | None
    slots_server_seed_hash: str | None = None
    server_seed_hash: str | None = None


class PlayResponse(BaseModel):
    result: RoundResultResponse
    state: CasinoStateResponse


class RefillResponse(BaseModel):
    balance: int
