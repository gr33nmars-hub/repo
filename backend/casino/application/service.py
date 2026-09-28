from __future__ import annotations

import json
from threading import RLock

from casino.application import commands as casino_commands
from casino.application.ports import CasinoReadUnitOfWork, CasinoRepository
from casino.application.queries import casino_state
from casino.domain.blackjack import Blackjack, BlackjackAction, BlackjackRules
from casino.domain.core import CasinoGame
from casino.domain.errors import InvalidCasinoCommand
from casino.domain.games import Roulette, SlotMachine
from casino.domain.models import GameResult


class CasinoService:
    """Application service coordinating domain games and atomic local persistence."""

    REFILL_AMOUNT = 1000

    def __init__(self, repository: CasinoRepository) -> None:
        self.repository = repository
        self._lock = RLock()
        with self.repository.read_transaction() as unit_of_work:
            self.player = unit_of_work.load()
            saved_blackjack = unit_of_work.load_blackjack()
            self.blackjack = Blackjack(blackjack_rules=BlackjackRules())
            self.blackjack.restore_state(saved_blackjack)
            self._validate_active_blackjack_ledger(unit_of_work)
            self._revision = unit_of_work.revision()
            self._slots_seed = unit_of_work.load_slot_seed()
        self.games: dict[str, CasinoGame] = {
            "slots": SlotMachine(),
            "roulette": Roulette(),
        }

    def _validate_active_blackjack_ledger(self, unit_of_work: CasinoReadUnitOfWork) -> None:
        hand = self.blackjack.hand
        if hand is not None and hand.status in {"playing", "insurance"}:
            unit_of_work.validate_active_blackjack_round(hand.round_id, hand.initial_bet, hand.bet)

    def _refresh_if_stale(self, unit_of_work: CasinoReadUnitOfWork) -> None:
        revision = unit_of_work.revision()
        if revision == self._revision:
            return
        self.player = unit_of_work.load()
        self.blackjack.restore_state(unit_of_work.load_blackjack())
        self._validate_active_blackjack_ledger(unit_of_work)
        self._revision = revision
        self._slots_seed = unit_of_work.load_slot_seed()

    def refresh_state(self) -> dict:
        """Refresh this process's snapshot before serving a read request."""
        with self._lock, self.repository.read_transaction() as unit_of_work:
            self._refresh_if_stale(unit_of_work)
            return self.state()

    def state(self) -> dict:
        with self._lock:
            return casino_state(
                self.player,
                (*self.games.values(), self.blackjack),
                self.blackjack,
                self._slots_seed,
            )

    def _validate_bet(self, game: CasinoGame | Blackjack, bet: int) -> None:
        if not game.minimum_bet <= bet <= game.rules.maximum_bet:
            raise InvalidCasinoCommand(
                f"Ставка должна быть от {game.minimum_bet} до {game.rules.maximum_bet} фишек"
            )
        if bet > self.player.balance:
            raise InvalidCasinoCommand("На балансе недостаточно фишек для этой ставки")
        if game.game_id == "blackjack" and bet % 2:
            raise InvalidCasinoCommand(
                "Для точной натуральной выплаты 3:2 ставка в блэкджеке должна быть чётной"
            )

    def _cached_request(
        self, request_key: str, signature: str, unit_of_work: CasinoReadUnitOfWork
    ) -> dict | None:
        if not request_key or len(request_key) > 128:
            raise InvalidCasinoCommand("Нужен уникальный ключ запроса")
        return unit_of_work.get_request_response(request_key, signature=signature)

    @staticmethod
    def _request_signature(operation: str, **payload: object) -> str:
        return json.dumps(
            {"operation": operation, **payload},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def play(
        self,
        game_id: str,
        bet: int,
        choice: str,
        request_key: str,
        client_seed: str = "",
        expected_server_seed_hash: str | None = None,
    ) -> dict:
        return casino_commands.play_game(
            self, game_id, bet, choice, request_key, client_seed, expected_server_seed_hash
        )

    def start_blackjack(self, bet: int, request_key: str) -> dict:
        return casino_commands.start_blackjack(self, bet, request_key)

    def blackjack_action(self, action: BlackjackAction, request_key: str) -> dict:
        return casino_commands.blackjack_action(self, action, request_key)

    def refill(self, request_key: str) -> int:
        return casino_commands.refill(self, request_key)

    def _record(self, result: GameResult) -> None:
        self.player.rounds.append(result)
