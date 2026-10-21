from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from casino.application.service import CasinoService
from casino.domain.errors import InvalidCasinoCommand
from casino.domain.models import GameResult
from casino.persistence.sqlite import PlayerRepository


def test_parallel_distinct_requests_cannot_overdraw_shared_wallet(tmp_path: Path) -> None:
    database = tmp_path / "casino.sqlite3"
    initial = CasinoService(PlayerRepository(database))
    sessions = [CasinoService(PlayerRepository(database)) for _ in range(2)]

    def lose(bet: int, _: list[int]) -> GameResult:
        return GameResult("slots", "Слоты", "Проигрыш", bet, 0, "Тест")

    for session in [initial, *sessions]:
        session.games["slots"].play_at_stops = lose

    initial.play("slots", 2490, "", "prepare-low-balance")

    request_count = 50
    start_together = Barrier(request_count)

    def attempt(index: int) -> dict | None:
        start_together.wait(timeout=10)
        try:
            return sessions[index % len(sessions)].play(
                "slots", 10, "", f"parallel-request-{index}"
            )
        except InvalidCasinoCommand:
            return None

    with ThreadPoolExecutor(max_workers=request_count) as pool:
        outcomes = list(pool.map(attempt, range(request_count)))

    assert sum(outcome is not None for outcome in outcomes) == 1
    assert sum(outcome is None for outcome in outcomes) == 49

    state = CasinoService(PlayerRepository(database)).state()
    assert state["player"]["balance"] == 0
    assert state["player"]["rounds_played"] == 2

    with sqlite3.connect(database) as connection:
        balance = 0
        for delta, balance_after in connection.execute(
            "SELECT delta, balance_after FROM ledger ORDER BY id"
        ):
            balance += delta
            assert balance >= 0
            assert balance == balance_after

        saved_balance = connection.execute("SELECT balance FROM profile WHERE id=1").fetchone()[0]

    assert balance == saved_balance == 0
