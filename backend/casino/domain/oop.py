"""Reusable object-oriented building blocks for the Python domain model.

The HTTP boundary still uses JSON objects, while mutable in-memory registries use
``PairMap`` so game code does not depend on the built-in ``dict`` type.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, MutableMapping
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class ComparableEntity(ABC):
    """Base class for domain entities with explicit value comparison and display."""

    @abstractmethod
    def comparison_key(self) -> tuple[object, ...]:
        """Return stable, comparable values that identify this entity."""

    def __eq__(self, other: object) -> bool:
        return type(self) is type(other) and self.comparison_key() == other.comparison_key()  # type: ignore[union-attr]

    def __lt__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self.comparison_key() < other.comparison_key()  # type: ignore[union-attr]

    def __repr__(self) -> str:
        values = ", ".join(repr(value) for value in self.comparison_key())
        return f"{type(self).__name__}({values})"

    def __str__(self) -> str:
        return ": ".join(str(value) for value in self.comparison_key())


class PairMap(MutableMapping[K, V], Generic[K, V]):
    """Small ordered mapping backed by key-value pairs instead of ``dict``.

    It deliberately exposes the normal mapping protocol so it can replace an
    internal registry without changing callers or public API DTOs.
    """

    def __init__(self, entries: tuple[tuple[K, V], ...] = ()) -> None:
        self._entries: list[tuple[K, V]] = []
        for key, value in entries:
            self[key] = value

    @property
    def entries(self) -> tuple[tuple[K, V], ...]:
        return tuple(self._entries)

    def __getitem__(self, key: K) -> V:
        for stored_key, value in self._entries:
            if stored_key == key:
                return value
        raise KeyError(key)

    def __setitem__(self, key: K, value: V) -> None:
        for index, (stored_key, _) in enumerate(self._entries):
            if stored_key == key:
                self._entries[index] = (key, value)
                return
        self._entries.append((key, value))

    def __delitem__(self, key: K) -> None:
        for index, (stored_key, _) in enumerate(self._entries):
            if stored_key == key:
                del self._entries[index]
                return
        raise KeyError(key)

    def __iter__(self) -> Iterator[K]:
        return (key for key, _ in self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        entries = ", ".join(f"{key!r}: {value!r}" for key, value in self._entries)
        return f"PairMap({entries})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PairMap) and self.entries == other.entries
