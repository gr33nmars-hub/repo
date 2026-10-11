"""Deterministic, reproducible randomness for committed casino rounds."""

from __future__ import annotations

import hashlib
import hmac
from itertools import count
from typing import TypeVar

T = TypeVar("T")


def digest(server_seed: str, client_seed: str, nonce: int, stream: str, index: int) -> bytes:
    message = f"{client_seed}:{nonce}:{stream}:{index}".encode()
    return hmac.new(server_seed.encode("utf-8"), message, hashlib.sha256).digest()


def bounded_int(
    server_seed: str, client_seed: str, nonce: int, stream: str, index: int, bound: int
) -> int:
    if type(bound) is not int or bound < 1:
        raise ValueError("Bound must be a positive integer")
    space = 1 << 256
    cutoff = space - space % bound
    for counter in count():
        candidate = int.from_bytes(
            digest(server_seed, client_seed, nonce, f"{stream}:{counter}", index), "big"
        )
        if candidate < cutoff:
            return candidate % bound
    raise AssertionError("unreachable")


def shuffle(values: list[T], server_seed: str, client_seed: str, nonce: int) -> None:
    """In-place Fisher–Yates shuffle using unbiased HMAC bounded integers."""
    for index in range(len(values) - 1, 0, -1):
        other = bounded_int(server_seed, client_seed, nonce, "shuffle", index, index + 1)
        values[index], values[other] = values[other], values[index]
