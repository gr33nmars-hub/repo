from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from casino.errors import IdempotencyConflict
from casino.session import CasinoSession
from casino.slot_fairness import new_server_seed, reel_stops, seed_hash
from casino.storage import PlayerRepository


class SlotFairnessTests(unittest.TestCase):
    def test_hmac_stop_vector_is_stable(self) -> None:
        self.assertEqual(
            seed_hash("00" * 32), "60e05bd1b195af2f94112fa7197a5c88289058840ce7c6df9693756bc6250f55"
        )
        self.assertEqual(reel_stops("00" * 32, "client-seed", [8, 8, 8]), [1, 2, 1])

    def test_reel_stop_mapping_is_repeatable_and_within_each_strip(self) -> None:
        server_seed = new_server_seed()
        first = reel_stops(server_seed, "client-seed", [8, 11, 1])
        self.assertEqual(first, reel_stops(server_seed, "client-seed", [8, 11, 1]))
        self.assertEqual(len(first), 3)
        self.assertTrue(
            all(0 <= stop < length for stop, length in zip(first, [8, 11, 1], strict=True))
        )
        with self.assertRaises(ValueError):
            reel_stops(server_seed, "client-seed", [8, 0, 1])

    def test_slot_spin_reveals_previous_commitment_and_rotates_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = PlayerRepository(Path(directory) / "casino.sqlite3")
            session = CasinoSession(repository)
            committed_hash = session.state()["slots_server_seed_hash"]

            response = session.play("slots", 10, "", "spin-key", "client-seed")
            proof = response["result"]["fairness"]
            self.assertEqual(seed_hash(proof["server_seed"]), committed_hash)
            self.assertEqual(proof["server_seed_hash"], committed_hash)
            self.assertEqual(
                response["result"]["reel_stops"],
                reel_stops(proof["server_seed"], "client-seed", [8, 8, 8]),
            )
            next_commitment = response["state"]["slots_server_seed_hash"]
            self.assertNotEqual(next_commitment, committed_hash)

            retry = session.play("slots", 10, "", "spin-key", "client-seed")
            self.assertEqual(retry, response)
            self.assertEqual(session.state()["slots_server_seed_hash"], next_commitment)
            restored = CasinoSession(PlayerRepository(repository.path))
            self.assertEqual(restored.state()["slots_server_seed_hash"], next_commitment)

            with self.assertRaises(IdempotencyConflict):
                session.play("slots", 10, "", "spin-key", "different-seed")

    def test_stale_client_commitment_cannot_spin_a_new_seed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = PlayerRepository(Path(directory) / "casino.sqlite3")
            first = CasinoSession(repository)
            second = CasinoSession(PlayerRepository(repository.path))
            announced_hash = first.state()["slots_server_seed_hash"]
            committed_result = second.play("slots", 10, "", "other-spin", "client-seed")

            with self.assertRaisesRegex(ValueError, "Seed для барабанов изменился"):
                first.play("slots", 10, "", "stale-spin", "client-seed", announced_hash)
            self.assertEqual(
                CasinoSession(PlayerRepository(repository.path)).state()["player"]["balance"],
                committed_result["state"]["player"]["balance"],
            )


if __name__ == "__main__":
    unittest.main()
