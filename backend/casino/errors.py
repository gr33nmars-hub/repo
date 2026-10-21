"""Фасад обратной совместимости для исключений приложения и домена."""

from casino.application.errors import IdempotencyConflict, StaleGameState
from casino.domain.errors import InvalidCasinoCommand

__all__ = ["IdempotencyConflict", "InvalidCasinoCommand", "StaleGameState"]
