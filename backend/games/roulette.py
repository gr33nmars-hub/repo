"""
Объектно-ориентированная модель Европейской Рулетки (37 секторов, одно зеро).
Учебный проект МИЭМ НИУ ВШЭ.

Архитектура:
- RouletteSector / RouletteWheel: абстракция колеса и таблицы выплат
- RouletteGame: логика ставок (red, black, zero) и расчет результатов через Provably Fair
"""

from dataclasses import dataclass
from typing import Set, Dict
from games.provably_fair import ProvablyFairEngine

@dataclass(frozen=True)
class RouletteConfig:
    id: str = "roulette"
    name: str = "Рулетка"
    minimum_bet: int = 10
    maximum_bet: int = 1000

class RouletteGame:
    """
    Класс игры Европейская рулетка.
    Содержит правила выплат, валидацию ставок и детерминированную физику шарика через CSPRNG/HMAC.
    """
    RED_NUMBERS: Set[int] = {
        1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36
    }
    
    COLOR_NAMES: Dict[str, str] = {
        "red": "красное",
        "black": "чёрное",
        "zero": "зелёное"
    }

    def __init__(self, config: RouletteConfig = RouletteConfig()):
        self.config = config

    def get_info(self) -> dict:
        """Возвращает правила и лимиты для лобби."""
        return {
            "id": self.config.id,
            "name": self.config.name,
            "minimum_bet": self.config.minimum_bet,
            "maximum_bet": self.config.maximum_bet
        }

    def spin(self, bet: int, choice: str, server_seed: str, client_seed: str, nonce: int) -> dict:
        """
        Проводит спин рулетки на основе HMAC-SHA256.
        """
        if choice not in ("red", "black", "zero"):
            choice = "red"

        if bet < self.config.minimum_bet or bet > self.config.maximum_bet:
            raise ValueError(f"Ставка должна быть от {self.config.minimum_bet} до {self.config.maximum_bet}")

        # Равномерное случайное число от 0 до 36
        number = ProvablyFairEngine.get_int(server_seed, client_seed, nonce, 0, 36)

        color = "zero" if number == 0 else "red" if number in self.RED_NUMBERS else "black"
        multiplier = 36 if choice == "zero" else 2
        payout = bet * multiplier if choice == color else 0
        message = "Шарик остановился на твоём секторе" if payout > 0 else "Шарик прошёл мимо"
        details = f"{number} · {self.COLOR_NAMES[color]}"

        outcome = {
            "number": number,
            "color": color,
            "choice": choice
        }

        return {
            "game_id": self.config.id,
            "game_name": self.config.name,
            "message": message,
            "bet": bet,
            "payout": payout,
            "profit": payout - bet,
            "details": details,
            "outcome": outcome,
            "fairness": {
                "server_seed": server_seed,
                "server_seed_hash": ProvablyFairEngine.hash_seed(server_seed),
                "client_seed": client_seed,
                "nonce": nonce
            }
        }

_roulette_instance = RouletteGame()

def get_roulette_info() -> dict:
    return _roulette_instance.get_info()

def play_roulette(bet: int, choice: str = "red", server_seed: str = None, client_seed: str = "default_client", nonce: int = 1) -> dict:
    if server_seed is None:
        server_seed = ProvablyFairEngine.generate_server_seed()
    return _roulette_instance.spin(bet, choice, server_seed, client_seed, nonce)
