from __future__ import annotations

from threading import RLock

from casino.games import Blackjack, BlackjackRules, CasinoGame, Roulette, SlotMachine
from casino.models import GameResult, Player
from casino.storage import PlayerRepository


class CasinoSession:
    """Application service coordinating domain games and atomic local persistence."""

    REFILL_AMOUNT = 1000

    def __init__(self, repository: PlayerRepository | None = None) -> None:
        self.repository = repository or PlayerRepository()
        self._lock = RLock()
        self.player = self.repository.load()
        self.games: dict[str, CasinoGame] = {
            "slots": SlotMachine(),
            "roulette": Roulette(),
            "blackjack": Blackjack(blackjack_rules=BlackjackRules()),
        }
        self.blackjack.restore_state(self.repository.load_blackjack())

    @property
    def blackjack(self) -> Blackjack:
        return self.games["blackjack"]  # type: ignore[return-value]

    def state(self) -> dict:
        with self._lock:
            rounds = [round_.to_dict() for round_ in reversed(self.player.rounds[-12:])]
            total = len(self.player.rounds)
            return {
                "player": {"name": self.player.name, "balance": self.player.balance, "rounds_played": total,
                           "wins": self.player.wins, "losses": self.player.losses,
                           "win_rate": round(self.player.wins / total * 100) if total else 0,
                           "total_wagered": self.player.total_wagered},
                "games": [{"id": game.game_id, "name": game.name, "minimum_bet": game.minimum_bet,
                           "maximum_bet": game.rules.maximum_bet} for game in self.games.values()],
                "history": rounds, "blackjack": self.blackjack.state(self.player.balance),
            }

    def _validate_bet(self, game: CasinoGame, bet: int) -> None:
        if not game.minimum_bet <= bet <= game.rules.maximum_bet:
            raise ValueError(f"Ставка должна быть от {game.minimum_bet} до {game.rules.maximum_bet} фишек")
        if bet > self.player.balance:
            raise ValueError("На балансе недостаточно фишек для этой ставки")
        if game.game_id == "blackjack" and bet % 2:
            raise ValueError("Для точной натуральной выплаты 3:2 ставка в блэкджеке должна быть чётной")

    def _cached_request(self, request_key: str) -> dict | None:
        if not request_key or len(request_key) > 128:
            raise ValueError("Нужен уникальный ключ запроса")
        return self.repository.get_request_response(request_key)

    def play(self, game_id: str, bet: int, choice: str, request_key: str) -> dict:
        with self._lock:
            cached = self._cached_request(request_key)
            if cached is not None:
                return cached
            game = self.games.get(game_id)
            if game is None:
                raise ValueError("Такой игры нет")
            if game_id == "blackjack":
                raise ValueError("Для блэкджека сначала начни новую раздачу")
            self._validate_bet(game, bet)
            before = self.player.balance
            before_rounds = self.player.rounds.copy()
            result = game.play(bet, choice)
            self.player.balance = before - bet + result.payout
            self._record(result)
            response = {"result": result.to_dict(), "state": self.state()}
            try:
                self.repository.save(self.player, self.blackjack.dump_state(), request_key=request_key,
                                     ledger_entries=[("bet_stake", -bet), ("game_payout", result.payout)], response=response)
            except Exception:
                self.player.balance = before
                self.player.rounds = before_rounds
                raise
            return response

    def start_blackjack(self, bet: int, request_key: str) -> dict:
        with self._lock:
            cached = self._cached_request(request_key)
            if cached is not None:
                return cached
            if self.blackjack.hand and self.blackjack.hand.status in {"playing", "insurance"}:
                raise ValueError("Сначала закончи текущую раздачу")
            self._validate_bet(self.blackjack, bet)
            before = self.player.balance
            before_rounds = self.player.rounds.copy()
            previous = self.blackjack.dump_state()
            self.player.balance -= bet
            hand = self.blackjack.start(bet)
            if hand.status not in {"playing", "insurance"}:
                result = self.blackjack.result()
                self.player.balance += result.payout
                self._record(result)
            entries = [("blackjack_stake", -bet)]
            if hand.status not in {"playing", "insurance"}:
                entries.append(("blackjack_payout", result.payout))
            state = self.state()
            try:
                self.repository.save(self.player, self.blackjack.dump_state(), request_key=request_key,
                                     ledger_entries=entries, response=state)
            except Exception:
                self.player.balance = before
                self.blackjack.restore_state(previous)
                self.player.rounds = before_rounds
                raise
            return state

    def blackjack_action(self, action: str, request_key: str) -> dict:
        with self._lock:
            cached = self._cached_request(request_key)
            if cached is not None:
                return cached
            hand = self.blackjack.hand
            if hand is None or hand.status not in {"playing", "insurance"}:
                raise ValueError("Сейчас нет активной раздачи")
            before_balance, before_state = self.player.balance, self.blackjack.dump_state()
            before_rounds = self.player.rounds.copy()
            active_bet = hand.hands[hand.active_hand_index].bet
            entries = []
            if action not in self.blackjack.available_actions(self.player.balance):
                raise ValueError("Это действие сейчас недоступно")
            if action == "hit":
                self.blackjack.hit()
            elif action == "stand":
                self.blackjack.stand()
            elif action == "double":
                self.player.balance -= active_bet
                entries.append(("blackjack_double_stake", -active_bet))
                self.blackjack.double()
            elif action == "split":
                self.player.balance -= active_bet
                entries.append(("blackjack_split_stake", -active_bet))
                self.blackjack.split()
            elif action == "surrender":
                self.blackjack.surrender()
            elif action == "insurance":
                insurance_bet = active_bet // 2
                self.player.balance -= insurance_bet
                entries.append(("blackjack_insurance_stake", -insurance_bet))
                self.blackjack.insurance(True)
            elif action == "decline_insurance":
                self.blackjack.insurance(False)
            else:
                raise ValueError("Неизвестное действие за столом")
            result = None
            if hand.status not in {"playing", "insurance"}:
                result = self.blackjack.result()
                self.player.balance += result.payout
                self._record(result)
                entries.append(("blackjack_payout", result.payout))
            response = self.state()
            try:
                self.repository.save(self.player, self.blackjack.dump_state(), request_key=request_key,
                                     ledger_entries=entries, response=response)
            except Exception:
                self.player.balance = before_balance
                self.blackjack.restore_state(before_state)
                self.player.rounds = before_rounds
                raise
            return response

    def refill(self, request_key: str) -> int:
        with self._lock:
            cached = self._cached_request(request_key)
            if cached is not None:
                return int(cached["balance"])
            if self.player.balance >= self.blackjack.minimum_bet:
                raise ValueError("Пополнение станет доступно, когда не хватит на минимальную ставку")
            before = self.player.balance
            self.player.balance += self.REFILL_AMOUNT
            try:
                self.repository.save(self.player, self.blackjack.dump_state(), request_key=request_key,
                                     ledger_entries=[("demo_refill", self.REFILL_AMOUNT)], response={"balance": self.player.balance})
            except Exception:
                self.player.balance = before
                raise
            return self.player.balance

    def _record(self, result: GameResult) -> None:
        self.player.rounds.append(result)
        self.player.rounds = self.player.rounds[-100:]
