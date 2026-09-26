from __future__ import annotations

from dataclasses import dataclass

from casino.models import Card, GameResult


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
        if self.decks < 1 or self.max_hands < 1 or self.natural_numerator <= self.natural_denominator or self.natural_denominator < 1:
            raise ValueError("Invalid blackjack rules")


@dataclass(slots=True)
class PlayerHand:
    cards: list[Card]
    bet: int
    status: str = "playing"
    from_split: bool = False
    split_aces: bool = False
    doubled: bool = False
    message: str = ""


@dataclass(slots=True)
class BlackjackRound:
    hands: list[PlayerHand]
    dealer_cards: list[Card]
    status: str = "playing"
    message: str = "Твой ход"
    active_hand_index: int = 0
    insurance_bet: int = 0
    insurance_decided: bool = True
    insurance_payout: int = 0

    @property
    def bet(self) -> int:
        return sum(hand.bet for hand in self.hands) + self.insurance_bet

    @property
    def player_cards(self) -> list[Card]:
        return self.hands[self.active_hand_index].cards


class Blackjack:
    game_id, name = "blackjack", "Блэкджек"
    suits = ("♠", "♥", "♣", "♦")
    ranks = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")

    def __init__(self, rng=None, rules=None, blackjack_rules: BlackjackRules | None = None):
        # Import here because games.py re-exports this implementation.
        from casino.games import GameRules, SecureRandom
        self._rng = rng or SecureRandom()
        self.rules = rules or GameRules()
        self.blackjack_rules = blackjack_rules or BlackjackRules()
        self.hand: BlackjackRound | None = None
        self.deck: list[Card] = []

    @property
    def minimum_bet(self) -> int:
        return self.rules.minimum_bet

    @staticmethod
    def score(cards: list[Card]) -> int:
        total = sum(card.value for card in cards)
        aces = sum(card.rank == "A" for card in cards)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    @staticmethod
    def _soft(cards: list[Card]) -> bool:
        return any(c.rank == "A" for c in cards) and sum(1 if c.rank == "A" else c.value for c in cards) + 10 <= 21

    def _draw(self) -> Card:
        if not self.deck:
            raise ValueError("В башмаке закончились карты")
        return self.deck.pop()

    def _new_shoe(self) -> None:
        self.deck = [Card(rank, suit) for _ in range(self.blackjack_rules.decks) for suit in self.suits for rank in self.ranks]
        self._rng.shuffle(self.deck)

    def start(self, bet: int) -> BlackjackRound:
        if self.hand and self.hand.status in {"playing", "insurance"}:
            raise ValueError("Сначала закончи текущую раздачу")
        # Reshuffle between rounds only; keep enough cards for four long hands.
        if len(self.deck) < 60:
            self._new_shoe()
        player = [self._draw()]
        dealer = [self._draw()]
        player.append(self._draw())
        dealer.append(self._draw())
        self.hand = BlackjackRound([PlayerHand(player, bet)], dealer)
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
        player_natural = self.score(round_.hands[0].cards) == 21
        if dealer_natural:
            round_.insurance_payout = round_.insurance_bet * 3
            round_.hands[0].status = "push" if player_natural else "lost"
            round_.hands[0].message = "Оба имеют блэкджек" if player_natural else "Блэкджек дилера"
            payout = self._payout(round_)
            round_.status = "won" if payout > round_.bet else "lost" if payout < round_.bet else "push"
            round_.message = round_.hands[0].message
        elif player_natural:
            round_.hands[0].status = "blackjack"
            round_.hands[0].message = "Натуральный блэкджек · 3:2"
            round_.status = "won"
            round_.message = round_.hands[0].message
        else:
            round_.status = "playing"
            round_.message = "Твой ход"

    def available_actions(self, balance: int | None = None) -> list[str]:
        round_ = self.hand
        if round_ is None:
            return []
        if round_.status == "insurance":
            actions = ["decline_insurance"]
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
        if first_two and self.blackjack_rules.allow_double and (not current.from_split or self.blackjack_rules.allow_double_after_split) and (balance is None or balance >= current.bet):
            actions.append("double")
        if first_two and not current.from_split and self.blackjack_rules.allow_surrender:
            actions.append("surrender")
        if first_two and len(round_.hands) < self.blackjack_rules.max_hands and not current.split_aces and current.cards[0].value == current.cards[1].value and (balance is None or balance >= current.bet):
            actions.append("split")
        return actions

    def _require_round(self, status: str = "playing") -> BlackjackRound:
        if self.hand is None or self.hand.status != status:
            raise ValueError("Сейчас нет подходящей активной раздачи")
        return self.hand

    def _current(self, action: str) -> tuple[BlackjackRound, PlayerHand]:
        round_ = self._require_round()
        if action not in self.available_actions():
            raise ValueError("Это действие сейчас недоступно")
        return round_, round_.hands[round_.active_hand_index]

    def _advance(self) -> None:
        round_ = self._require_round()
        next_index = next((i for i in range(round_.active_hand_index + 1, len(round_.hands)) if round_.hands[i].status == "playing"), None)
        if next_index is not None:
            round_.active_hand_index = next_index
            next_hand = round_.hands[next_index]
            if len(next_hand.cards) == 1:
                next_hand.cards.append(self._draw())
            round_.message = f"Рука {next_index + 1}: твой ход"
        else:
            self._settle()

    def hit(self) -> BlackjackRound:
        round_, current = self._current("hit")
        current.cards.append(self._draw())
        if self.score(current.cards) > 21:
            current.status, current.message = "bust", "Перебор"
            self._advance()
        elif self.score(current.cards) == 21:
            current.status = "standing"
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
        current.message = "Перебор после удвоения" if current.status == "bust" else "Удвоение · одна карта"
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
        if ace:
            new.cards.append(self._draw())
            current.status = new.status = "standing"
            current.message = new.message = "После разделения тузов выдана одна карта"
            self._advance()
        return round_

    def surrender(self) -> BlackjackRound:
        round_, current = self._current("surrender")
        current.status, current.message = "surrendered", "Сдача · возвращена половина ставки"
        self._advance()
        return round_

    def _settle(self) -> None:
        round_ = self._require_round()
        contenders = [h for h in round_.hands if h.status == "standing"]
        if contenders:
            while self.score(round_.dealer_cards) < 17 or (self.blackjack_rules.dealer_hits_soft_17 and self.score(round_.dealer_cards) == 17 and self._soft(round_.dealer_cards)):
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
        round_.status = "mixed" if wins and losses else "won" if payout > round_.bet else "lost" if payout < round_.bet else "push"
        round_.message = " · ".join(f"Рука {i + 1}: {h.message or h.status}" for i, h in enumerate(round_.hands))

    def _payout(self, round_: BlackjackRound) -> int:
        payout = round_.insurance_payout
        for hand in round_.hands:
            if hand.status == "blackjack":
                payout += hand.bet * (self.blackjack_rules.natural_denominator + self.blackjack_rules.natural_numerator) // self.blackjack_rules.natural_denominator
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
        details = "  ·  ".join(f"Рука {i + 1}: {' '.join(c.label for c in h.cards)} ({self.score(h.cards)}), {h.status}" for i, h in enumerate(round_.hands))
        details += f"  ·  Дилер: {' '.join(c.label for c in round_.dealer_cards)} ({self.score(round_.dealer_cards)})"
        if round_.insurance_bet:
            details += f"  ·  Страховка: {round_.insurance_bet} → {round_.insurance_payout}"
        return GameResult(self.game_id, self.name, round_.message, round_.bet, payout, details)

    def play(self, bet: int, choice: str = "") -> GameResult:
        round_ = self.start(bet)
        if round_.status == "insurance":
            self.insurance(False)
        while round_.status == "playing":
            self.hit() if self.score(round_.player_cards) < 17 else self.stand()
        return self.result()

    def state(self, balance: int | None = None) -> dict | None:
        round_ = self.hand
        if round_ is None:
            return None
        reveal = round_.status not in {"playing", "insurance"}
        current = round_.hands[round_.active_hand_index]
        actions = self.available_actions(balance)
        return {"bet": round_.bet, "player_cards": [c.label for c in current.cards],
                "dealer_cards": [c.label for c in round_.dealer_cards] if reveal else [round_.dealer_cards[0].label, "hidden"],
                "player_score": self.score(current.cards), "dealer_score": self.score(round_.dealer_cards) if reveal else None,
                "status": round_.status, "message": round_.message, "can_double": "double" in actions,
                "can_split": "split" in actions, "can_surrender": "surrender" in actions,
                "available_actions": actions, "active_hand_index": round_.active_hand_index,
                "insurance_bet": round_.insurance_bet, "insurance_payout": round_.insurance_payout,
                "hands": [{"cards": [c.label for c in h.cards], "score": self.score(h.cards), "bet": h.bet,
                           "status": h.status, "message": h.message, "from_split": h.from_split,
                           "doubled": h.doubled} for h in round_.hands],
                "rules": {"decks": self.blackjack_rules.decks, "dealer_soft_17": "hit" if self.blackjack_rules.dealer_hits_soft_17 else "stand",
                          "blackjack_payout": "3:2", "insurance_payout": "2:1", "max_hands": self.blackjack_rules.max_hands,
                          "double_after_split": self.blackjack_rules.allow_double_after_split,
                          "split_aces_one_card": True, "late_surrender": self.blackjack_rules.allow_surrender}}

    def dump_state(self) -> dict | None:
        round_ = self.hand
        if round_ is None:
            return None
        return {"version": 2, "deck": [c.label for c in self.deck], "dealer_cards": [c.label for c in round_.dealer_cards],
                "hands": [{"cards": [c.label for c in h.cards], "bet": h.bet, "status": h.status,
                           "from_split": h.from_split, "split_aces": h.split_aces, "doubled": h.doubled,
                           "message": h.message} for h in round_.hands],
                "status": round_.status, "message": round_.message, "active_hand_index": round_.active_hand_index,
                "insurance_bet": round_.insurance_bet, "insurance_decided": round_.insurance_decided,
                "insurance_payout": round_.insurance_payout}

    def restore_state(self, state: dict | None) -> None:
        if not state:
            self.hand, self.deck = None, []
            return
        if state.get("version") == 2:
            deck = [self._parse_card(c) for c in state["deck"]]
            dealer = [self._parse_card(c) for c in state["dealer_cards"]]
            hands = [PlayerHand([self._parse_card(c) for c in h["cards"]], int(h["bet"]), str(h["status"]),
                                bool(h["from_split"]), bool(h["split_aces"]), bool(h["doubled"]), str(h["message"])) for h in state["hands"]]
            round_ = BlackjackRound(hands, dealer, str(state["status"]), str(state["message"]), int(state["active_hand_index"]),
                                    int(state["insurance_bet"]), bool(state["insurance_decided"]), int(state["insurance_payout"]))
            cards = deck + dealer + [c for h in hands for c in h.cards]
            count = {(r, s): 0 for s in self.suits for r in self.ranks}
            for card in cards:
                count[(card.rank, card.suit)] += 1
            if (not hands or not 0 <= round_.active_hand_index < len(hands) or len(hands) > self.blackjack_rules.max_hands
                    or len(dealer) < 2 or any(h.bet < 1 or not h.cards or (len(h.cards) == 1 and (not h.from_split or h.status != "playing")) for h in hands)
                    or any(n > self.blackjack_rules.decks for n in count.values())
                    or round_.status not in {"playing", "insurance", "won", "lost", "push", "mixed"}
                    or round_.insurance_bet < 0):
                raise ValueError("Некорректное состояние раздачи блэкджека")
            self.deck, self.hand = deck, round_
            return
        # Preserve an in-progress single-deck save from the previous version.
        old_cards = [self._parse_card(c) for c in state["player_cards"]]
        dealer = [self._parse_card(c) for c in state["dealer_cards"]]
        deck = [self._parse_card(c) for c in state["deck"]]
        labels = [c.label for c in old_cards + dealer + deck]
        if len(labels) != 52 or len(set(labels)) != 52:
            raise ValueError("Некорректная колода в сохранённой раздаче блэкджека")
        status = str(state["status"])
        player_status = "blackjack" if state.get("natural") and status == "won" else status
        self.hand = BlackjackRound([PlayerHand(old_cards, int(state["bet"]), player_status)], dealer, status, str(state.get("message", "Твой ход")))
        self.deck = deck

    def _parse_card(self, label: str) -> Card:
        if not isinstance(label, str) or len(label) < 2 or label[:-1] not in self.ranks or label[-1] not in self.suits:
            raise ValueError("Некорректная карта в сохранённой раздаче блэкджека")
        return Card(label[:-1], label[-1])
