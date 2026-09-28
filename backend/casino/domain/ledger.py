"""Typed virtual-chip movements recorded by the persistent wallet ledger."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LedgerEntryType(str, Enum):
    OPENING_BALANCE = "opening_balance"
    BET_STAKE = "bet_stake"
    GAME_PAYOUT = "game_payout"
    BLACKJACK_STAKE = "blackjack_stake"
    BLACKJACK_DOUBLE_STAKE = "blackjack_double_stake"
    BLACKJACK_SPLIT_STAKE = "blackjack_split_stake"
    BLACKJACK_INSURANCE_STAKE = "blackjack_insurance_stake"
    BLACKJACK_PAYOUT = "blackjack_payout"
    DEMO_REFILL = "demo_refill"
    PROFILE_ADJUSTMENT = "profile_adjustment"


_DEBIT_TYPES = frozenset(
    {
        LedgerEntryType.BET_STAKE,
        LedgerEntryType.BLACKJACK_STAKE,
        LedgerEntryType.BLACKJACK_DOUBLE_STAKE,
        LedgerEntryType.BLACKJACK_SPLIT_STAKE,
        LedgerEntryType.BLACKJACK_INSURANCE_STAKE,
    }
)
_CREDIT_TYPES = frozenset(
    {
        LedgerEntryType.OPENING_BALANCE,
        LedgerEntryType.GAME_PAYOUT,
        LedgerEntryType.BLACKJACK_PAYOUT,
        LedgerEntryType.DEMO_REFILL,
    }
)


@dataclass(frozen=True, slots=True)
class LedgerMovement:
    entry_type: LedgerEntryType
    delta: int
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.entry_type, LedgerEntryType):
            raise TypeError("Ledger movement requires a known LedgerEntryType")
        if type(self.delta) is not int:
            raise TypeError("Ledger movement delta must be an integer")
        if self.entry_type in _DEBIT_TYPES and self.delta >= 0:
            raise ValueError("Stake movements must debit virtual chips")
        if self.entry_type in _CREDIT_TYPES and self.delta < 0:
            raise ValueError("Credit movements cannot debit virtual chips")
        if self.entry_type is LedgerEntryType.PROFILE_ADJUSTMENT:
            if type(self.reason) is not str or not self.reason.strip():
                raise ValueError("Profile adjustments require a non-empty reason")
        elif self.reason is not None:
            raise ValueError("Only profile adjustments may include a reason")

    @classmethod
    def adjustment(cls, delta: int, reason: str) -> LedgerMovement:
        return cls(LedgerEntryType.PROFILE_ADJUSTMENT, delta, reason)
