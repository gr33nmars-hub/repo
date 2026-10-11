"""State-changing casino use cases, each committed in one repository transaction."""

from __future__ import annotations

import secrets
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Protocol

from casino.application.errors import IdempotencyConflict, StaleGameState
from casino.application.ports import CasinoRepository, CasinoUnitOfWork
from casino.domain.blackjack import Blackjack, BlackjackAction
from casino.domain.core import CasinoGame
from casino.domain.errors import InvalidCasinoCommand
from casino.domain.games import Roulette, SlotMachine
from casino.domain.ledger import LedgerEntryType, LedgerMovement
from casino.domain.models import GameResult, Player
from casino.domain.provably_fair import bounded_int
from casino.domain.slot_fairness import reel_stops, seed_hash


class CasinoCommandContext(Protocol):
    repository: CasinoRepository

    @property
    def _lock(self) -> AbstractContextManager[object]: ...

    player: Player
    blackjack: Blackjack
    games: dict[str, CasinoGame]
    _server_seed: str
    _revision: int
    REFILL_AMOUNT: int

    def _refresh_if_stale(self, unit_of_work: CasinoUnitOfWork) -> None: ...

    def _validate_bet(self, game: CasinoGame | Blackjack, bet: int) -> None: ...

    def _cached_request(
        self, request_key: str, signature: str, unit_of_work: CasinoUnitOfWork
    ) -> dict | None: ...

    def _request_signature(self, operation: str, **payload: object) -> str: ...

    def state(self) -> dict: ...

    def _record(self, result: GameResult) -> None: ...


@contextmanager
def _command_transaction(service: CasinoCommandContext) -> Iterator[CasinoUnitOfWork]:
    """Restore the in-memory snapshot if work or the database commit fails."""
    with service._lock:
        snapshot = None
        try:
            with service.repository.write_transaction() as unit_of_work:
                service._refresh_if_stale(unit_of_work)
                snapshot = (
                    service.player.balance,
                    service.player.rounds.copy(),
                    service.blackjack.dump_state(),
                    service.blackjack.deck.copy(),
                    service._server_seed,
                    service._revision,
                )
                yield unit_of_work
        except BaseException:
            if snapshot is not None:
                (
                    balance,
                    rounds,
                    blackjack_state,
                    blackjack_deck,
                    server_seed,
                    revision,
                ) = snapshot
                service.player.balance = balance
                service.player.rounds = rounds
                service.blackjack.restore_state(blackjack_state)
                service.blackjack.deck = blackjack_deck
                service._server_seed = server_seed
                service._revision = revision
            raise


