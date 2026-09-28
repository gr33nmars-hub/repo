from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from casino.application.errors import (
    IdempotencyConflict as ApplicationIdempotencyConflict,
)
from casino.application.errors import (
    StaleGameState as ApplicationStaleGameState,
)
from casino.application.service import CasinoService
from casino.blackjack import Blackjack as LegacyBlackjack
from casino.core import GameRules as LegacyGameRules
from casino.domain.blackjack import Blackjack as DomainBlackjack
from casino.domain.core import GameRules as DomainGameRules
from casino.domain.errors import InvalidCasinoCommand as DomainInvalidCasinoCommand
from casino.domain.games import Roulette as DomainRoulette
from casino.domain.games import SlotMachine as DomainSlotMachine
from casino.domain.models import Card as DomainCard
from casino.domain.models import GameResult as DomainGameResult
from casino.domain.models import Player as DomainPlayer
from casino.domain.round_verifier import verification_status as domain_verification_status
from casino.domain.slot_fairness import reel_stops as domain_reel_stops
from casino.errors import IdempotencyConflict as LegacyIdempotencyConflict
from casino.errors import InvalidCasinoCommand as LegacyInvalidCasinoCommand
from casino.errors import StaleGameState as LegacyStaleGameState
from casino.games import Roulette as LegacyRoulette
from casino.games import SlotMachine as LegacySlotMachine
from casino.models import Card as LegacyCard
from casino.models import GameResult as LegacyGameResult
from casino.models import Player as LegacyPlayer
from casino.persistence.sqlite import PlayerRepository as SQLitePlayerRepository
from casino.round_verifier import verification_status as legacy_verification_status
from casino.session import CasinoSession
from casino.slot_fairness import reel_stops as legacy_reel_stops
from casino.storage import PlayerRepository as LegacyPlayerRepository


class CompatibilityFacadeTests(unittest.TestCase):
    def test_legacy_domain_imports_resolve_to_new_modules(self) -> None:
        self.assertIs(LegacyBlackjack, DomainBlackjack)
        self.assertIs(LegacyGameRules, DomainGameRules)
        self.assertIs(LegacyRoulette, DomainRoulette)
        self.assertIs(LegacySlotMachine, DomainSlotMachine)
        self.assertIs(LegacyCard, DomainCard)
        self.assertIs(LegacyGameResult, DomainGameResult)
        self.assertIs(LegacyPlayer, DomainPlayer)
        self.assertIs(legacy_verification_status, domain_verification_status)
        self.assertIs(legacy_reel_stops, domain_reel_stops)
        self.assertIs(LegacyPlayerRepository, SQLitePlayerRepository)
        self.assertIs(LegacyInvalidCasinoCommand, DomainInvalidCasinoCommand)
        self.assertIs(LegacyIdempotencyConflict, ApplicationIdempotencyConflict)
        self.assertIs(LegacyStaleGameState, ApplicationStaleGameState)

    def test_legacy_session_constructor_uses_application_service(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLitePlayerRepository(Path(directory) / "casino.sqlite3")
            session = CasinoSession(repository)

        self.assertIsInstance(session, CasinoService)
        self.assertEqual(session.state()["player"]["balance"], 2500)


if __name__ == "__main__":
    unittest.main()
