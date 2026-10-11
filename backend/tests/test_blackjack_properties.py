from __future__ import annotations

import hashlib
import random
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from casino.application.service import CasinoService
from casino.persistence.sqlite import PlayerRepository
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, precondition, rule


class BlackjackPersistenceMachine(RuleBasedStateMachine):
    """Generate legal game traces and check the committed wallet after every step."""

    def __init__(self) -> None:
        super().__init__()
        self._temporary_directory = tempfile.TemporaryDirectory()
        self._database_path = Path(self._temporary_directory.name) / "casino.sqlite3"
        self._random_seed = 0
        self._request_number = 0
        self._session: CasinoService | None = None
        self._seed_counter = 0
        self._seed_patcher = None

    @initialize(seed=st.integers(min_value=0, max_value=2**32 - 1))
    def open_profile(self, seed: int) -> None:
        self._random_seed = seed
        self._seed_counter = 0
        self._seed_patcher = patch("secrets.token_hex", side_effect=self._next_seed)
        self._seed_patcher.start()
        self._reload()

    def _next_seed(self, nbytes: int = 32) -> str:
        value = hashlib.sha256(f"{self._random_seed}:{self._seed_counter}".encode()).hexdigest()
        self._seed_counter += 1
        return value[: nbytes * 2]

    def _reload(self) -> None:
        self._session = CasinoService(PlayerRepository(self._database_path))
        self._session.blackjack._rng = random.Random(self._random_seed)

    def _next_request_key(self) -> str:
        self._request_number += 1
        return f"property-{self._request_number}"

    def _can_start(self) -> bool:
        if self._session is None or self._session.player.balance < 50:
            return False
        hand = self._session.blackjack.hand
        return hand is None or hand.status not in {"playing", "insurance"}

    def _can_act(self) -> bool:
        if self._session is None:
            return False
        hand = self._session.blackjack.hand
        return hand is not None and hand.status in {"playing", "insurance"}

    @precondition(lambda self: self._can_start())
    @rule(bet=st.sampled_from((10, 20, 30, 50)))
    def start_round(self, bet: int) -> None:
        assert self._session is not None
        self._session.start_blackjack(bet, self._next_request_key())

    @precondition(lambda self: self._can_act())
    @rule(action_index=st.integers(min_value=0, max_value=2**16))
    def play_legal_action(self, action_index: int) -> None:
        assert self._session is not None
        actions = self._session.blackjack.available_actions(self._session.player.balance)
        assert actions
        action = actions[action_index % len(actions)]
        self._session.blackjack_action(action, self._next_request_key())

    @precondition(lambda self: self._session is not None)
    @rule()
    def restart_service(self) -> None:
        assert self._session is not None
        before = self._session.state()
        self._reload()
        assert self._session.state() == before

    @invariant()
    def wallet_and_ledger_remain_consistent(self) -> None:
        if self._session is None:
            return

        balance = self._session.state()["player"]["balance"]
        assert balance >= 0
        with closing(sqlite3.connect(self._database_path)) as connection:
            committed_balance = 0
            for delta, balance_after in connection.execute(
                "SELECT delta, balance_after FROM ledger ORDER BY id"
            ):
                committed_balance += delta
                assert committed_balance >= 0
                assert committed_balance == balance_after
        assert committed_balance == balance

    def teardown(self) -> None:
        if self._seed_patcher is not None:
            self._seed_patcher.stop()
        self._temporary_directory.cleanup()


BlackjackPersistenceMachine.TestCase.settings = settings(
    max_examples=12,
    stateful_step_count=16,
    derandomize=True,
    database=None,
    deadline=None,
)
BlackjackPersistenceTests = BlackjackPersistenceMachine.TestCase
