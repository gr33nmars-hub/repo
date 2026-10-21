"""Independent validation of persisted v1 round outcomes and payouts."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

_RED_NUMBERS = frozenset({1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36})


def verification_status(result: dict[str, Any]) -> str:
    """Return verified, invalid, or legacy-unverified for one serialized round."""
    if all(
        result.get(key) is None
        for key in ("rule_version", "rules_fingerprint", "rules_snapshot", "outcome")
    ):
        return "legacy-unverified"
    if not verify_recorded_round(result):
        return "invalid"
    if (
        result.get("game_id") == "blackjack"
        and result.get("fairness") is not None
        and not isinstance(result.get("outcome", {}).get("draw_events"), list)
    ):
        return "legacy-unverified"
    if result.get("game_id") in {"roulette", "blackjack"} and result.get("fairness") is None:
        return "legacy-unverified"
    return "verified"


def verify_recorded_round(result: dict[str, Any]) -> bool:
    """Check stored rule fingerprint, outcome evidence, and payout without game objects."""
    try:
        version = result.get("rule_version")
        snapshot = result.get("rules_snapshot")
        outcome = result.get("outcome")
        if not _metadata_matches(version, result.get("rules_fingerprint"), snapshot, outcome):
            return False
        if type(snapshot) is not dict or type(outcome) is not dict:
            return False
        bet, payout = result.get("bet"), result.get("payout")
        if type(bet) is not int or bet < 1 or type(payout) is not int or payout < 0:
            return False
        if result.get("profit") != payout - bet:
            return False
        if version == "slots-v1":
            return _verify_slots(result, snapshot, outcome)
        if version == "roulette-v1":
            return _verify_roulette(bet, payout, snapshot, outcome, result.get("fairness"))
        if version == "blackjack-v1":
            return _verify_blackjack(bet, payout, snapshot, outcome, result.get("fairness"))
    except (KeyError, TypeError, ValueError, IndexError, OverflowError):
        return False
    else:
        return False


def _verify_slots(
    result: dict[str, Any], snapshot: dict[str, Any], outcome: dict[str, Any]
) -> bool:
    proof = result.get("fairness")
    reels = snapshot.get("reels")
    triples = snapshot.get("triples")
    stops = result.get("reel_stops")
    symbols = result.get("symbols")
    if (
        type(proof) is not dict
        or type(proof.get("server_seed")) is not str
        or len(proof["server_seed"]) != 64
        or any(char not in "0123456789abcdef" for char in proof["server_seed"])
        or type(proof.get("client_seed")) is not str
        or type(proof.get("nonce")) is not int
        or proof["nonce"] != 0
        or proof.get("server_seed_hash") != _seed_hash(proof["server_seed"])
        or type(reels) is not list
        or len(reels) != 3
        or type(triples) is not list
        or type(stops) is not list
        or len(stops) != 3
        or type(symbols) is not list
        or len(symbols) != 3
        or outcome.get("reel_stops") != stops
        or outcome.get("symbols") != symbols
    ):
        return False
    if any(
        type(reel) is not list or not reel or any(type(symbol) is not str for symbol in reel)
        for reel in reels
    ):
        return False
    if any(
        type(stop) is not int or not 0 <= stop < len(reels[index])
        for index, stop in enumerate(stops)
    ):
        return False
    expected_stops = _reel_stops(
        proof["server_seed"], proof["client_seed"], [len(reel) for reel in reels]
    )
    expected_symbols = [reels[index][stop] for index, stop in enumerate(expected_stops)]
    if stops != expected_stops or symbols != expected_symbols:
        return False
    if type(snapshot.get("pair_multiplier")) is not int or snapshot["pair_multiplier"] < 0:
        return False
    paytable: dict[str, int] = {}
    for item in triples:
        if (
            type(item) is not dict
            or type(item.get("symbol")) is not str
            or type(item.get("multiplier")) is not int
            or item["multiplier"] < 0
            or item["symbol"] in paytable
        ):
            return False
        paytable[item["symbol"]] = item["multiplier"]
    if symbols[0] == symbols[1] == symbols[2]:
        multiplier = paytable.get(symbols[0], 0)
    elif len(set(symbols)) == 2:
        multiplier = snapshot["pair_multiplier"]
    else:
        multiplier = 0
    return result["payout"] == result["bet"] * multiplier


def _verify_roulette(
    bet: int,
    payout: int,
    snapshot: dict[str, Any],
    outcome: dict[str, Any],
    proof: dict[str, Any] | None = None,
) -> bool:
    wheel = snapshot.get("wheel")
    red_numbers = snapshot.get("red_numbers")
    number, choice, color = (
        outcome.get("number"),
        outcome.get("choice"),
        outcome.get("color"),
    )
    if (
        wheel != list(range(37))
        or type(red_numbers) is not list
        or any(type(number) is not int for number in red_numbers)
        or set(red_numbers) != _RED_NUMBERS
        or type(number) is not int
        or number not in wheel
        or choice not in {"red", "black", "zero"}
    ):
        return False
    if proof is not None and not _valid_proof(proof):
        return False
    if proof is not None and number != _bounded_int(
        proof["server_seed"], proof["client_seed"], proof["nonce"], "roulette", 0, 37
    ):
        return False
    expected_color = "zero" if number == 0 else "red" if number in red_numbers else "black"
    if color != expected_color:
        return False
    color_multiplier = snapshot.get("color_return_multiplier")
    number_multiplier = snapshot.get("number_return_multiplier")
    if (
        type(color_multiplier) is not int
        or color_multiplier < 1
        or type(number_multiplier) is not int
        or number_multiplier < 1
    ):
        return False
    expected_payout = (
        bet * (number_multiplier if choice == "zero" else color_multiplier)
        if choice == color
        else 0
    )
    return payout == expected_payout


def _card_score(cards: list[str]) -> tuple[int, bool]:
    values = []
    aces = 0
    for card in cards:
        rank = card[:-1]
        if rank == "A":
            aces += 1
            values.append(1)
        elif rank in {"J", "Q", "K"}:
            values.append(10)
        elif rank.isdigit() and 2 <= int(rank) <= 10:
            values.append(int(rank))
        else:
            raise ValueError("Invalid card")
    total = sum(values)
    soft = aces > 0 and total + 10 <= 21
    return total + 10 if soft else total, soft


def _dealer_draws_follow_rules(cards: list[str], hits_soft_17: bool) -> bool:
    if len(cards) < 2:
        return False
    dealt = list(cards[:2])
    score, soft = _card_score(dealt)
    for card in cards[2:]:
        should_hit = score < 17 or (hits_soft_17 and score == 17 and soft)
        if not should_hit:
            return False
        dealt.append(card)
        score, soft = _card_score(dealt)
    return score >= 17 and not (hits_soft_17 and score == 17 and soft)


def _verify_blackjack(
    bet: int,
    payout: int,
    snapshot: dict[str, Any],
    outcome: dict[str, Any],
    proof: dict[str, Any] | None = None,
) -> bool:
    dealer_cards = outcome.get("dealer_cards")
    hands = outcome.get("hands")
    if type(dealer_cards) is not list or not dealer_cards or type(hands) is not list or not hands:
        return False
    if proof is not None and not _valid_proof(proof):
        return False
    if proof is not None:
        draw_order = outcome.get("draw_order")
        if (
            type(draw_order) is not list
            or not draw_order
            or any(type(card) is not str for card in draw_order)
        ):
            return False
        shoe = [
            f"{rank}{suit}"
            for _ in range(snapshot.get("decks", 0))
            for suit in ("♠", "♥", "♣", "♦")
            for rank in ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
        ]
        _shuffle(shoe, proof["server_seed"], proof["client_seed"], proof["nonce"])
        if len(draw_order) > len(shoe) or draw_order != shoe[: len(draw_order)]:
            return False
        draw_events = outcome.get("draw_events")
        if draw_events is not None:
            if not _draw_events_match(draw_order, draw_events, dealer_cards, hands):
                return False
        else:
            recorded_cards = dealer_cards + [
                card for hand in hands if type(hand) is dict for card in hand.get("cards", [])
            ]
            if sorted(recorded_cards) != sorted(draw_order):
                return False
    if any(type(card) is not str or card[-1:] not in {"♠", "♥", "♣", "♦"} for card in dealer_cards):
        return False
    dealer_score, _ = _card_score(dealer_cards)
    dealer_natural = len(dealer_cards) == 2 and dealer_score == 21
    insurance_bet, insurance_payout = outcome.get("insurance_bet"), outcome.get("insurance_payout")
    initial_bet = outcome.get("initial_bet")
    if (
        type(initial_bet) is not int
        or initial_bet < 1
        or type(insurance_bet) is not int
        or insurance_bet not in {0, initial_bet // 2}
        or (insurance_bet > 0 and dealer_cards[0][:-1] != "A")
        or type(insurance_payout) is not int
        or insurance_payout != (insurance_bet * 3 if dealer_natural else 0)
        or any(type(hand) is not dict for hand in hands)
    ):
        return False
    hand_bets = [hand.get("bet") for hand in hands]
    if any(type(hand_bet) is not int or hand_bet < 1 for hand_bet in hand_bets):
        return False
    if sum(hand_bets) + insurance_bet != bet:
        return False
    if (
        type(snapshot.get("natural_numerator")) is not int
        or type(snapshot.get("natural_denominator")) is not int
    ):
        return False
    natural_num, natural_den = snapshot["natural_numerator"], snapshot["natural_denominator"]
    if natural_num <= natural_den or natural_den < 1:
        return False
    decks = snapshot.get("decks")
    if (
        type(snapshot.get("late_surrender")) is not bool
        or type(decks) is not int
        or decks < 1
        or snapshot.get("insurance_profit_multiplier") != 2
        or type(snapshot.get("minimum_bet")) is not int
        or type(snapshot.get("maximum_bet")) is not int
        or snapshot["minimum_bet"] < 1
        or snapshot["maximum_bet"] < snapshot["minimum_bet"]
        or type(snapshot.get("max_hands")) is not int
        or snapshot["max_hands"] < 1
        or len(hands) > snapshot["max_hands"]
        or type(snapshot.get("allow_double")) is not bool
        or type(snapshot.get("allow_double_after_split")) is not bool
        or snapshot.get("split_aces_one_card") is not True
        or snapshot.get("split_aces_resplit") is not False
    ):
        return False
    if (
        not snapshot["minimum_bet"] <= initial_bet <= snapshot["maximum_bet"]
        or initial_bet % 2
        or initial_bet % natural_den
    ):
        return False

    dealer_hits_soft_17 = snapshot.get("dealer_hits_soft_17")
    if type(dealer_hits_soft_17) is not bool:
        return False

    expected_payout = insurance_payout
    contenders = 0
    card_counts: dict[str, int] = {}
    for hand in hands:
        if type(hand) is not dict:
            return False
        cards, hand_bet, status = hand.get("cards"), hand.get("bet"), hand.get("status")
        from_split = hand.get("from_split")
        doubled = hand.get("doubled")
        split_aces = hand.get("split_aces")
        if (
            type(cards) is not list
            or len(cards) < 2
            or any(type(card) is not str or card[-1:] not in {"♠", "♥", "♣", "♦"} for card in cards)
            or type(hand_bet) is not int
            or hand_bet < 1
            or type(from_split) is not bool
            or type(doubled) is not bool
            or type(split_aces) is not bool
            or hand_bet != initial_bet * (2 if doubled else 1)
            or hand_bet > snapshot["maximum_bet"]
            or (doubled and len(cards) != 3)
            or (doubled and not snapshot["allow_double"])
            or (doubled and from_split and not snapshot["allow_double_after_split"])
            or (doubled and split_aces)
            or (split_aces and (not from_split or cards[0][:-1] != "A" or len(cards) != 2))
        ):
            return False
        score, _ = _card_score(cards)
        for card in cards:
            card_counts[card] = card_counts.get(card, 0) + 1
            if card_counts[card] > decks:
                return False
        natural = len(cards) == 2 and score == 21 and not from_split
        if dealer_natural:
            expected_status = "push" if natural else "lost"
        elif status == "blackjack":
            if not natural:
                return False
            expected_status = "blackjack"
        elif status == "surrendered":
            if len(cards) != 2 or from_split or doubled or not snapshot["late_surrender"]:
                return False
            expected_status = "surrendered"
        elif status == "bust":
            if score <= 21:
                return False
            expected_status = "bust"
        else:
            if score > 21:
                return False
            contenders += 1
            if dealer_score > 21 or score > dealer_score:
                expected_status = "won"
            elif score == dealer_score:
                expected_status = "push"
            else:
                expected_status = "lost"
        if status != expected_status:
            return False
        if status == "blackjack":
            expected_payout += hand_bet * (natural_den + natural_num) // natural_den
        elif status == "won":
            expected_payout += hand_bet * 2
        elif status == "push":
            expected_payout += hand_bet
        elif status == "surrendered":
            expected_payout += hand_bet // 2

    for card in dealer_cards:
        card_counts[card] = card_counts.get(card, 0) + 1
        if card_counts[card] > decks:
            return False

    if contenders and not _dealer_draws_follow_rules(dealer_cards, dealer_hits_soft_17):
        return False
    if not contenders and len(dealer_cards) != 2:
        return False
    return payout == expected_payout


def _draw_events_match(
    draw_order: list[str], events: object, dealer_cards: list[Any], hands: list[Any]
) -> bool:
    if type(events) is not list or len(events) != len(draw_order):
        return False
    dealer: list[str] = []
    allocated: list[list[str]] = [[] for _ in hands]
    for card, event in zip(draw_order, events, strict=True):
        if (
            type(event) is not dict
            or set(event) != {"card", "target"}
            or event.get("card") != card
            or type(event.get("target")) is not str
        ):
            return False
        target = event["target"]
        if target == "dealer":
            dealer.append(card)
            continue
        if not target.startswith("hand:") or not target.removeprefix("hand:").isdigit():
            return False
        index = int(target.removeprefix("hand:"))
        if not 0 <= index < len(allocated):
            return False
        allocated[index].append(card)
    return dealer == dealer_cards and allocated == [hand.get("cards") for hand in hands]


def _valid_proof(proof: dict[str, Any] | None) -> bool:
    return bool(
        type(proof) is dict
        and type(proof.get("server_seed")) is str
        and len(proof["server_seed"]) == 64
        and all(char in "0123456789abcdef" for char in proof["server_seed"])
        and type(proof.get("client_seed")) is str
        and type(proof.get("nonce")) is int
        and proof["nonce"] >= 0
        and proof.get("server_seed_hash") == _seed_hash(proof["server_seed"])
    )


def _metadata_matches(
    version: Any,
    fingerprint: Any,
    snapshot: Any,
    outcome: Any,
) -> bool:
    if version is fingerprint is snapshot is outcome is None:
        return True
    if (
        type(version) is not str
        or not version
        or type(snapshot) is not dict
        or type(outcome) is not dict
        or type(fingerprint) is not str
        or len(fingerprint) != 64
        or any(character not in "0123456789abcdef" for character in fingerprint)
    ):
        return False
    try:
        canonical = json.dumps(
            {"version": version, "rules": snapshot},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        json.dumps(outcome, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest() == fingerprint


def _seed_hash(server_seed: str) -> str:
    return hashlib.sha256(server_seed.encode("utf-8")).hexdigest()


def _bounded_int(
    server_seed: str, client_seed: str, nonce: int, stream: str, index: int, bound: int
) -> int:
    space = 1 << 256
    cutoff = space - space % bound
    counter = 0
    while True:
        message = f"{client_seed}:{nonce}:{stream}:{counter}:{index}".encode()
        candidate = int.from_bytes(
            hmac.new(server_seed.encode("utf-8"), message, hashlib.sha256).digest(), "big"
        )
        if candidate < cutoff:
            return candidate % bound
        counter += 1


def _shuffle(values: list[Any], server_seed: str, client_seed: str, nonce: int) -> None:
    for index in range(len(values) - 1, 0, -1):
        other = _bounded_int(server_seed, client_seed, nonce, "shuffle", index, index + 1)
        values[index], values[other] = values[other], values[index]


def _reel_stops(server_seed: str, client_seed: str, lengths: list[int]) -> list[int]:
    stops = []
    space = 1 << 256
    key = server_seed.encode("utf-8")
    for index, length in enumerate(lengths):
        cutoff = space - space % length
        prefix = f"{client_seed}:0:{index}:".encode()
        counter = 0
        while True:
            message = prefix + str(counter).encode("ascii")
            candidate = int.from_bytes(hmac.new(key, message, hashlib.sha256).digest(), "big")
            if candidate < cutoff:
                stops.append(candidate % length)
                break
            counter += 1
    return stops
