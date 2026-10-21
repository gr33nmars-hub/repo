from __future__ import annotations

from pathlib import Path

import pytest
from casino.application.errors import IdempotencyConflict
from casino.application.service import CasinoService
from casino.domain.slot_fairness import new_server_seed, reel_stops, seed_hash
from casino.persistence.sqlite import PlayerRepository


def test_hmac_stop_vector_is_stable() -> None:
    assert (
        seed_hash("00" * 32) == "60e05bd1b195af2f94112fa7197a5c88289058840ce7c6df9693756bc6250f55"
    )
    assert reel_stops("00" * 32, "client-seed", [8, 8, 8]) == [1, 2, 1]


def test_reel_stop_mapping_is_repeatable_and_within_each_strip() -> None:
    server_seed = new_server_seed()
    first = reel_stops(server_seed, "client-seed", [8, 11, 1])

    assert first == reel_stops(server_seed, "client-seed", [8, 11, 1])
    assert len(first) == 3
    assert all(0 <= stop < length for stop, length in zip(first, [8, 11, 1], strict=True))
    with pytest.raises(ValueError):
        reel_stops(server_seed, "client-seed", [8, 0, 1])


def test_slot_spin_reveals_previous_commitment_and_rotates_once(tmp_path: Path) -> None:
    repository = PlayerRepository(tmp_path / "casino.sqlite3")
    session = CasinoService(repository)
    committed_hash = session.state()["slots_server_seed_hash"]

    response = session.play("slots", 10, "", "spin-key", "client-seed")
    proof = response["result"]["fairness"]
    assert seed_hash(proof["server_seed"]) == committed_hash
    assert proof["server_seed_hash"] == committed_hash
    assert response["result"]["reel_stops"] == reel_stops(
        proof["server_seed"], "client-seed", [8, 8, 8]
    )
    next_commitment = response["state"]["slots_server_seed_hash"]
    assert next_commitment != committed_hash

    retry = session.play("slots", 10, "", "spin-key", "client-seed")
    assert retry == response
    assert session.state()["slots_server_seed_hash"] == next_commitment
    restored = CasinoService(PlayerRepository(repository.path))
    assert restored.state()["slots_server_seed_hash"] == next_commitment

    with pytest.raises(IdempotencyConflict):
        session.play("slots", 10, "", "spin-key", "different-seed")


def test_stale_client_commitment_cannot_spin_a_new_seed(tmp_path: Path) -> None:
    repository = PlayerRepository(tmp_path / "casino.sqlite3")
    first = CasinoService(repository)
    second = CasinoService(PlayerRepository(repository.path))
    announced_hash = first.state()["slots_server_seed_hash"]
    committed_result = second.play("slots", 10, "", "other-spin", "client-seed")

    with pytest.raises(ValueError, match="Seed для барабанов изменился"):
        first.play("slots", 10, "", "stale-spin", "client-seed", announced_hash)
    assert (
        CasinoService(PlayerRepository(repository.path)).state()["player"]["balance"]
        == committed_result["state"]["player"]["balance"]
    )
