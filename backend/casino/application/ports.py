"""Persistence contract used by application services."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Protocol

from casino.domain.ledger import LedgerMovement
from casino.domain.models import Player


class CasinoReadUnitOfWork(Protocol):
    """Read operations available inside a consistent persistence transaction."""

    def load(self) -> Player: ...

    def load_blackjack(self) -> dict | None: ...

    def validate_active_blackjack_round(
        self, round_id: str | None, initial_bet: int, total_stake: int
    ) -> None: ...

    def revision(self) -> int: ...

    def load_slot_seed(self) -> str: ...

    def load_server_seed(self) -> str: ...

    def get_request_response(
        self, request_key: str, *, signature: str | None = None
    ) -> dict | None: ...


class CasinoUnitOfWork(CasinoReadUnitOfWork, Protocol):
    """Write operations added to the transaction-scoped persistence view."""

    def set_slot_seed(self, seed: str) -> None: ...

    def set_server_seed(self, seed: str) -> None: ...

    def save(
        self,
        player: Player,
        blackjack: dict | None = None,
        *,
        request_key: str,
        signature: str,
        ledger_entries: list[LedgerMovement],
        response: dict,
        round_id: str | None = None,
    ) -> dict: ...


class CasinoRepository(Protocol):
    """Begin transaction-scoped units of work for application services."""

    def read_transaction(self) -> AbstractContextManager[CasinoReadUnitOfWork]: ...

    def write_transaction(self) -> AbstractContextManager[CasinoUnitOfWork]: ...
