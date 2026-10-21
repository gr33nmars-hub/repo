"""Read-side projections for the application layer."""

from __future__ import annotations

from collections.abc import Iterable

from casino.domain.blackjack import Blackjack
from casino.domain.core import GameCatalogItem
from casino.domain.models import GameResult, Player
from casino.domain.round_verifier import verification_status
from casino.domain.slot_fairness import seed_hash


def blackjack_view(blackjack: Blackjack, balance: int) -> dict[str, object] | None:
    round_ = blackjack.hand
    if round_ is None:
        return None

    rules = blackjack.blackjack_rules
    reveal = round_.status not in {"playing", "insurance"}
    current = round_.hands[round_.active_hand_index]
    actions = blackjack.available_actions(balance)
    return {
        "bet": round_.bet,
        "player_cards": [card.label for card in current.cards],
        "dealer_cards": [card.label for card in round_.dealer_cards]
        if reveal
        else [round_.dealer_cards[0].label, "hidden"],
        "player_score": blackjack.score(current.cards),
        "dealer_score": blackjack.score(round_.dealer_cards) if reveal else None,
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
                "cards": [card.label for card in hand.cards],
                "score": blackjack.score(hand.cards),
                "bet": hand.bet,
                "status": hand.status,
                "message": hand.message,
                "from_split": hand.from_split,
                "doubled": hand.doubled,
            }
            for hand in round_.hands
        ],
        "rules": {
            "decks": rules.decks,
            "dealer_soft_17": "hit" if rules.dealer_hits_soft_17 else "stand",
            "blackjack_payout": f"{rules.natural_numerator}:{rules.natural_denominator}",
            "insurance_payout": "2:1",
            "max_hands": rules.max_hands,
            "double_allowed": rules.allow_double,
            "double_after_split": rules.allow_double_after_split,
            "split_aces_one_card": True,
            "split_21_stands": True,
            "late_surrender": rules.allow_surrender,
        },
    }


def game_result_view(round_: GameResult) -> dict[str, object]:
    result: dict[str, object] = {
        "game_id": round_.game_id,
        "game_name": round_.game_name,
        "message": round_.message,
        "bet": round_.bet,
        "payout": round_.payout,
        "profit": round_.profit,
        "details": round_.details,
        "played_at": round_.played_at,
    }
    if round_.symbols is not None:
        result["symbols"] = round_.symbols
    if round_.reel_stops is not None:
        result["reel_stops"] = round_.reel_stops
    if round_.fairness is not None:
        result["fairness"] = round_.fairness
    if round_.round_id is not None:
        result["round_id"] = round_.round_id
    if round_.rule_version is not None:
        result.update(
            rule_version=round_.rule_version,
            rules_fingerprint=round_.rules_fingerprint,
            rules_snapshot=round_.rules_snapshot,
            outcome=round_.outcome,
        )
    return result


def casino_state(
    player: Player,
    games: Iterable[GameCatalogItem],
    blackjack: Blackjack,
    server_seed: str,
) -> dict[str, object]:
    """Build the public state view from one in-memory application snapshot."""
    rounds = []
    for round_ in reversed(player.rounds[-12:]):
        result = game_result_view(round_)
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
        "blackjack": blackjack_view(blackjack, player.balance),
        "server_seed_hash": seed_hash(server_seed),
        "slots_server_seed_hash": seed_hash(server_seed),
    }
