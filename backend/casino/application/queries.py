"""Read-side projections for the application layer."""

from __future__ import annotations

from collections.abc import Iterable

from casino.domain.blackjack import Blackjack
from casino.domain.core import GameCatalogItem
from casino.domain.models import Player
from casino.domain.round_verifier import verification_status
from casino.domain.slot_fairness import seed_hash


def casino_state(
    player: Player,
    games: Iterable[GameCatalogItem],
    blackjack: Blackjack,
    server_seed: str,
) -> dict[str, object]:
    """Build the public state view from one in-memory application snapshot."""
    rounds = []
    for round_ in reversed(player.rounds[-12:]):
        result = round_.to_dict()
        result["verification_status"] = verification_status(result)
        rounds.append(result)
    total = len(player.rounds)
    return {
        "player": {
            "name": player.name,
            "balance": player.balance,
            "rounds_played": total,
            "wins": player.wins,
            "losses": player.losses,
            "win_rate": round(player.wins / total * 100) if total else 0,
            "total_wagered": player.total_wagered,
        },
        "games": [game.catalog_info() for game in games],
        "history": rounds,
        "blackjack": blackjack.state(player.balance),
        "server_seed_hash": seed_hash(server_seed),
        "slots_server_seed_hash": seed_hash(server_seed),
    }
