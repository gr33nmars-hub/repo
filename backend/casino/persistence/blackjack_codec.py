from __future__ import annotations

from copy import deepcopy
from typing import cast

from casino.domain.blackjack import (
    BLACKJACK_PHASES,
    PLAYER_HAND_STATUSES,
    Blackjack,
    BlackjackPhase,
    BlackjackRound,
    BlackjackSnapshot,
    PlayerHand,
    PlayerHandStatus,
)
from casino.domain.models import Card
from casino.domain.shoe import Shoe


class BlackjackStateCodec:
    @staticmethod
    def encode(snapshot: BlackjackSnapshot | None) -> dict | None:
        if snapshot is None or snapshot.hand is None:
            return None

        round_ = snapshot.hand
        state = {
            "version": 5,
            "deck": [card.label for card in snapshot.shoe.remaining_cards],
            "discarded_cards": [card.label for card in snapshot.shoe.discarded_cards],
            "dealer_cards": [card.label for card in round_.dealer_cards],
            "hands": [
                {
                    "cards": [card.label for card in hand.cards],
                    "bet": hand.bet,
                    "status": hand.status,
                    "from_split": hand.from_split,
                    "split_aces": hand.split_aces,
                    "doubled": hand.doubled,
                    "message": hand.message,
                }
                for hand in round_.hands
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
        if round_.fairness is not None:
            state["fairness"] = deepcopy(round_.fairness)
            state["draw_order"] = list(round_.draw_order or [])
            state["draw_events"] = [event.copy() for event in round_.draw_events or []]
        return state

    @classmethod
    def decode(cls, state: dict | None) -> BlackjackSnapshot | None:
        if state is None:
            return None
        if type(state) is not dict:
            raise ValueError("Некорректное состояние раздачи блэкджека")

        game = Blackjack()
        version = state.get("version")
        if version in {2, 3, 4, 5}:
            snapshot = cls._decode_versioned(state, game)
        else:
            snapshot = cls._decode_legacy(state, game)
        game.restore_snapshot(snapshot)
        return snapshot

    @classmethod
    def _decode_versioned(cls, state: dict, game: Blackjack) -> BlackjackSnapshot:
        try:
            version = state.get("version")
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
            if version in {3, 4, 5} and type(state.get("initial_bet")) is not int:
                raise ValueError
            if version in {4, 5} and not isinstance(state.get("discarded_cards"), list):
                raise ValueError
            if (
                version == 5
                and state.get("round_id") is not None
                and (not isinstance(state.get("round_id"), str) or not state["round_id"])
            ):
                raise ValueError
            deck = [cls._parse_card(card, game) for card in state["deck"]]
            discarded = (
                [cls._parse_card(card, game) for card in state["discarded_cards"]]
                if version in {4, 5}
                else []
            )
            dealer = [cls._parse_card(card, game) for card in state["dealer_cards"]]
            hands = [cls._decode_hand(saved_hand, game) for saved_hand in state["hands"]]
        except (TypeError, ValueError, KeyError):
            raise ValueError("Некорректное состояние раздачи блэкджека") from None

        initial_bet = state.get(
            "initial_bet",
            min((hand.bet // 2 if hand.doubled else hand.bet for hand in hands), default=0),
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
            deepcopy(state.get("fairness")) if type(state.get("fairness")) is dict else None,
            list(state["draw_order"]) if type(state.get("draw_order")) is list else [],
            deepcopy(state.get("draw_events")) if type(state.get("draw_events")) is list else None,
        )
        if state.get("version") == 5 and (
            ("fairness" in state and type(state["fairness"]) is not dict)
            or ("draw_order" in state and type(state["draw_order"]) is not list)
            or ("draw_events" in state and type(state["draw_events"]) is not list)
            or (("fairness" in state) != ("draw_order" in state))
        ):
            raise ValueError("Некорректное состояние раздачи блэкджека")

        counts = cls._card_counts(deck, discarded, round_)
        if any(count > game.blackjack_rules.decks for count in counts.values()):
            raise ValueError("Некорректный состав башмака")
        if version in {4, 5}:
            if any(count != game.blackjack_rules.decks for count in counts.values()):
                raise ValueError("Некорректный состав башмака")
        else:
            discarded = [
                Card(rank, suit)
                for suit in game.suits
                for rank in game.ranks
                for _ in range(game.blackjack_rules.decks - counts[(rank, suit)])
            ]
        return BlackjackSnapshot(round_, Shoe(deck, discarded))

    @classmethod
    def _decode_hand(cls, state: object, game: Blackjack) -> PlayerHand:
        if (
            type(state) is not dict
            or not isinstance(state.get("cards"), list)
            or type(state.get("bet")) is not int
            or type(state.get("from_split")) is not bool
            or type(state.get("split_aces")) is not bool
            or type(state.get("doubled")) is not bool
            or not isinstance(state.get("message"), str)
            or not isinstance(state.get("status"), str)
            or state["status"] not in PLAYER_HAND_STATUSES
        ):
            raise ValueError("Некорректное состояние раздачи блэкджека")
        return PlayerHand(
            [cls._parse_card(card, game) for card in state["cards"]],
            state["bet"],
            cast(PlayerHandStatus, state["status"]),
            state["from_split"],
            state["split_aces"],
            state["doubled"],
            state["message"],
        )

    @classmethod
    def _decode_legacy(cls, state: dict, game: Blackjack) -> BlackjackSnapshot:
        if (
            state.get("version") is not None
            or not isinstance(state.get("player_cards"), list)
            or not isinstance(state.get("dealer_cards"), list)
            or not isinstance(state.get("deck"), list)
            or type(state.get("bet")) is not int
            or state.get("status") not in {"playing", "won", "lost", "push"}
        ):
            raise ValueError("Некорректное состояние раздачи блэкджека")
        player = [cls._parse_card(label, game) for label in state["player_cards"]]
        dealer = [cls._parse_card(label, game) for label in state["dealer_cards"]]
        deck = [cls._parse_card(label, game) for label in state["deck"]]
        labels = [card.label for card in player + dealer + deck]
        bet = state["bet"]
        if (
            len(labels) != 52
            or len(set(labels)) != 52
            or not player
            or len(dealer) < 2
            or not game.minimum_bet <= bet <= game.rules.maximum_bet
            or bet % 2
            or bet % game.blackjack_rules.natural_denominator
            or (state["status"] == "playing" and game.score(player) >= 21)
        ):
            raise ValueError("Некорректная колода в сохранённой раздаче блэкджека")
        if (
            "natural" in state
            and type(state["natural"]) is not bool
            or state.get("natural")
            and (not game._is_natural(player) or game.score(dealer) == 21)
        ):
            raise ValueError("Некорректная натуральная рука в сохранённой раздаче блэкджека")
        status = cast(BlackjackPhase, state["status"])
        player_status = cast(
            PlayerHandStatus,
            "blackjack" if state.get("natural") and status == "won" else status,
        )
        round_ = BlackjackRound(
            [PlayerHand(player, bet, player_status)],
            dealer,
            status,
            str(state.get("message", "Твой ход")),
            initial_bet=bet,
        )
        counts = cls._card_counts(deck, [], round_)
        discarded = [
            Card(rank, suit)
            for suit in game.suits
            for rank in game.ranks
            for _ in range(game.blackjack_rules.decks - counts[(rank, suit)])
        ]
        return BlackjackSnapshot(round_, Shoe(deck, discarded))

    @staticmethod
    def _card_counts(
        deck: list[Card], discarded: list[Card], round_: BlackjackRound
    ) -> dict[tuple[str, str], int]:
        counts = {(rank, suit): 0 for suit in Blackjack.suits for rank in Blackjack.ranks}
        cards = (
            deck
            + discarded
            + round_.dealer_cards
            + [card for hand in round_.hands for card in hand.cards]
        )
        for card in cards:
            counts[(card.rank, card.suit)] += 1
        return counts

    @staticmethod
    def _parse_card(label: object, game: Blackjack) -> Card:
        if (
            not isinstance(label, str)
            or len(label) < 2
            or label[:-1] not in game.ranks
            or label[-1] not in game.suits
        ):
            raise ValueError("Некорректная карта в сохранённой раздаче блэкджека")
        return Card(label[:-1], label[-1])
