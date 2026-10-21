"""Детерминированная генерация случайных значений (Provably Fair) на базе HMAC-SHA256."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from itertools import count
from typing import TypeVar

T = TypeVar("T")


def new_server_seed() -> str:
    return secrets.token_hex(32)


def seed_hash(server_seed: str) -> str:
    return hashlib.sha256(server_seed.encode("utf-8")).hexdigest()


def digest(server_seed: str, client_seed: str, nonce: int, stream: str, index: int) -> bytes:
    message = f"{client_seed}:{nonce}:{stream}:{index}".encode()
    return hmac.new(server_seed.encode("utf-8"), message, hashlib.sha256).digest()


def bounded_int(
    server_seed: str, client_seed: str, nonce: int, stream: str, index: int, bound: int
) -> int:
    space = 1 << 256
    if type(bound) is not int or not 1 <= bound <= space:
        raise ValueError("Bound must be between 1 and 2**256")
    cutoff = space - space % bound
    for counter in count():
        candidate = int.from_bytes(
            digest(server_seed, client_seed, nonce, f"{stream}:{counter}", index), "big"
        )
        if candidate < cutoff:
            return candidate % bound
    raise AssertionError("unreachable")


def shuffle(values: list[T], server_seed: str, client_seed: str, nonce: int) -> None:
    """Перемешивание списка по алгоритму Фишера–Йетса с выборкой без смещения."""
    for index in range(len(values) - 1, 0, -1):
        other = bounded_int(server_seed, client_seed, nonce, "shuffle", index, index + 1)
        values[index], values[other] = values[other], values[index]
