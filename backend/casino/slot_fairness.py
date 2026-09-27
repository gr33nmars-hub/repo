"""Committed slot outcomes. A fresh server seed is committed before every spin."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from itertools import count


def new_server_seed() -> str:
    return secrets.token_hex(32)


def seed_hash(server_seed: str) -> str:
    return hashlib.sha256(server_seed.encode("utf-8")).hexdigest()


def reel_stops(server_seed: str, client_seed: str, lengths: list[int]) -> list[int]:
    """Map independent HMAC values to stops without modulo bias."""
    if any(type(length) is not int or length < 1 for length in lengths):
        raise ValueError("Reel lengths must be positive integers")
    key = server_seed.encode("utf-8")
    stops = []
    space = 1 << 256
    for index, length in enumerate(lengths):
        cutoff = space - space % length
        prefix = f"{client_seed}:0:{index}:".encode()
        for counter in count():
            candidate = int.from_bytes(
                hmac.new(key, prefix + str(counter).encode("ascii"), hashlib.sha256).digest(),
                "big",
            )
            if candidate < cutoff:
                stops.append(candidate % length)
                break
    return stops
