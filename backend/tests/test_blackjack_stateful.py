from __future__ import annotations

import random
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from casino.application.service import CasinoService
from casino.persistence.sqlite import PlayerRepository
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, precondition, rule


class BlackjackPersistenceMachine(RuleBasedStateMachine):
    """Generate legal blackjack actions and check persistence invariants after each one."""

    def __init__(self) -> None:
        super().__init__()
        self._temporary_directory = tempfile.TemporaryDirectory()
        self._database_path = Path(self._temporary_directory.name) / "casino.sqlite3"
        self._random_seed = 0
        self._request_number = 0
        self._session: CasinoService | None = None

    @initialize(seed=st.integers(min_value=0, max_value=2**32 - 1))
    def open_profile(self, seed: int) -> None:
        self._random_seed = seed
        self._reload()

    def _reload(self) -> None:
        self._session = CasinoService(PlayerRepository(self._database_path))
        self._session.blackjack._rng = random.Random(self._random_seed)

    def _next_request_key(self) -> str:
        self._request_number += 1
        return f"stateful-{self._request_number}"

    def _can_start(self) -> bool:
        if self._session is None or self._session.player.balance < 10:
            return False
        hand = self._session.blackjack.hand
        return hand is None or hand.status not in {"playing", "insurance"}

    def _can_take_action(self, action: str) -> bool:
        if self._session is None:
            return False
        hand = self._session.blackjack.hand
        if hand is None or hand.status not in {"playing", "insurance"}:
            return False
        return action in self._session.blackjack.available_actions(self._session.player.balance)

    def _act(self, action: str) -> None:
        assert self._session is not None
        self._session.blackjack_action(action, self._next_request_key())  # type: ignore[arg-type]

    @precondition(lambda self: self._can_start())
    @rule()
    def start_round(self) -> None:
        assert self._session is not None
        self._session.start_blackjack(10, self._next_request_key())

    @precondition(lambda self: self._can_take_action("hit"))
    @rule()
    def hit(self) -> None:
        self._act("hit")

    @precondition(lambda self: self._can_take_action("stand"))
    @rule()
    def stand(self) -> None:
        self._act("stand")

    @precondition(lambda self: self._can_take_action("double"))
    @rule()
    def double(self) -> None:
        self._act("double")

    @precondition(lambda self: self._can_take_action("split"))
    @rule()
    def split(self) -> None:
        self._act("split")

    @precondition(lambda self: self._can_take_action("surrender"))
    @rule()
    def surrender(self) -> None:
        self._act("surrender")

    @precondition(lambda self: self._can_take_action("insurance"))
    @rule()
    def take_insurance(self) -> None:
        self._act("insurance")

    @precondition(lambda self: self._can_take_action("decline_insurance"))
    @rule()
    def decline_insurance(self) -> None:
        self._act("decline_insurance")

    @precondition(lambda self: self._session is not None)
    @rule()
    def reload_from_disk(self) -> None:
        assert self._session is not None
        before = self._session.state()
        self._reload()
        assert self._session.state() == before

    @invariant()
    def wallet_matches_committed_ledger(self) -> None:
        if self._session is None:
            return
        balance = self._session.state()["player"]["balance"]
        assert balance >= 0
        with closing(sqlite3.connect(self._database_path)) as connection:
            ledger_total = 0
            for delta, recorded_balance in connection.execute(
                "SELECT delta,balance_after FROM ledger ORDER BY id"
            ):
                ledger_total += delta
                assert ledger_total >= 0
                assert ledger_total == recorded_balance
            saved_balance = connection.execute("SELECT balance FROM profile WHERE id=1").fetchone()[
                0
            ]
        assert ledger_total == saved_balance == balance

    def teardown(self) -> None:
        self._temporary_directory.cleanup()


BlackjackPersistenceMachine.TestCase.settings = settings(
    max_examples=12,
    stateful_step_count=16,
    derandomize=True,
    database=None,
    deadline=None,
)
BlackjackPersistenceTests = BlackjackPersistenceMachine.TestCase


if __name__ == "__main__":
    unittest.main()
