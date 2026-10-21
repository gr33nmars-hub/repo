"""
Объектно-ориентированная модель и правила классических слотов 3x3.
Учебный проект МИЭМ НИУ ВШЭ.

Архитектура:
- SlotSymbol / SlotPaytable: доменные сущности и выплатная таблица
- SlotEngine: генератор исходов на основе HMAC-SHA256 (Provably Fair)
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
from games.provably_fair import ProvablyFairEngine

@dataclass(frozen=True)
class SlotConfig:
    id: str = "slots"
    name: str = "Слоты"
    minimum_bet: int = 10
    maximum_bet: int = 1000
    pair_multiplier: int = 1
    theoretical_rtp: float = 95.8

class SlotGame:
    """
    Класс игры в слоты. Реализует инкапсуляцию правил вращения барабанов,
    расчета комбинаций и детерминированной генерации через Provably Fair.
    """
    REELS: List[List[str]] = [
        ["🍒", "🍋", "🔔", "🍒", "💎", "🍒", "🍋", "7️⃣"],
        ["🍋", "🍒", "💎", "🍋", "🍒", "🔔", "7️⃣", "🍒"],
        ["🍒", "🔔", "🍋", "🍒", "7️⃣", "🍋", "🍒", "💎"]
    ]

    TRIPLES: Dict[str, int] = {
        "7️⃣": 24,
        "💎": 12,
        "🔔": 8,
        "🍒": 4,
        "🍋": 4
    }

    PAIR_MULTIPLIER: int = 1

    def __init__(self, config: SlotConfig = SlotConfig()):
        self.config = config

    def get_info(self) -> dict:
        """Возвращает метаданные игры для отображения в лобби и интерфейсе."""
        return {
            "id": self.config.id,
            "name": self.config.name,
            "minimum_bet": self.config.minimum_bet,
            "maximum_bet": self.config.maximum_bet,
            "paytable": [{"symbol": sym, "multiplier": mul} for sym, mul in self.TRIPLES.items()],
            "pair_multiplier": self.PAIR_MULTIPLIER,
            "theoretical_return_percent": self.config.theoretical_rtp,
            "reel_strips": self.REELS
        }

    def spin(self, bet: int, server_seed: str, client_seed: str, nonce: int) -> dict:
        """
        Проводит спин барабанов с гарантией доказательной честности.
        Определяет остановки барабанов по детерминированному HMAC срезу.
        """
        if bet < self.config.minimum_bet or bet > self.config.maximum_bet:
            raise ValueError(f"Ставка должна быть от {self.config.minimum_bet} до {self.config.maximum_bet}")

        stops = []
        for i, reel in enumerate(self.REELS):
            stop = ProvablyFairEngine.get_int(server_seed, client_seed, nonce, 0, len(reel) - 1, offset=i * 4)
            stops.append(stop)

        symbols = [self.REELS[i][stops[i]] for i in range(3)]

        if symbols[0] == symbols[1] == symbols[2]:
            multiplier = self.TRIPLES.get(symbols[0], 4)
            payout = bet * multiplier
            message = f"Тройка {symbols[0]}"
        elif symbols[0] == symbols[1] or symbols[1] == symbols[2] or symbols[0] == symbols[2]:
            payout = bet * self.PAIR_MULTIPLIER
            message = "Пара символов"
        else:
            payout = 0
            message = "Попробуй ещё раз"

        details = " · ".join(symbols)
        outcome = {
            "symbols": symbols,
            "reel_stops": stops
        }

        return {
            "game_id": self.config.id,
            "game_name": self.config.name,
            "message": message,
            "bet": bet,
            "payout": payout,
            "profit": payout - bet,
            "details": details,
            "symbols": symbols,
            "reel_stops": stops,
            "outcome": outcome,
            "fairness": {
                "server_seed": server_seed,
                "server_seed_hash": ProvablyFairEngine.hash_seed(server_seed),
                "client_seed": client_seed,
                "nonce": nonce
            }
        }

# Для обратной совместимости с существующими импортами
_slot_game_instance = SlotGame()

def get_slots_info() -> dict:
    return _slot_game_instance.get_info()

def play_slots(bet: int, server_seed: str = None, client_seed: str = "default_client", nonce: int = 1) -> dict:
    if server_seed is None:
        server_seed = ProvablyFairEngine.generate_server_seed()
    return _slot_game_instance.spin(bet, server_seed, client_seed, nonce)
