"""JSON codecs for persisted casino profiles and idempotent responses."""

from __future__ import annotations

import json
from typing import Any

from casino.domain.models import GameResult


class CasinoSaveCodec:
    """Translate persisted JSON columns without performing SQLite operations."""

    @staticmethod
    def encode_history(rounds: list[GameResult]) -> str:
        return json.dumps([round_.to_dict() for round_ in rounds], ensure_ascii=False)

    @staticmethod
    def decode_history(value: str) -> Any:
        return json.loads(value)

    @staticmethod
    def encode_blackjack(snapshot: dict | None) -> str | None:
        return json.dumps(snapshot, ensure_ascii=False) if snapshot is not None else None

    @staticmethod
    def decode_blackjack(value: str | None) -> dict | None:
        return json.loads(value) if value else None

    @staticmethod
    def encode_object(value: dict) -> str:
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def decode_object(value: str) -> dict:
        return json.loads(value)
