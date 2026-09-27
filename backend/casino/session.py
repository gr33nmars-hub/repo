from __future__ import annotations

import json
import secrets
from threading import RLock

from casino.blackjack import Blackjack, BlackjackAction, BlackjackRules
from casino.core import CasinoGame, GameCatalogItem
from casino.errors import StaleGameState
from casino.games import Roulette, SlotMachine
from casino.models import GameResult
from casino.slot_fairness import reel_stops, seed_hash
from casino.storage import PlayerRepository


class CasinoSession:
    """Application service coordinating domain games and atomic local persistence."""

    REFILL_AMOUNT = 1000

    def __init__(self, repository: PlayerRepository | None = None) -> None:
        self.repository = repository or PlayerRepository()
        self._lock = RLock()
        with self.repository.read_transaction() as db:
            self.player = self.repository.load(db)
            saved_blackjack = self.repository.load_blackjack(db)
            self.blackjack = Blackjack(blackjack_rules=BlackjackRules())
            self.blackjack.restore_state(saved_blackjack)
            self._validate_active_blackjack_ledger(db)
            self._revision = self.repository.revision(db)
            self._slots_seed = self.repository.load_slot_seed(db)
        self.games: dict[str, CasinoGame] = {
            "slots": SlotMachine(),
            "roulette": Roulette(),
        }

    def _validate_active_blackjack_ledger(self, db) -> None:
        hand = self.blackjack.hand
        if hand is not None and hand.status in {"playing", "insurance"}:
            self.repository.validate_active_blackjack_round(
                db, hand.round_id, hand.initial_bet, hand.bet
            )

    def _refresh_if_stale(self, db) -> None:
        revision = self.repository.revision(db)
        if revision == self._revision:
            return
        self.player = self.repository.load(db)
        self.blackjack.restore_state(self.repository.load_blackjack(db))
        self._validate_active_blackjack_ledger(db)
        self._revision = revision
        self._slots_seed = self.repository.load_slot_seed(db)

    def refresh_state(self) -> dict:
        """Refresh this process's snapshot before serving a read request."""
        with self._lock, self.repository.read_transaction() as db:
            self._refresh_if_stale(db)
            return self.state()

    def state(self) -> dict:
        with self._lock:
            rounds = [round_.to_dict() for round_ in reversed(self.player.rounds[-12:])]
            total = len(self.player.rounds)
            catalog_items: tuple[GameCatalogItem, ...] = (*self.games.values(), self.blackjack)
            games = [game.catalog_info() for game in catalog_items]
            return {
                "player": {
                    "name": self.player.name,
                    "balance": self.player.balance,
                    "rounds_played": total,
                    "wins": self.player.wins,
                    "losses": self.player.losses,
                    "win_rate": round(self.player.wins / total * 100) if total else 0,
                    "total_wagered": self.player.total_wagered,
                },
                "games": games,
                "history": rounds,
                "blackjack": self.blackjack.state(self.player.balance),
                "slots_server_seed_hash": seed_hash(self._slots_seed),
            }

    def _validate_bet(self, game: CasinoGame | Blackjack, bet: int) -> None:
        if not game.minimum_bet <= bet <= game.rules.maximum_bet:
            raise ValueError(
                f"Ставка должна быть от {game.minimum_bet} до {game.rules.maximum_bet} фишек"
            )
        if bet > self.player.balance:
            raise ValueError("На балансе недостаточно фишек для этой ставки")
        if game.game_id == "blackjack" and bet % 2:
            raise ValueError(
                "Для точной натуральной выплаты 3:2 ставка в блэкджеке должна быть чётной"
            )

    def _cached_request(self, request_key: str, signature: str, db) -> dict | None:
        if not request_key or len(request_key) > 128:
            raise ValueError("Нужен уникальный ключ запроса")
        return self.repository.get_request_response(request_key, signature=signature, db=db)

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
        with self._lock, self.repository.write_transaction() as db:
            self._refresh_if_stale(db)
            signature = self._request_signature(
                "game.play",
                game_id=game_id,
                bet=bet,
                choice=choice,
                client_seed=client_seed if game_id == "slots" else "",
                expected_server_seed_hash=(
                    expected_server_seed_hash if game_id == "slots" else None
                ),
            )
            cached = self._cached_request(request_key, signature, db)
            if cached is not None:
                return cached
            if game_id == "blackjack":
                raise ValueError("Для блэкджека сначала начни новую раздачу")
            game = self.games.get(game_id)
            if game is None:
                raise ValueError("Такой игры нет")
            self._validate_bet(game, bet)
            before = self.player.balance
            before_rounds = self.player.rounds.copy()
            previous_seed = self._slots_seed
            try:
                if isinstance(game, SlotMachine):
                    if (
                        expected_server_seed_hash is not None
                        and expected_server_seed_hash != seed_hash(previous_seed)
                    ):
                        raise StaleGameState(
                            "Seed для барабанов изменился. Состояние обновлено; проверь стол."
                        )
                    actual_client_seed = client_seed or request_key
                    if len(actual_client_seed) > 128:
                        raise ValueError("Слишком длинный client seed")
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
                    self._slots_seed = secrets.token_hex(32)
                    self.repository.set_slot_seed(db, self._slots_seed)
                else:
                    result = game.play(bet, choice)
                self.player.debit(bet)
                self.player.credit(result.payout)
                self._record(result)
                response = {"result": result.to_dict(), "state": self.state()}
                self.repository.save(
                    self.player,
                    self.blackjack.dump_state(),
                    request_key=request_key,
                    signature=signature,
                    ledger_entries=[("bet_stake", -bet), ("game_payout", result.payout)],
                    response=response,
                    db=db,
                )
                self._revision = self.repository.revision(db)
            except Exception:
                self.player.balance = before
                self.player.rounds = before_rounds
                self._slots_seed = previous_seed
                raise
            return response

    def start_blackjack(self, bet: int, request_key: str) -> dict:
        with self._lock, self.repository.write_transaction() as db:
            self._refresh_if_stale(db)
            signature = self._request_signature("blackjack.start", bet=bet)
            cached = self._cached_request(request_key, signature, db)
            if cached is not None:
                return cached
            if self.blackjack.hand and self.blackjack.hand.status in {"playing", "insurance"}:
                raise ValueError("Сначала закончи текущую раздачу")
            self._validate_bet(self.blackjack, bet)
            before = self.player.balance
            before_rounds = self.player.rounds.copy()
            previous = self.blackjack.dump_state()
            previous_deck = self.blackjack.deck.copy()
            try:
                self.player.debit(bet)
                hand = self.blackjack.start(bet)
                entries = [("blackjack_stake", -bet)]
                if hand.status not in {"playing", "insurance"}:
                    result = self.blackjack.result()
                    self.player.credit(result.payout)
                    self._record(result)
                    entries.append(("blackjack_payout", result.payout))
                state = self.state()
                self.repository.save(
                    self.player,
                    self.blackjack.dump_state(),
                    request_key=request_key,
                    signature=signature,
                    ledger_entries=entries,
                    response=state,
                    round_id=hand.round_id,
                    db=db,
                )
                self._revision = self.repository.revision(db)
            except Exception:
                self.player.balance = before
                self.blackjack.restore_state(previous)
                self.blackjack.deck = previous_deck
                self.player.rounds = before_rounds
                raise
            return state

    def blackjack_action(self, action: BlackjackAction, request_key: str) -> dict:
        with self._lock, self.repository.write_transaction() as db:
            self._refresh_if_stale(db)
            signature = self._request_signature("blackjack.action", action=action)
            cached = self._cached_request(request_key, signature, db)
            if cached is not None:
                return cached
            hand = self.blackjack.hand
            if hand is None or hand.status not in {"playing", "insurance"}:
                raise ValueError("Сейчас нет активной раздачи")
            before_balance, before_state = self.player.balance, self.blackjack.dump_state()
            before_rounds = self.player.rounds.copy()
            try:
                entries: list[tuple[str, int]] = []
                transition = self.blackjack.act(action, self.player.balance)
                for entry_type, delta in transition.ledger_entries:
                    if delta < 0:
                        self.player.debit(-delta)
                    else:
                        self.player.credit(delta)
                if transition.result is not None:
                    self._record(transition.result)
                entries.extend(transition.ledger_entries)
                response = self.state()
                self.repository.save(
                    self.player,
                    self.blackjack.dump_state(),
                    request_key=request_key,
                    signature=signature,
                    ledger_entries=entries,
                    response=response,
                    round_id=hand.round_id,
                    db=db,
                )
                self._revision = self.repository.revision(db)
            except Exception:
                self.player.balance = before_balance
                self.blackjack.restore_state(before_state)
                self.player.rounds = before_rounds
                raise
            return response

    def refill(self, request_key: str) -> int:
        with self._lock, self.repository.write_transaction() as db:
            self._refresh_if_stale(db)
            signature = self._request_signature("wallet.refill")
            cached = self._cached_request(request_key, signature, db)
            if cached is not None:
                return int(cached["balance"])
            if self.blackjack.hand and self.blackjack.hand.status in {"playing", "insurance"}:
                raise ValueError("Пополнение доступно после завершения текущей раздачи")
            if self.player.balance >= self.blackjack.minimum_bet:
                raise ValueError(
                    "Пополнение станет доступно, когда не хватит на минимальную ставку"
                )
            before = self.player.balance
            self.player.credit(self.REFILL_AMOUNT)
            try:
                self.repository.save(
                    self.player,
                    self.blackjack.dump_state(),
                    request_key=request_key,
                    signature=signature,
                    ledger_entries=[("demo_refill", self.REFILL_AMOUNT)],
                    response={"balance": self.player.balance},
                    db=db,
                )
                self._revision = self.repository.revision(db)
            except Exception:
                self.player.balance = before
                raise
            return self.player.balance

    def _record(self, result: GameResult) -> None:
        self.player.rounds.append(result)
