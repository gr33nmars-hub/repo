from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from .core import GameRules, RandomSource, SecureRandom
from .errors import InvalidCasinoCommand
from .ledger import LedgerEntryType, LedgerMovement
from .models import Card, GameResult
from .provably_fair import shuffle as fair_shuffle
from .rule_metadata import fingerprint_rules
from .shoe import Shoe
from .slot_fairness import seed_hash

BlackjackAction = Literal[
    "hit", "stand", "double", "split", "surrender", "insurance", "decline_insurance"
]
BlackjackPhase = Literal["insurance", "playing", "won", "lost", "push", "mixed"]
PlayerHandStatus = Literal[
    "playing", "standing", "bust", "surrendered", "blackjack", "won", "lost", "push"
]
PLAYER_HAND_STATUSES = frozenset(
    {"playing", "standing", "bust", "surrendered", "blackjack", "won", "lost", "push"}
)
BLACKJACK_PHASES = frozenset({"insurance", "playing", "won", "lost", "push", "mixed"})


@dataclass(frozen=True, slots=True)
class BlackjackRules:
    decks: int = 6
    dealer_hits_soft_17: bool = False
    natural_numerator: int = 3
    natural_denominator: int = 2
    allow_double: bool = True
    allow_double_after_split: bool = True
    allow_surrender: bool = True
    max_hands: int = 4

    def __post_init__(self) -> None:
        if (
            type(self.decks) is not int
            or self.decks < 1
            or type(self.max_hands) is not int
            or self.max_hands < 1
            or type(self.natural_numerator) is not int
            or self.natural_numerator < 1
            or type(self.natural_denominator) is not int
            or self.natural_denominator < 1
            or self.natural_numerator <= self.natural_denominator
            or any(
                type(value) is not bool
                for value in (
                    self.dealer_hits_soft_17,
                    self.allow_double,
                    self.allow_double_after_split,
                    self.allow_surrender,
                )
            )
        ):
            raise ValueError("Invalid blackjack rules")


@dataclass(slots=True)
class PlayerHand:
    cards: list[Card]
    bet: int
    status: PlayerHandStatus = "playing"
    from_split: bool = False
    split_aces: bool = False
    doubled: bool = False
    message: str = ""


@dataclass(slots=True)
class BlackjackRound:
    hands: list[PlayerHand]
    dealer_cards: list[Card]
    status: BlackjackPhase = "playing"
    message: str = "Твой ход"
    active_hand_index: int = 0
    insurance_bet: int = 0
    insurance_decided: bool = True
    insurance_payout: int = 0
    initial_bet: int = 0
    round_id: str | None = None
    fairness: dict | None = None
    draw_order: list[str] | None = None
    draw_events: list[dict[str, str]] | None = None

    @property
    def bet(self) -> int:
        return sum(hand.bet for hand in self.hands) + self.insurance_bet


@dataclass(frozen=True, slots=True)
class BlackjackTransition:
    ledger_entries: tuple[LedgerMovement, ...]
    result: GameResult | None


@dataclass(frozen=True, slots=True)
class _BlackjackCheckpoint:
    hand: BlackjackRound | None
    shoe: Shoe


@dataclass(frozen=True, slots=True)
class BlackjackSnapshot:
    hand: BlackjackRound | None
    shoe: Shoe


