from __future__ import annotations

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
from casino.domain.provably_fair import new_server_seed, seed_hash
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
from casino.slot_fairness import (
    new_server_seed as legacy_new_server_seed,
)
from casino.slot_fairness import reel_stops as legacy_reel_stops
from casino.slot_fairness import (
    seed_hash as legacy_seed_hash,
)
from casino.storage import PlayerRepository as LegacyPlayerRepository


def test_legacy_domain_imports_resolve_to_new_modules() -> None:
    assert LegacyBlackjack is DomainBlackjack
    assert LegacyGameRules is DomainGameRules
    assert LegacyRoulette is DomainRoulette
    assert LegacySlotMachine is DomainSlotMachine
    assert LegacyCard is DomainCard
    assert LegacyGameResult is DomainGameResult
    assert LegacyPlayer is DomainPlayer
    assert legacy_verification_status is domain_verification_status
    assert legacy_reel_stops is domain_reel_stops
    assert legacy_new_server_seed is new_server_seed
    assert legacy_seed_hash is seed_hash
    assert LegacyPlayerRepository is SQLitePlayerRepository
    assert LegacyInvalidCasinoCommand is DomainInvalidCasinoCommand
    assert LegacyIdempotencyConflict is ApplicationIdempotencyConflict
    assert LegacyStaleGameState is ApplicationStaleGameState


def test_legacy_session_constructor_uses_application_service(tmp_path: Path) -> None:
    repository = SQLitePlayerRepository(tmp_path / "casino.sqlite3")
    session = CasinoSession(repository)

    assert isinstance(session, CasinoService)
    assert session.state()["player"]["balance"] == 2500
