from __future__ import annotations

from dataclasses import dataclass

from .core import CasinoGame, GameRules, RandomSource
from .errors import InvalidCasinoCommand
from .models import GameResult
from .rule_metadata import fingerprint_rules


@dataclass(frozen=True, slots=True)
class SlotRules:
    reels: tuple[tuple[str, ...], ...] = (
        ("🍒", "🍋", "🔔", "🍒", "💎", "🍒", "🍋", "7️⃣"),
        ("🍋", "🍒", "💎", "🍋", "🍒", "🔔", "7️⃣", "🍒"),
        ("🍒", "🔔", "🍋", "🍒", "7️⃣", "🍋", "🍒", "💎"),
    )
    triples: tuple[tuple[str, int], ...] = (("7️⃣", 24), ("💎", 12), ("🔔", 8), ("🍒", 4), ("🍋", 4))
    pair_multiplier: int = 1

    def snapshot(self) -> dict[str, object]:
        return {
            "reels": [list(reel) for reel in self.reels],
            "triples": [
                {"symbol": symbol, "multiplier": multiplier} for symbol, multiplier in self.triples
            ],
            "pair_multiplier": self.pair_multiplier,
        }

    @property
    def theoretical_return_percent(self) -> float:
        symbols = {symbol for reel in self.reels for symbol in reel}
        probabilities = [
            {symbol: reel.count(symbol) / len(reel) for symbol in symbols} for reel in self.reels
        ]
        triple_return = sum(
            probabilities[0].get(symbol, 0)
            * probabilities[1].get(symbol, 0)
            * probabilities[2].get(symbol, 0)
            * multiplier
            for symbol, multiplier in self.triples
        )
        pair_probability = sum(
            probabilities[0].get(symbol, 0)
            * probabilities[1].get(symbol, 0)
            * (1 - probabilities[2].get(symbol, 0))
            + probabilities[0].get(symbol, 0)
            * probabilities[2].get(symbol, 0)
            * (1 - probabilities[1].get(symbol, 0))
            + probabilities[1].get(symbol, 0)
            * probabilities[2].get(symbol, 0)
            * (1 - probabilities[0].get(symbol, 0))
            for symbol in symbols
        )
        return round((triple_return + pair_probability * self.pair_multiplier) * 100, 1)

    def __post_init__(self) -> None:
        if (
            type(self.reels) is not tuple
            or len(self.reels) != 3
            or any(type(reel) is not tuple or not reel for reel in self.reels)
            or any(type(symbol) is not str or not symbol for reel in self.reels for symbol in reel)
        ):
            raise ValueError("Slots require exactly three non-empty reels")
        if (
            type(self.triples) is not tuple
            or not self.triples
            or any(
                type(entry) is not tuple
                or len(entry) != 2
                or type(entry[0]) is not str
                or not entry[0]
                or type(entry[1]) is not int
                or entry[1] < 1
                for entry in self.triples
            )
            or type(self.pair_multiplier) is not int
            or self.pair_multiplier < 0
        ):
            raise ValueError("Invalid slot paytable")
        payout_symbols = [symbol for symbol, _ in self.triples]
        if len(set(payout_symbols)) != len(payout_symbols):
            raise ValueError("Slot paytable symbols must be non-empty and unique")
        if any(
            symbol not in {entry[0] for entry in self.triples}
            for reel in self.reels
            for symbol in reel
        ):
            raise ValueError("Every slot symbol must have a configured triple payout")


