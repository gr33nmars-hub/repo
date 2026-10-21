from __future__ import annotations

from collections.abc import Iterable, Sequence

from .core import RandomSource
from .models import Card
from .provably_fair import shuffle as fair_shuffle


class Shoe:
    def __init__(
        self,
        cards: Iterable[Card] = (),
        discarded_cards: Iterable[Card] = (),
    ) -> None:
        self._cards = list(cards)
        self._discarded_cards = list(discarded_cards)

    @classmethod
    def full(cls, decks: int, suits: Sequence[str], ranks: Sequence[str]) -> Shoe:
        if type(decks) is not int or decks < 1:
            raise ValueError("Shoe requires at least one deck")
        return cls(Card(rank, suit) for _ in range(decks) for suit in suits for rank in ranks)

    @property
    def remaining_cards(self) -> tuple[Card, ...]:
        return tuple(self._cards)

    @property
    def discarded_cards(self) -> tuple[Card, ...]:
        return tuple(self._discarded_cards)

    @property
    def remaining_count(self) -> int:
        return len(self._cards)

    def draw(self) -> Card:
        if not self._cards:
            raise ValueError("В башмаке закончились карты")
        return self._cards.pop()

    def shuffle(self, rng: RandomSource) -> None:
        rng.shuffle(self._cards)

    def shuffle_fair(self, server_seed: str, client_seed: str, nonce: int) -> None:
        fair_shuffle(self._cards, server_seed, client_seed, nonce)
        self._cards.reverse()

    def discard(self, cards: Iterable[Card]) -> None:
        self._discarded_cards.extend(cards)

    def copy(self) -> Shoe:
        return Shoe(self._cards, self._discarded_cards)
