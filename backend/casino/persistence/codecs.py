"""JSON codecs for persisted casino profiles and idempotent responses."""

from __future__ import annotations

import json

from casino.domain.models import GameResult


class CasinoSaveCodec:
    """Translate persisted JSON columns without performing SQLite operations."""

    @staticmethod
    def encode_history(rounds: list[GameResult]) -> str:
        return json.dumps([round_.to_dict() for round_ in rounds], ensure_ascii=False)

    @staticmethod
    def decode_history(value: str) -> list[dict]:
        decoded = json.loads(value)
        if not isinstance(decoded, list) or any(not isinstance(item, dict) for item in decoded):
            raise ValueError("Saved round history must be a list of objects")
        return decoded

    @staticmethod
    def encode_blackjack(snapshot: dict | None) -> str | None:
        return json.dumps(snapshot, ensure_ascii=False) if snapshot is not None else None

    @staticmethod
    def decode_blackjack(value: str | None) -> dict | None:
        if not value:
            return None
        decoded = json.loads(value)
        if not isinstance(decoded, dict):
            raise ValueError("Saved blackjack state must be an object")
        return decoded

    @staticmethod
    def encode_object(value: dict) -> str:
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def decode_object(value: str) -> dict:
        decoded = json.loads(value)
        if not isinstance(decoded, dict):
            raise ValueError("Saved response must be an object")
        return decoded