class Blackjack:
    game_id, name = "blackjack", "Блэкджек"
    rule_version = "blackjack-v1"
    suits = ("♠", "♥", "♣", "♦")
    ranks = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")

    def __init__(
        self,
        rng: RandomSource | None = None,
        rules: GameRules | None = None,
        blackjack_rules: BlackjackRules | None = None,
    ):
        self._rng = rng if rng is not None else SecureRandom()
        self.rules = rules if rules is not None else GameRules()
        self.blackjack_rules = blackjack_rules if blackjack_rules is not None else BlackjackRules()
        self._hand: BlackjackRound | None = None
        self._shoe = Shoe()
        self._draw_trace: list[str] | None = None
        self._draw_event_trace: list[dict[str, str]] | None = None
        self._draw_target: str | None = None

    @property
    def hand(self) -> BlackjackRound | None:
        return deepcopy(self._hand)

    @property
    def minimum_bet(self) -> int:
        return self.rules.minimum_bet

    def catalog_info(self) -> dict[str, object]:
        return {
            "id": self.game_id,
            "name": self.name,
            "minimum_bet": self.minimum_bet,
            "maximum_bet": self.rules.maximum_bet,
        }

    def snapshot(self) -> BlackjackSnapshot:
        return BlackjackSnapshot(deepcopy(self._hand), self._shoe.copy())

    def restore_snapshot(self, snapshot: BlackjackSnapshot | None) -> None:
        if snapshot is None:
            self._set_snapshot(BlackjackSnapshot(None, Shoe()))
            return
        if not isinstance(snapshot, BlackjackSnapshot):
            raise ValueError("Некорректное состояние раздачи блэкджека")
        if snapshot.hand is not None:
            self._validate_saved_round(snapshot.hand)
            self._validate_shoe(snapshot)
        self._set_snapshot(snapshot)

    def _set_snapshot(self, snapshot: BlackjackSnapshot) -> None:
        self._hand = deepcopy(snapshot.hand)
        self._shoe = snapshot.shoe.copy()
        self._draw_trace = (
            self._hand.draw_order
            if self._hand is not None
            and self._hand.status in {"playing", "insurance"}
            and self._hand.fairness is not None
            else None
        )
        self._draw_event_trace = (
            self._hand.draw_events
            if self._hand is not None
            and self._hand.status in {"playing", "insurance"}
            and self._hand.fairness is not None
            else None
        )
        self._draw_target = None

    def checkpoint(self) -> _BlackjackCheckpoint:
        return _BlackjackCheckpoint(deepcopy(self._hand), self._shoe.copy())

    def restore_checkpoint(self, checkpoint: _BlackjackCheckpoint) -> None:
        self._set_snapshot(BlackjackSnapshot(checkpoint.hand, checkpoint.shoe))

    def _validate_shoe(self, snapshot: BlackjackSnapshot) -> None:
        round_ = snapshot.hand
        if round_ is None:
            return
        cards = (
            list(snapshot.shoe.remaining_cards)
            + list(snapshot.shoe.discarded_cards)
            + round_.dealer_cards
            + [card for hand in round_.hands for card in hand.cards]
        )
        counts = Counter((card.rank, card.suit) for card in cards)
        if any(
            counts[(rank, suit)] != self.blackjack_rules.decks
            for suit in self.suits
            for rank in self.ranks
        ):
            raise ValueError("Некорректный состав башмака")

    @staticmethod
    def score(cards: list[Card]) -> int:
        total = sum(card.value for card in cards)
        aces = sum(card.rank == "A" for card in cards)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    @classmethod
    def _is_natural(cls, cards: list[Card]) -> bool:
        return len(cards) == 2 and cls.score(cards) == 21

    @staticmethod
    def _soft(cards: list[Card]) -> bool:
        return (
            any(c.rank == "A" for c in cards)
            and sum(1 if c.rank == "A" else c.value for c in cards) + 10 <= 21
        )

    def _draw(self) -> Card:
        card = self._shoe.draw()
        trace = self._draw_trace
        if trace is not None:
            trace.append(card.label)
        events = self._draw_event_trace
        if events is not None and self._draw_target is not None:
            events.append({"card": card.label, "target": self._draw_target})
        return card

    def _draw_for(self, target: str) -> Card:
        self._draw_target = target
        try:
            return self._draw()
        finally:
            self._draw_target = None

    def _new_shoe(
        self, server_seed: str | None = None, client_seed: str = "", nonce: int = 0
    ) -> None:
        self._shoe = Shoe.full(self.blackjack_rules.decks, self.suits, self.ranks)
        if server_seed is None:
            self._shoe.shuffle(self._rng)
        else:
            self._shoe.shuffle_fair(server_seed, client_seed, nonce)

    def _archive_completed_round(self) -> None:
        """Keep prior rounds in the shoe inventory while they leave the playable deck."""
        if self._hand is not None:
            cards = self._hand.dealer_cards + [
                card for hand in self._hand.hands for card in hand.cards
            ]
            self._shoe.discard(cards)

    def start(
        self,
        bet: int,
        *,
        fairness: dict | None = None,
        server_seed: str | None = None,
        client_seed: str = "",
        nonce: int = 0,
    ) -> BlackjackRound:
        if (
            type(bet) is not int
            or not self.minimum_bet <= bet <= self.rules.maximum_bet
            or bet % 2
            or bet % self.blackjack_rules.natural_denominator
        ):
            raise InvalidCasinoCommand(
                "Ставка должна быть в пределах стола и точно делиться для выплат блэкджека и страховки"
            )
        if self._hand and self._hand.status in {"playing", "insurance"}:
            raise InvalidCasinoCommand("Сначала закончи текущую раздачу")
        # Committed rounds use a reproducible shoe whose draw order can be verified.
        if server_seed is not None:
            self._new_shoe(server_seed, client_seed, nonce)
        elif self._shoe.remaining_count < 60:
            self._new_shoe()
        elif self._hand is not None:
            self._archive_completed_round()
        draw_order: list[str] = []
        draw_events: list[dict[str, str]] = []
        self._draw_trace = draw_order
        self._draw_event_trace = draw_events
        player = [self._draw_for("hand:0")]
        dealer = [self._draw_for("dealer")]
        player.append(self._draw_for("hand:0"))
        dealer.append(self._draw_for("dealer"))
        self._hand = BlackjackRound(
            [PlayerHand(player, bet)],
            dealer,
            initial_bet=bet,
            round_id=uuid4().hex,
            fairness=fairness,
            draw_order=draw_order,
            draw_events=draw_events,
        )
        if dealer[0].rank == "A":
            self._hand.status = "insurance"
            self._hand.insurance_decided = False
            self._hand.message = "Дилер показывает туза · страховка до половины ставки"
        else:
            self._peek()
        assert self._hand is not None
        return deepcopy(self._hand)

    def _insurance(self, take: bool) -> BlackjackRound:
        round_ = self._require_round("insurance")
        round_.insurance_decided = True
        round_.insurance_bet = round_.hands[0].bet // 2 if take else 0
        self._peek()
        return round_

    def _peek(self) -> None:
        round_ = self._hand
        assert round_ is not None
        dealer_natural = self.score(round_.dealer_cards) == 21
        player_natural = self._is_natural(round_.hands[0].cards)
        if dealer_natural:
            round_.insurance_payout = round_.insurance_bet * 3
            round_.hands[0].status = "push" if player_natural else "lost"
            round_.hands[0].message = "Оба имеют блэкджек" if player_natural else "Блэкджек дилера"
            payout = self._payout(round_)
            round_.status = (
                "won" if payout > round_.bet else "lost" if payout < round_.bet else "push"
            )
            round_.message = round_.hands[0].message
        elif player_natural:
            round_.hands[0].status = "blackjack"
            round_.hands[0].message = "Натуральный блэкджек · 3:2"
            round_.status = "won"
            round_.message = round_.hands[0].message
        else:
            round_.status = "playing"
            round_.message = "Твой ход"

    def available_actions(self, balance: int | None = None) -> list[BlackjackAction]:
        round_ = self._hand
        if round_ is None:
            return []
        if round_.status == "insurance":
            actions: list[BlackjackAction] = ["decline_insurance"]
            if balance is None or balance >= round_.hands[0].bet // 2:
                actions.insert(0, "insurance")
            return actions
        if round_.status != "playing":
            return []
        current = round_.hands[round_.active_hand_index]
        if current.status != "playing":
            return []
        actions = ["hit", "stand"]
        first_two = len(current.cards) == 2
        if (
            first_two
            and self.blackjack_rules.allow_double
            and current.bet * 2 <= self.rules.maximum_bet
            and (not current.from_split or self.blackjack_rules.allow_double_after_split)
            and (balance is None or balance >= current.bet)
        ):
            actions.append("double")
        if first_two and not current.from_split and self.blackjack_rules.allow_surrender:
            actions.append("surrender")
        if (
            first_two
            and len(round_.hands) < self.blackjack_rules.max_hands
            and not current.split_aces
            and current.cards[0].value == current.cards[1].value
            and (balance is None or balance >= current.bet)
        ):
            actions.append("split")
        return actions

    def _require_round(self, status: BlackjackPhase = "playing") -> BlackjackRound:
        if self._hand is None or self._hand.status != status:
            raise ValueError("Сейчас нет подходящей активной раздачи")
        return self._hand

    def _current(self, action: BlackjackAction) -> tuple[BlackjackRound, PlayerHand]:
        round_ = self._require_round()
        if round_.status != "playing" or action not in {
            "hit",
            "stand",
            "double",
            "split",
            "surrender",
        }:
            raise InvalidCasinoCommand("Это действие сейчас недоступно")
        return round_, round_.hands[round_.active_hand_index]

    def _advance(self) -> None:
        round_ = self._require_round()
        next_index = next(
            (
                i
                for i in range(round_.active_hand_index + 1, len(round_.hands))
                if round_.hands[i].status == "playing"
            ),
            None,
        )
        if next_index is not None:
            round_.active_hand_index = next_index
            next_hand = round_.hands[next_index]
            if len(next_hand.cards) == 1:
                next_hand.cards.append(self._draw_for(f"hand:{next_index}"))
            if self.score(next_hand.cards) == 21:
                next_hand.status = "standing"
                next_hand.message = "21 после разделения · выплата как за обычную руку"
                self._advance()
                return
            round_.message = f"Рука {next_index + 1}: твой ход"
        else:
            self._settle()

    def _hit(self) -> BlackjackRound:
        round_, current = self._current("hit")
        current.cards.append(self._draw_for(f"hand:{round_.active_hand_index}"))
        score = self.score(current.cards)
        if score > 21:
            current.status, current.message = "bust", "Перебор"
            self._advance()
        elif score == 21:
            current.status = "standing"
            current.message = "21 · рука остановлена"
            self._advance()
        return round_

    def _stand(self) -> BlackjackRound:
        round_, current = self._current("stand")
        current.status = "standing"
        self._advance()
        return round_

    def _double(self) -> BlackjackRound:
        round_, current = self._current("double")
        current.bet *= 2
        current.doubled = True
        current.cards.append(self._draw_for(f"hand:{round_.active_hand_index}"))
        current.status = "bust" if self.score(current.cards) > 21 else "standing"
        current.message = (
            "Перебор после удвоения" if current.status == "bust" else "Удвоение · одна карта"
        )
        self._advance()
        return round_

    def _split(self) -> BlackjackRound:
        round_, current = self._current("split")
        index = round_.active_hand_index
        second = current.cards.pop()
        ace = current.cards[0].rank == "A"
        current.from_split = True
        current.split_aces = ace
        new = PlayerHand([second], current.bet, from_split=True, split_aces=ace)
        round_.hands.insert(index + 1, new)
        if self._draw_event_trace is not None:
            for event in self._draw_event_trace:
                target = event.get("target", "")
                if target.startswith("hand:") and target[5:].isdigit() and int(target[5:]) > index:
                    event["target"] = f"hand:{int(target[5:]) + 1}"
            for event in reversed(self._draw_event_trace):
                if event.get("target") == f"hand:{index}" and event.get("card") == second.label:
                    event["target"] = f"hand:{index + 1}"
                    break
        current.cards.append(self._draw_for(f"hand:{index}"))
        if self.score(current.cards) == 21:
            current.status = "standing"
            current.message = "21 после разделения · выплата как за обычную руку"
        if ace:
            new.cards.append(self._draw_for(f"hand:{index + 1}"))
            current.status = new.status = "standing"
            current.message = new.message = "После разделения тузов выдана одна карта"
            self._advance()
        elif current.status == "standing":
            self._advance()
        return round_

    def _surrender(self) -> BlackjackRound:
        round_, current = self._current("surrender")
        current.status, current.message = "surrendered", "Сдача · возвращена половина ставки"
        self._advance()
        return round_

    def act(self, action: BlackjackAction, balance: int) -> BlackjackTransition:
        if type(balance) is not int or balance < 0:
            raise InvalidCasinoCommand("Баланс должен быть неотрицательным целым числом")
        if action not in self.available_actions(balance):
            raise InvalidCasinoCommand("Это действие сейчас недоступно")
        assert self._hand is not None
        round_ = self._require_round("insurance" if self._hand.status == "insurance" else "playing")
        hand = round_.hands[round_.active_hand_index]
        additional_stake = (
            hand.bet
            if action in {"double", "split"}
            else hand.bet // 2
            if action == "insurance"
            else 0
        )

        if action == "hit":
            self._hit()
        elif action == "stand":
            self._stand()
        elif action == "double":
            self._double()
        elif action == "split":
            self._split()
        elif action == "surrender":
            self._surrender()
        elif action == "insurance":
            self._insurance(True)
        elif action == "decline_insurance":
            self._insurance(False)
        else:
            raise ValueError("Неизвестное действие за столом")

        result = self.result() if round_.status not in {"playing", "insurance"} else None
        ledger_entries: list[LedgerMovement] = []
        if additional_stake:
            entry_type = {
                "double": LedgerEntryType.BLACKJACK_DOUBLE_STAKE,
                "split": LedgerEntryType.BLACKJACK_SPLIT_STAKE,
                "insurance": LedgerEntryType.BLACKJACK_INSURANCE_STAKE,
            }[action]
            ledger_entries.append(LedgerMovement(entry_type, -additional_stake))
        if result is not None:
            ledger_entries.append(LedgerMovement(LedgerEntryType.BLACKJACK_PAYOUT, result.payout))
        return BlackjackTransition(tuple(ledger_entries), result)

    def _settle(self) -> None:
        round_ = self._require_round()
        contenders = [h for h in round_.hands if h.status == "standing"]
        if contenders:
            while self.score(round_.dealer_cards) < 17 or (
                self.blackjack_rules.dealer_hits_soft_17
                and self.score(round_.dealer_cards) == 17
                and self._soft(round_.dealer_cards)
            ):
                round_.dealer_cards.append(self._draw_for("dealer"))
        dealer_score = self.score(round_.dealer_cards)
        for hand in contenders:
            score = self.score(hand.cards)
            if dealer_score > 21 or score > dealer_score:
                hand.status, hand.message = "won", "Победа"
            elif score == dealer_score:
                hand.status, hand.message = "push", "Ничья"
            else:
                hand.status, hand.message = "lost", "Поражение"
        payout = self._payout(round_)
        wins = any(h.status in {"won", "blackjack"} for h in round_.hands)
        losses = any(h.status in {"lost", "bust", "surrendered"} for h in round_.hands)
        round_.status = (
            "mixed"
            if wins and losses
            else "won"
            if payout > round_.bet
            else "lost"
            if payout < round_.bet
            else "push"
        )
        round_.message = " · ".join(
            f"Рука {i + 1}: {h.message or h.status}" for i, h in enumerate(round_.hands)
        )

    def _payout(self, round_: BlackjackRound) -> int:
        payout = round_.insurance_payout
        for hand in round_.hands:
            if hand.status == "blackjack":
                payout += (
                    hand.bet
                    * (
                        self.blackjack_rules.natural_denominator
                        + self.blackjack_rules.natural_numerator
                    )
                    // self.blackjack_rules.natural_denominator
                )
            elif hand.status == "won":
                payout += hand.bet * 2
            elif hand.status == "push":
                payout += hand.bet
            elif hand.status == "surrendered":
                payout += hand.bet // 2
        return payout

    def result(self) -> GameResult:
        round_ = self._hand
        if round_ is None or round_.status in {"playing", "insurance"}:
            raise ValueError("Раунд ещё не завершён")
        payout = self._payout(round_)
        details = "  ·  ".join(
            f"Рука {i + 1}: {' '.join(c.label for c in h.cards)} ({self.score(h.cards)}), {h.status}"
            for i, h in enumerate(round_.hands)
        )
        details += f"  ·  Дилер: {' '.join(c.label for c in round_.dealer_cards)} ({self.score(round_.dealer_cards)})"
        if round_.insurance_bet:
            details += f"  ·  Страховка: {round_.insurance_bet} → {round_.insurance_payout}"
        snapshot = self._rules_snapshot()
        outcome: dict[str, object] = {
            "round_id": round_.round_id,
            "initial_bet": round_.initial_bet,
            "dealer_cards": [card.label for card in round_.dealer_cards],
            "hands": [
                {
                    "cards": [card.label for card in hand.cards],
                    "bet": hand.bet,
                    "status": hand.status,
                    "from_split": hand.from_split,
                    "doubled": hand.doubled,
                    "split_aces": hand.split_aces,
                }
                for hand in round_.hands
            ],
            "insurance_bet": round_.insurance_bet,
            "insurance_payout": round_.insurance_payout,
        }
        if round_.fairness is not None:
            outcome["draw_order"] = round_.draw_order or []
            outcome["draw_events"] = list(round_.draw_events or [])
        return GameResult(
            self.game_id,
            self.name,
            round_.message,
            round_.bet,
            payout,
            details,
            rule_version=self.rule_version,
            rules_fingerprint=fingerprint_rules(self.rule_version, snapshot),
            rules_snapshot=snapshot,
            outcome=outcome,
            fairness=round_.fairness,
            round_id=round_.round_id,
        )

    def _rules_snapshot(self) -> dict[str, object]:
        return {
            "decks": self.blackjack_rules.decks,
            "minimum_bet": self.rules.minimum_bet,
            "maximum_bet": self.rules.maximum_bet,
            "dealer_hits_soft_17": self.blackjack_rules.dealer_hits_soft_17,
            "natural_numerator": self.blackjack_rules.natural_numerator,
            "natural_denominator": self.blackjack_rules.natural_denominator,
            "insurance_profit_multiplier": 2,
            "max_hands": self.blackjack_rules.max_hands,
            "allow_double": self.blackjack_rules.allow_double,
            "allow_double_after_split": self.blackjack_rules.allow_double_after_split,
            "split_aces_one_card": True,
            "split_aces_resplit": False,
            "late_surrender": self.blackjack_rules.allow_surrender,
        }

    def _validate_saved_round(self, round_: BlackjackRound) -> None:
        hands, dealer = round_.hands, round_.dealer_cards
        live_statuses = {
            "playing",
            "standing",
            "bust",
            "surrendered",
            "blackjack",
            "won",
            "lost",
            "push",
        }
        valid = (
            bool(hands)
            and 0 <= round_.active_hand_index < len(hands)
            and len(hands) <= self.blackjack_rules.max_hands
            and len(dealer) >= 2
            and self.minimum_bet <= round_.initial_bet <= self.rules.maximum_bet
            and round_.initial_bet % 2 == 0
            and round_.initial_bet % self.blackjack_rules.natural_denominator == 0
            and all(
                h.bet in {round_.initial_bet, round_.initial_bet * 2}
                and h.bet <= self.rules.maximum_bet
                and h.cards
                and h.status in live_statuses
                and (len(h.cards) != 1 or (h.from_split and h.status == "playing"))
                and (not h.split_aces or (h.from_split and h.cards[0].rank == "A"))
                and (not h.doubled or h.bet == round_.initial_bet * 2)
                and (
                    h.status != "blackjack"
                    or (self._is_natural(h.cards) and not h.from_split and not h.doubled)
                )
                for h in hands
            )
            and round_.status in {"playing", "insurance", "won", "lost", "push", "mixed"}
            and round_.insurance_bet in {0, round_.initial_bet // 2}
            and round_.insurance_payout in {0, round_.insurance_bet * 3}
        )
        if round_.status == "insurance":
            valid = (
                valid
                and not round_.insurance_decided
                and round_.insurance_bet == 0
                and round_.insurance_payout == 0
                and dealer[0].rank == "A"
                and len(hands) == 1
                and hands[0].status == "playing"
            )
        elif round_.status == "playing":
            valid = (
                valid
                and round_.insurance_decided
                and any(h.status == "playing" for h in hands)
                and hands[round_.active_hand_index].status == "playing"
                and len(dealer) == 2
                and self.score(dealer) != 21
                and all(
                    h.status in {"playing", "standing", "bust"}
                    and (
                        self.score(h.cards) < 21
                        if h.status == "playing"
                        else self.score(h.cards) > 21
                        if h.status == "bust"
                        else self.score(h.cards) <= 21
                    )
                    for h in hands
                )
            )
        else:
            valid = (
                valid
                and round_.insurance_decided
                and all(h.status not in {"playing", "standing"} for h in hands)
            )
            for hand in hands:
                score = self.score(hand.cards)
                if hand.status == "blackjack":
                    valid = valid and round_.status == "won" and self.score(dealer) != 21
                elif hand.status == "bust":
                    valid = valid and score > 21
                elif hand.status == "surrendered":
                    valid = (
                        valid and len(hand.cards) == 2 and not hand.from_split and not hand.doubled
                    )
                elif hand.status == "won":
                    valid = (
                        valid
                        and score <= 21
                        and (self.score(dealer) > 21 or score > self.score(dealer))
                    )
                elif hand.status == "lost":
                    dealer_natural = self._is_natural(dealer)
                    valid = (
                        valid
                        and score <= 21
                        and self.score(dealer) <= 21
                        and (
                            (dealer_natural and not self._is_natural(hand.cards))
                            or (not dealer_natural and score < self.score(dealer))
                        )
                    )
                elif hand.status == "push":
                    valid = (
                        valid
                        and score <= 21
                        and self.score(dealer) <= 21
                        and score == self.score(dealer)
                    )
            payout = self._payout(round_)
            wins = any(h.status in {"won", "blackjack"} for h in hands)
            losses = any(h.status in {"lost", "bust", "surrendered"} for h in hands)
            expected_status = (
                "mixed"
                if wins and losses
                else "won"
                if payout > round_.bet
                else "lost"
                if payout < round_.bet
                else "push"
            )
            valid = valid and round_.status == expected_status
        if round_.fairness is not None:
            valid = valid and self._validate_saved_proof(round_)
        elif round_.draw_order:
            valid = False
        if not valid:
            raise ValueError("Некорректное состояние раздачи блэкджека")

    def _validate_saved_proof(self, round_: BlackjackRound) -> bool:
        proof = round_.fairness
        draw_order = round_.draw_order
        if type(proof) is not dict or type(draw_order) is not list or len(draw_order) < 4:
            return False
        server_seed = proof.get("server_seed")
        client_seed = proof.get("client_seed")
        nonce = proof.get("nonce")
        if (
            type(server_seed) is not str
            or len(server_seed) != 64
            or any(char not in "0123456789abcdef" for char in server_seed)
            or proof.get("server_seed_hash") != seed_hash(server_seed)
            or type(client_seed) is not str
            or type(nonce) is not int
            or nonce < 0
            or any(type(label) is not str for label in draw_order)
        ):
            return False
        shoe = [
            f"{rank}{suit}"
            for _ in range(self.blackjack_rules.decks)
            for suit in self.suits
            for rank in self.ranks
        ]
        fair_shuffle(shoe, server_seed, client_seed, nonce)
        if len(draw_order) > len(shoe) or draw_order != shoe[: len(draw_order)]:
            return False
        draw_events = round_.draw_events
        if draw_events is not None:
            return self._draw_events_match(round_, draw_order, draw_events)
        dealt = [card.label for card in round_.dealer_cards]
        dealt.extend(card.label for hand in round_.hands for card in hand.cards)
        return Counter(dealt) == Counter(draw_order)

    @staticmethod
    def _draw_events_match(
        round_: BlackjackRound, draw_order: list[str], events: list[dict[str, str]]
    ) -> bool:
        if len(events) != len(draw_order):
            return False
        dealer: list[str] = []
        hands: list[list[str]] = [[] for _ in round_.hands]
        for card, event in zip(draw_order, events, strict=True):
            if (
                type(event) is not dict
                or set(event) != {"card", "target"}
                or event.get("card") != card
                or type(event.get("target")) is not str
            ):
                return False
            target = event["target"]
            if target == "dealer":
                dealer.append(card)
                continue
            if not target.startswith("hand:") or not target.removeprefix("hand:").isdigit():
                return False
            index = int(target.removeprefix("hand:"))
            if not 0 <= index < len(hands):
                return False
            hands[index].append(card)
        return dealer == [card.label for card in round_.dealer_cards] and hands == [
            [card.label for card in hand.cards] for hand in round_.hands
        ]