def play_game(
    service: CasinoCommandContext,
    game_id: str,
    bet: int,
    choice: str,
    request_key: str,
    client_seed: str = "",
    expected_server_seed_hash: str | None = None,
) -> dict:
    with _command_transaction(service) as unit_of_work:
        signature = service._request_signature(
            "game.play",
            game_id=game_id,
            bet=bet,
            choice=choice,
            client_seed=client_seed,
            expected_server_seed_hash=expected_server_seed_hash,
        )
        cached = service._cached_request(request_key, signature, unit_of_work)
        if cached is not None:
            return cached
        if game_id == "blackjack":
            raise InvalidCasinoCommand("Для блэкджека сначала начни новую раздачу")
        if service.blackjack.hand and service.blackjack.hand.status in {"playing", "insurance"}:
            raise InvalidCasinoCommand("Сначала закончи текущую раздачу блэкджека")
        game = service.games.get(game_id)
        if game is None:
            raise InvalidCasinoCommand("Такой игры нет")
        service._validate_bet(game, bet)
        before = service.player.balance
        before_rounds = service.player.rounds.copy()
        previous_seed = service._server_seed
        try:
            if expected_server_seed_hash is not None and expected_server_seed_hash != seed_hash(
                previous_seed
            ):
                message = (
                    "Seed для барабанов изменился. Состояние обновлено; проверь стол."
                    if game_id == "slots"
                    else "Seed игры изменился. Состояние обновлено; проверь стол."
                )
                raise StaleGameState(message)
            actual_client_seed = client_seed or request_key
            if len(actual_client_seed) > 128:
                raise InvalidCasinoCommand("Слишком длинный client seed")
            if isinstance(game, SlotMachine):
                stops = reel_stops(
                    previous_seed,
                    actual_client_seed,
                    [len(reel) for reel in game.slot_rules.reels],
                )
                result = game.play_at_stops(bet, stops)
                result.fairness = {
                    "server_seed": previous_seed,
                    "server_seed_hash": seed_hash(previous_seed),
                    "client_seed": actual_client_seed,
                    "nonce": 0,
                }
            elif isinstance(game, Roulette):
                result = game.play_at_number(
                    bet,
                    choice,
                    bounded_int(previous_seed, actual_client_seed, 0, "roulette", 0, 37),
                )
                result.fairness = {
                    "server_seed": previous_seed,
                    "server_seed_hash": seed_hash(previous_seed),
                    "client_seed": actual_client_seed,
                    "nonce": 0,
                }
            else:
                result = game.play(bet, choice)
            service._server_seed = secrets.token_hex(32)
            unit_of_work.set_server_seed(service._server_seed)
            service.player.debit(bet)
            service.player.credit(result.payout)
            service._record(result)
            response = {"result": result.to_dict(), "state": service.state()}
            unit_of_work.save(
                service.player,
                service.blackjack.dump_state(),
                request_key=request_key,
                signature=signature,
                ledger_entries=[
                    LedgerMovement(LedgerEntryType.BET_STAKE, -bet),
                    LedgerMovement(LedgerEntryType.GAME_PAYOUT, result.payout),
                ],
                response=response,
            )
            service._revision = unit_of_work.revision()
        except Exception:
            service.player.balance = before
            service.player.rounds = before_rounds
            service._server_seed = previous_seed
            raise
        return response


def start_blackjack(
    service: CasinoCommandContext,
    bet: int,
    request_key: str,
    client_seed: str = "",
    expected_server_seed_hash: str | None = None,
    legacy_signature_compatible: bool = False,
) -> dict:
    with _command_transaction(service) as unit_of_work:
        signature = service._request_signature(
            "blackjack.start",
            bet=bet,
            client_seed=client_seed,
            expected_server_seed_hash=expected_server_seed_hash,
        )
        try:
            cached = service._cached_request(request_key, signature, unit_of_work)
        except IdempotencyConflict:
            # Older releases bound blackjack.start retries to bet alone. The old
            # request DTO did not accept seeds, so only that legacy payload is safe
            # to match against its historical signature.
            if (
                not legacy_signature_compatible
                or client_seed
                or expected_server_seed_hash is not None
            ):
                raise
            legacy_signature = service._request_signature("blackjack.start", bet=bet)
            cached = service._cached_request(request_key, legacy_signature, unit_of_work)
        if cached is not None:
            return cached
        if service.blackjack.hand and service.blackjack.hand.status in {"playing", "insurance"}:
            raise InvalidCasinoCommand("Сначала закончи текущую раздачу")
        service._validate_bet(service.blackjack, bet)
        before = service.player.balance
        before_rounds = service.player.rounds.copy()
        previous = service.blackjack.dump_state()
        previous_deck = service.blackjack.deck.copy()
        previous_seed = service._server_seed
        try:
            if expected_server_seed_hash is not None and expected_server_seed_hash != seed_hash(
                previous_seed
            ):
                raise StaleGameState("Seed игры изменился. Состояние обновлено; проверь стол.")
            actual_client_seed = client_seed or request_key
            if len(actual_client_seed) > 128:
                raise InvalidCasinoCommand("Слишком длинный client seed")
            proof = {
                "server_seed": previous_seed,
                "server_seed_hash": seed_hash(previous_seed),
                "client_seed": actual_client_seed,
                "nonce": 0,
            }
            service.player.debit(bet)
            hand = service.blackjack.start(
                bet,
                fairness=proof,
                server_seed=previous_seed,
                client_seed=actual_client_seed,
            )
            entries = [LedgerMovement(LedgerEntryType.BLACKJACK_STAKE, -bet)]
            if hand.status not in {"playing", "insurance"}:
                result = service.blackjack.result()
                service.player.credit(result.payout)
                service._record(result)
                entries.append(LedgerMovement(LedgerEntryType.BLACKJACK_PAYOUT, result.payout))
                service._server_seed = secrets.token_hex(32)
                unit_of_work.set_server_seed(service._server_seed)
            state = service.state()
            unit_of_work.save(
                service.player,
                service.blackjack.dump_state(),
                request_key=request_key,
                signature=signature,
                ledger_entries=entries,
                response=state,
                round_id=hand.round_id,
            )
            service._revision = unit_of_work.revision()
        except Exception:
            service.player.balance = before
            service.blackjack.restore_state(previous)
            service.blackjack.deck = previous_deck
            service.player.rounds = before_rounds
            service._server_seed = previous_seed
            raise
        return state


