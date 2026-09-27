from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast
from uuid import uuid4

from casino.core import GameRules, RandomSource, SecureRandom
from casino.models import Card, GameResult

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

    @property
    def bet(self) -> int:
        return sum(hand.bet for hand in self.hands) + self.insurance_bet


@dataclass(frozen=True, slots=True)
class BlackjackTransition:
    ledger_entries: tuple[tuple[str, int], ...]
    result: GameResult | None


class Blackjack:
    game_id, name = "blackjack", "Блэкджек"
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
        self.hand: BlackjackRound | None = None
        self.deck: list[Card] = []
        self.discarded_cards: list[Card] = []

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
        if not self.deck:
            raise ValueError("В башмаке закончились карты")
        return self.deck.pop()

    def _new_shoe(self) -> None:
        self.deck = [
            Card(rank, suit)
            for _ in range(self.blackjack_rules.decks)
            for suit in self.suits
            for rank in self.ranks
        ]
        self._rng.shuffle(self.deck)
        self.discarded_cards = []

    def _archive_completed_round(self) -> None:
        """Keep prior rounds in the shoe inventory while they leave the playable deck."""
        if self.hand is not None:
            self.discarded_cards.extend(self.hand.dealer_cards)
            self.discarded_cards.extend(card for hand in self.hand.hands for card in hand.cards)

    def start(self, bet: int) -> BlackjackRound:
        if (
            type(bet) is not int
            or not self.minimum_bet <= bet <= self.rules.maximum_bet
            or bet % 2
            or bet % self.blackjack_rules.natural_denominator
        ):
            raise ValueError(
                "Ставка должна быть в пределах стола и точно делиться для выплат блэкджека и страховки"
            )
        if self.hand and self.hand.status in {"playing", "insurance"}:
            raise ValueError("Сначала закончи текущую раздачу")
        # Reshuffle between rounds only; keep enough cards for four long hands.
        if len(self.deck) < 60:
            self._new_shoe()
        elif self.hand is not None:
            self._archive_completed_round()
        player = [self._draw()]
        dealer = [self._draw()]
        player.append(self._draw())
        dealer.append(self._draw())
        self.hand = BlackjackRound(
            [PlayerHand(player, bet)], dealer, initial_bet=bet, round_id=uuid4().hex
        )
        if dealer[0].rank == "A":
            self.hand.status = "insurance"
            self.hand.insurance_decided = False
            self.hand.message = "Дилер показывает туза · страховка до половины ставки"
        else:
            self._peek()
        return self.hand

    def insurance(self, take: bool) -> BlackjackRound:
        round_ = self._require_round("insurance")
        round_.insurance_decided = True
        round_.insurance_bet = round_.hands[0].bet // 2 if take else 0
        self._peek()
        return round_

    def _peek(self) -> None:
        round_ = self.hand
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
        round_ = self.hand
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
        if self.hand is None or self.hand.status != status:
            raise ValueError("Сейчас нет подходящей активной раздачи")
        return self.hand

    def _current(self, action: BlackjackAction) -> tuple[BlackjackRound, PlayerHand]:
        round_ = self._require_round()
        if action not in self.available_actions():
            raise ValueError("Это действие сейчас недоступно")
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
                next_hand.cards.append(self._draw())
            if self.score(next_hand.cards) == 21:
                next_hand.status = "standing"
                next_hand.message = "21 после разделения · выплата как за обычную руку"
                self._advance()
                return
            round_.message = f"Рука {next_index + 1}: твой ход"
        else:
            self._settle()

    def hit(self) -> BlackjackRound:
        round_, current = self._current("hit")
        current.cards.append(self._draw())
        score = self.score(current.cards)
        if score > 21:
            current.status, current.message = "bust", "Перебор"
            self._advance()
        elif score == 21:
            current.status = "standing"
            current.message = "21 · рука остановлена"
            self._advance()
        return round_

    def stand(self) -> BlackjackRound:
        round_, current = self._current("stand")
        current.status = "standing"
        self._advance()
        return round_

    def double(self) -> BlackjackRound:
        round_, current = self._current("double")
        current.bet *= 2
        current.doubled = True
        current.cards.append(self._draw())
        current.status = "bust" if self.score(current.cards) > 21 else "standing"
        current.message = (
            "Перебор после удвоения" if current.status == "bust" else "Удвоение · одна карта"
        )
        self._advance()
        return round_

    def split(self) -> BlackjackRound:
        round_, current = self._current("split")
        index = round_.active_hand_index
        second = current.cards.pop()
        ace = current.cards[0].rank == "A"
        current.from_split = True
        current.split_aces = ace
        new = PlayerHand([second], current.bet, from_split=True, split_aces=ace)
        round_.hands.insert(index + 1, new)
        current.cards.append(self._draw())
        if self.score(current.cards) == 21:
            current.status = "standing"
            current.message = "21 после разделения · выплата как за обычную руку"
        if ace:
            new.cards.append(self._draw())
            current.status = new.status = "standing"
            current.message = new.message = "После разделения тузов выдана одна карта"
            self._advance()
        elif current.status == "standing":
            self._advance()
        return round_

    def surrender(self) -> BlackjackRound:
        round_, current = self._current("surrender")
        current.status, current.message = "surrendered", "Сдача · возвращена половина ставки"
        self._advance()
        return round_

    def act(self, action: BlackjackAction, balance: int) -> BlackjackTransition:
        """Apply one permitted player action and report its wallet effects."""
        if action not in self.available_actions(balance):
            raise ValueError("Это действие сейчас недоступно")
        assert self.hand is not None
        round_ = self._require_round("insurance" if self.hand.status == "insurance" else "playing")
        hand = round_.hands[round_.active_hand_index]
        additional_stake = (
            hand.bet
            if action in {"double", "split"}
            else hand.bet // 2
            if action == "insurance"
            else 0
        )

        if action == "hit":
            self.hit()
        elif action == "stand":
            self.stand()
        elif action == "double":
            self.double()
        elif action == "split":
            self.split()
        elif action == "surrender":
            self.surrender()
        elif action == "insurance":
            self.insurance(True)
        elif action == "decline_insurance":
            self.insurance(False)
        else:
            raise ValueError("Неизвестное действие за столом")

        result = self.result() if round_.status not in {"playing", "insurance"} else None
        ledger_entries: list[tuple[str, int]] = []
        if additional_stake:
            ledger_entries.append((f"blackjack_{action}_stake", -additional_stake))
        if result is not None:
            ledger_entries.append(("blackjack_payout", result.payout))
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
                round_.dealer_cards.append(self._draw())
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
        round_ = self.hand
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
        return GameResult(self.game_id, self.name, round_.message, round_.bet, payout, details)

    def state(self, balance: int | None = None) -> dict | None:
        round_ = self.hand
        if round_ is None:
            return None
        reveal = round_.status not in {"playing", "insurance"}
        current = round_.hands[round_.active_hand_index]
        actions = self.available_actions(balance)
        return {
            "bet": round_.bet,
            "player_cards": [c.label for c in current.cards],
            "dealer_cards": [c.label for c in round_.dealer_cards]
            if reveal
            else [round_.dealer_cards[0].label, "hidden"],
            "player_score": self.score(current.cards),
            "dealer_score": self.score(round_.dealer_cards) if reveal else None,
            "status": round_.status,
            "message": round_.message,
            "can_double": "double" in actions,
            "can_split": "split" in actions,
            "can_surrender": "surrender" in actions,
            "available_actions": actions,
            "active_hand_index": round_.active_hand_index,
            "insurance_bet": round_.insurance_bet,
            "insurance_payout": round_.insurance_payout,
            "hands": [
                {
                    "cards": [c.label for c in h.cards],
                    "score": self.score(h.cards),
                    "bet": h.bet,
                    "status": h.status,
                    "message": h.message,
                    "from_split": h.from_split,
                    "doubled": h.doubled,
                }
                for h in round_.hands
            ],
            "rules": {
                "decks": self.blackjack_rules.decks,
                "dealer_soft_17": "hit" if self.blackjack_rules.dealer_hits_soft_17 else "stand",
                "blackjack_payout": f"{self.blackjack_rules.natural_numerator}:{self.blackjack_rules.natural_denominator}",
                "insurance_payout": "2:1",
                "max_hands": self.blackjack_rules.max_hands,
                "double_allowed": self.blackjack_rules.allow_double,
                "double_after_split": self.blackjack_rules.allow_double_after_split,
                "split_aces_one_card": True,
                "split_21_stands": True,
                "late_surrender": self.blackjack_rules.allow_surrender,
            },
        }

    def dump_state(self) -> dict | None:
        round_ = self.hand
        if round_ is None:
            return None
        return {
            "version": 5,
            "deck": [c.label for c in self.deck],
            "discarded_cards": [c.label for c in self.discarded_cards],
            "dealer_cards": [c.label for c in round_.dealer_cards],
            "hands": [
                {
                    "cards": [c.label for c in h.cards],
                    "bet": h.bet,
                    "status": h.status,
                    "from_split": h.from_split,
                    "split_aces": h.split_aces,
                    "doubled": h.doubled,
                    "message": h.message,
                }
                for h in round_.hands
            ],
            "status": round_.status,
            "message": round_.message,
            "active_hand_index": round_.active_hand_index,
            "insurance_bet": round_.insurance_bet,
            "insurance_decided": round_.insurance_decided,
            "insurance_payout": round_.insurance_payout,
            "initial_bet": round_.initial_bet,
            "round_id": round_.round_id,
        }

    def restore_state(self, state: dict | None) -> None:
        if state is None:
            self.hand, self.deck, self.discarded_cards = None, [], []
            return
        if not isinstance(state, dict):
            raise ValueError("Некорректное состояние раздачи блэкджека")
        if state.get("version") in {2, 3, 4, 5}:
            deck, discarded, round_ = self._read_versioned_state(state)
            discarded = self._restore_inventory(state["version"], deck, round_, discarded)
            self._validate_saved_round(round_)
            self.deck, self.hand = deck, round_
            self.discarded_cards = discarded
            return
        self._restore_legacy_state(state)

    def _restore_inventory(
        self, version: int, deck: list[Card], round_: BlackjackRound, discarded: list[Card]
    ) -> list[Card]:
        cards = (
            deck
            + round_.dealer_cards
            + [c for hand in round_.hands for c in hand.cards]
            + discarded
        )
        count = {(rank, suit): 0 for suit in self.suits for rank in self.ranks}
        for card in cards:
            count[(card.rank, card.suit)] += 1
        if any(n > self.blackjack_rules.decks for n in count.values()):
            raise ValueError("Некорректный состав башмака")
        if version in {4, 5}:
            if any(n != self.blackjack_rules.decks for n in count.values()):
                raise ValueError("Некорректный состав башмака")
            return discarded
        # Older saves did not record cards used by previous rounds.
        return [
            Card(rank, suit)
            for suit in self.suits
            for rank in self.ranks
            for _ in range(self.blackjack_rules.decks - count[(rank, suit)])
        ]

    def _read_versioned_state(self, state: dict) -> tuple[list[Card], list[Card], BlackjackRound]:
        try:
            if (
                not isinstance(state.get("deck"), list)
                or not isinstance(state.get("dealer_cards"), list)
                or not isinstance(state.get("hands"), list)
            ):
                raise ValueError
            if not isinstance(state.get("message"), str):
                raise ValueError
            if not isinstance(state.get("status"), str) or state["status"] not in BLACKJACK_PHASES:
                raise ValueError
            if (
                type(state.get("active_hand_index")) is not int
                or type(state.get("insurance_bet")) is not int
                or type(state.get("insurance_payout")) is not int
            ):
                raise ValueError
            if type(state.get("insurance_decided")) is not bool:
                raise ValueError
            if state.get("version") in {3, 4, 5} and type(state.get("initial_bet")) is not int:
                raise ValueError
            if state.get("version") in {4, 5} and not isinstance(
                state.get("discarded_cards"), list
            ):
                raise ValueError
            if (
                state.get("version") == 5
                and state.get("round_id") is not None
                and (not isinstance(state.get("round_id"), str) or not state["round_id"])
            ):
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("Некорректное состояние раздачи блэкджека") from None
        deck = [self._parse_card(c) for c in state["deck"]]
        discarded = (
            [self._parse_card(c) for c in state["discarded_cards"]]
            if state.get("version") in {4, 5}
            else []
        )
        dealer = [self._parse_card(c) for c in state["dealer_cards"]]
        hands = []
        for saved_hand in state["hands"]:
            if (
                not isinstance(saved_hand, dict)
                or not isinstance(saved_hand.get("cards"), list)
                or type(saved_hand.get("bet")) is not int
                or type(saved_hand.get("from_split")) is not bool
                or type(saved_hand.get("split_aces")) is not bool
                or type(saved_hand.get("doubled")) is not bool
                or not isinstance(saved_hand.get("message"), str)
                or not isinstance(saved_hand.get("status"), str)
                or saved_hand["status"] not in PLAYER_HAND_STATUSES
            ):
                raise ValueError("Некорректное состояние раздачи блэкджека")
            hands.append(
                PlayerHand(
                    [self._parse_card(c) for c in saved_hand["cards"]],
                    saved_hand["bet"],
                    cast(PlayerHandStatus, saved_hand["status"]),
                    saved_hand["from_split"],
                    saved_hand["split_aces"],
                    saved_hand["doubled"],
                    saved_hand["message"],
                )
            )
        initial_bet = state.get(
            "initial_bet", min((h.bet // 2 if h.doubled else h.bet for h in hands), default=0)
        )
        round_ = BlackjackRound(
            hands,
            dealer,
            cast(BlackjackPhase, state["status"]),
            state["message"],
            state["active_hand_index"],
            state["insurance_bet"],
            state["insurance_decided"],
            state["insurance_payout"],
            initial_bet,
            state.get("round_id"),
        )
        return deck, discarded, round_

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
        if not valid:
            raise ValueError("Некорректное состояние раздачи блэкджека")

    def _restore_legacy_state(self, state: dict) -> None:
        # Preserve an in-progress single-deck save from the previous version.
        if (
            state.get("version") is not None
            or not isinstance(state.get("player_cards"), list)
            or not isinstance(state.get("dealer_cards"), list)
            or not isinstance(state.get("deck"), list)
            or type(state.get("bet")) is not int
            or state.get("status") not in {"playing", "won", "lost", "push"}
        ):
            raise ValueError("Некорректное состояние раздачи блэкджека")
        old_cards = [self._parse_card(c) for c in state["player_cards"]]
        dealer = [self._parse_card(c) for c in state["dealer_cards"]]
        deck = [self._parse_card(c) for c in state["deck"]]
        labels = [c.label for c in old_cards + dealer + deck]
        if (
            len(labels) != 52
            or len(set(labels)) != 52
            or not old_cards
            or len(dealer) < 2
            or not self.minimum_bet <= state["bet"] <= self.rules.maximum_bet
            or state["bet"] % 2
            or state["bet"] % self.blackjack_rules.natural_denominator
            or (state["status"] == "playing" and self.score(old_cards) >= 21)
        ):
            raise ValueError("Некорректная колода в сохранённой раздаче блэкджека")
        if (
            "natural" in state
            and type(state["natural"]) is not bool
            or state.get("natural")
            and (not self._is_natural(old_cards) or self.score(dealer) == 21)
        ):
            raise ValueError("Некорректная натуральная рука в сохранённой раздаче блэкджека")
        status = cast(BlackjackPhase, state["status"])
        player_status = cast(
            PlayerHandStatus,
            "blackjack" if state.get("natural") and status == "won" else status,
        )
        bet = int(state["bet"])
        self.hand = BlackjackRound(
            [PlayerHand(old_cards, bet, player_status)],
            dealer,
            status,
            str(state.get("message", "Твой ход")),
            initial_bet=bet,
        )
        self.deck = deck
        present = {(rank, suit): 0 for suit in self.suits for rank in self.ranks}
        for card in deck + dealer + old_cards:
            present[(card.rank, card.suit)] += 1
        self.discarded_cards = [
            Card(rank, suit)
            for suit in self.suits
            for rank in self.ranks
            for _ in range(self.blackjack_rules.decks - present[(rank, suit)])
        ]

    def _parse_card(self, label: str) -> Card:
        if (
            not isinstance(label, str)
            or len(label) < 2
            or label[:-1] not in self.ranks
            or label[-1] not in self.suits
        ):
            raise ValueError("Некорректная карта в сохранённой раздаче блэкджека")
        return Card(label[:-1], label[-1])