class SlotMachine(CasinoGame):
    game_id, name = "slots", "Слоты"
    rule_version = "slots-v1"

    def __init__(
        self,
        rng: RandomSource | None = None,
        rules: GameRules | None = None,
        slot_rules: SlotRules | None = None,
    ):
        super().__init__(rng, rules)
        self.slot_rules = slot_rules or SlotRules()
        self._payouts = dict(self.slot_rules.triples)

    def play(self, bet: int, choice: str = "") -> GameResult:
        stops = [self._rng.choice(range(len(reel))) for reel in self.slot_rules.reels]
        return self.play_at_stops(bet, stops)

    def play_at_stops(self, bet: int, stops: list[int]) -> GameResult:
        if len(stops) != 3 or any(
            type(stop) is not int or not 0 <= stop < len(reel)
            for reel, stop in zip(self.slot_rules.reels, stops)
        ):
            raise ValueError("Invalid slot reel stops")
        result = [reel[stop] for reel, stop in zip(self.slot_rules.reels, stops)]
        details = "  ·  ".join(result)
        if result[0] == result[1] == result[2]:
            multiplier = self._payouts[result[0]]
            display_symbol = {"🍋": "🍌", "7️⃣": "777"}.get(result[0], result[0])
            payout, message = bet * multiplier, f"Тройка {display_symbol} · выплата ×{multiplier}"
        elif len(set(result)) == 2:
            payout, message = (
                bet * self.slot_rules.pair_multiplier,
                "Пара символов · ставка возвращена",
            )
        else:
            payout, message = 0, "Комбинация не собрана"
        snapshot = self.slot_rules.snapshot()
        outcome = {"symbols": result, "reel_stops": stops}
        return GameResult(
            self.game_id,
            self.name,
            message,
            bet,
            payout,
            details,
            symbols=result,
            reel_stops=stops,
            rule_version=self.rule_version,
            rules_fingerprint=fingerprint_rules(self.rule_version, snapshot),
            rules_snapshot=snapshot,
            outcome=outcome,
        )

    def catalog_info(self) -> dict[str, object]:
        return {
            **super().catalog_info(),
            "paytable": [
                {"symbol": symbol, "multiplier": multiplier}
                for symbol, multiplier in self.slot_rules.triples
            ],
            "pair_multiplier": self.slot_rules.pair_multiplier,
            "theoretical_return_percent": self.slot_rules.theoretical_return_percent,
            "reel_strips": [list(reel) for reel in self.slot_rules.reels],
        }


RED_NUMBERS = frozenset({1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36})
EUROPEAN_WHEEL = tuple(range(37))


@dataclass(frozen=True, slots=True)
class RouletteRules:
    color_return_multiplier: int = 2
    number_return_multiplier: int = 36

    def __post_init__(self) -> None:
        if (
            type(self.color_return_multiplier) is not int
            or type(self.number_return_multiplier) is not int
            or self.color_return_multiplier < 1
            or self.number_return_multiplier < 1
        ):
            raise ValueError("Roulette return multipliers must be positive")


class Roulette(CasinoGame):
    game_id, name = "roulette", "Рулетка"
    choices = frozenset({"red", "black", "zero"})
    rule_version = "roulette-v1"

    def __init__(
        self,
        rng: RandomSource | None = None,
        rules: GameRules | None = None,
        roulette_rules: RouletteRules | None = None,
    ):
        super().__init__(rng, rules)
        self.roulette_rules = roulette_rules or RouletteRules()

    def play(self, bet: int, choice: str = "red") -> GameResult:
        if choice not in self.choices:
            raise InvalidCasinoCommand("Выбери красное, чёрное или зеро")
        number = self._rng.choice(EUROPEAN_WHEEL)
        return self._result_for_number(bet, choice, number)

    def _result_for_number(self, bet: int, choice: str, number: int) -> GameResult:
        if choice not in self.choices:
            raise InvalidCasinoCommand("Выбери красное, чёрное или зеро")
        if type(number) is not int or number not in EUROPEAN_WHEEL:
            raise ValueError("Invalid roulette number")
        color = "zero" if number == 0 else "red" if number in RED_NUMBERS else "black"
        colors = {"red": "красное", "black": "чёрное", "zero": "зелёное"}
        multiplier = (
            self.roulette_rules.number_return_multiplier
            if choice == "zero"
            else self.roulette_rules.color_return_multiplier
        )
        payout = bet * multiplier if choice == color else 0
        message = "Шарик остановился на твоём секторе" if payout else "Шарик прошёл мимо"
        snapshot = {
            "wheel": list(EUROPEAN_WHEEL),
            "red_numbers": sorted(RED_NUMBERS),
            "color_return_multiplier": self.roulette_rules.color_return_multiplier,
            "number_return_multiplier": self.roulette_rules.number_return_multiplier,
        }
        outcome = {"number": number, "color": color, "choice": choice}
        return GameResult(
            self.game_id,
            self.name,
            message,
            bet,
            payout,
            f"{number} · {colors[color]}",
            rule_version=self.rule_version,
            rules_fingerprint=fingerprint_rules(self.rule_version, snapshot),
            rules_snapshot=snapshot,
            outcome=outcome,
        )

    def play_at_number(self, bet: int, choice: str, number: int) -> GameResult:
        """Build the ordinary roulette result for a committed wheel pocket."""
        return self._result_for_number(bet, choice, number)