def blackjack_action(
    service: CasinoCommandContext, action: BlackjackAction, request_key: str
) -> dict:
    with _command_transaction(service) as unit_of_work:
        signature = service._request_signature("blackjack.action", action=action)
        cached = service._cached_request(request_key, signature, unit_of_work)
        if cached is not None:
            return cached
        hand = service.blackjack.hand
        if hand is None or hand.status not in {"playing", "insurance"}:
            raise InvalidCasinoCommand("Сейчас нет активной раздачи")
        before_balance, before_state = service.player.balance, service.blackjack.dump_state()
        before_rounds = service.player.rounds.copy()
        try:
            entries: list[LedgerMovement] = []
            transition = service.blackjack.act(action, service.player.balance)
            for movement in transition.ledger_entries:
                if movement.delta < 0:
                    service.player.debit(-movement.delta)
                else:
                    service.player.credit(movement.delta)
            if transition.result is not None:
                service._record(transition.result)
                service._server_seed = secrets.token_hex(32)
                unit_of_work.set_server_seed(service._server_seed)
            entries.extend(transition.ledger_entries)
            response = service.state()
            unit_of_work.save(
                service.player,
                service.blackjack.dump_state(),
                request_key=request_key,
                signature=signature,
                ledger_entries=entries,
                response=response,
                round_id=hand.round_id,
            )
            service._revision = unit_of_work.revision()
        except Exception:
            service.player.balance = before_balance
            service.blackjack.restore_state(before_state)
            service.player.rounds = before_rounds
            raise
        return response


def refill(service: CasinoCommandContext, request_key: str) -> int:
    with _command_transaction(service) as unit_of_work:
        signature = service._request_signature("wallet.refill")
        cached = service._cached_request(request_key, signature, unit_of_work)
        if cached is not None:
            return int(cached["balance"])
        if service.blackjack.hand and service.blackjack.hand.status in {"playing", "insurance"}:
            raise InvalidCasinoCommand("Пополнение доступно после завершения текущей раздачи")
        if service.player.balance >= service.blackjack.minimum_bet:
            raise InvalidCasinoCommand(
                "Пополнение станет доступно, когда не хватит на минимальную ставку"
            )
        before = service.player.balance
        service.player.credit(service.REFILL_AMOUNT)
        try:
            unit_of_work.save(
                service.player,
                service.blackjack.dump_state(),
                request_key=request_key,
                signature=signature,
                ledger_entries=[LedgerMovement(LedgerEntryType.DEMO_REFILL, service.REFILL_AMOUNT)],
                response={"balance": service.player.balance},
            )
            service._revision = unit_of_work.revision()
        except Exception:
            service.player.balance = before
            raise
        return service.player.balance
