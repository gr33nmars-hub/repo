"""JSON codecs for persisted casino profiles and idempotent responses."""

from __future__ import annotations

import json
from dataclasses import asdict

from casino.domain.blackjack import BlackjackSnapshot
from casino.domain.models import GameResult, Player
from casino.persistence.blackjack_codec import BlackjackStateCodec


class CasinoSaveCodec:
    """Translate persisted JSON columns without performing SQLite operations."""

    @staticmethod
    def encode_history(rounds: list[GameResult]) -> str:
        return json.dumps(
            [CasinoSaveCodec.encode_result(round_) for round_ in rounds], ensure_ascii=False
        )

    @staticmethod
    def encode_result(round_: GameResult) -> dict:
        result = asdict(round_)
        result["profit"] = round_.profit
        for key in ("symbols", "reel_stops", "fairness", "round_id"):
            if result[key] is None:
                del result[key]
        if round_.rule_version is None:
            for key in ("rule_version", "rules_fingerprint", "rules_snapshot", "outcome"):
                del result[key]
        return result

    @staticmethod
    def decode_history(value: str) -> list[dict]:
        decoded = json.loads(value)
        if not isinstance(decoded, list) or any(not isinstance(item, dict) for item in decoded):
            raise ValueError("Saved round history must be a list of objects")
        return decoded

    @staticmethod
    def decode_result(data: dict) -> GameResult:
        if not isinstance(data, dict):
            raise ValueError("Данные результата игры должны быть объектом-словарем")
        required_text = ("game_id", "game_name", "message")
        if any(type(data.get(key)) is not str for key in required_text):
            raise ValueError("В результате игры отсутствуют обязательные текстовые поля")
        if type(data.get("bet")) is not int or type(data.get("payout")) is not int:
            raise ValueError("Ставка и выплата (bet and payout) должны быть целыми числами")
        if "details" in data and type(data["details"]) is not str:
            raise ValueError("Детали раунда должны быть строкой")
        if "played_at" in data and type(data["played_at"]) is not str:
            raise ValueError("Временная метка раунда должна быть строкой")
        if data.get("symbols") is not None and (
            type(data["symbols"]) is not list
            or any(type(symbol) is not str for symbol in data["symbols"])
        ):
            raise ValueError("Символы результата игры должны быть списком строк")
        if data.get("reel_stops") is not None and (
            type(data["reel_stops"]) is not list
            or any(type(stop) is not int or stop < 0 for stop in data["reel_stops"])
        ):
            raise ValueError(
                "Остановки барабанов слота должны быть неотрицательными целыми числами"
            )
        if data.get("fairness") is not None and type(data["fairness"]) is not dict:
            raise ValueError("Подтверждение честности раунда должно быть объектом")
        for key in ("rule_version", "rules_fingerprint"):
            if key in data and data[key] is not None and type(data[key]) is not str:
                raise ValueError(f"Параметр {key} результата игры должен быть строкой")
        if (
            "round_id" in data
            and data["round_id"] is not None
            and type(data["round_id"]) is not str
        ):
            raise ValueError("Идентификатор раунда round_id должен быть строкой")
        for key in ("rules_snapshot", "outcome"):
            if key in data and data[key] is not None and type(data[key]) is not dict:
                raise ValueError(f"Параметр {key} результата игры должен быть объектом")
        return GameResult(
            game_id=data["game_id"],
            game_name=data["game_name"],
            message=data["message"],
            bet=data["bet"],
            payout=data["payout"],
            details=data.get("details", ""),
            symbols=data.get("symbols"),
            reel_stops=data.get("reel_stops"),
            fairness=data.get("fairness"),
            played_at=data.get("played_at", ""),
            round_id=data.get("round_id"),
            rule_version=data.get("rule_version"),
            rules_fingerprint=data.get("rules_fingerprint"),
            rules_snapshot=data.get("rules_snapshot"),
            outcome=data.get("outcome"),
        )

    @staticmethod
    def decode_player(data: dict) -> Player:
        if not isinstance(data, dict):
            raise ValueError("Профиль игрока должен быть объектом")
        name = data.get("name", "Гость")
        balance = data.get("balance", 2500)
        rounds = data.get("rounds", [])
        if type(name) is not str or not name:
            raise ValueError("Имя игрока должно быть непустой строкой")
        if type(balance) is not int or balance < 0:
            raise ValueError("Баланс игрока (balance) должен быть неотрицательным целым числом")
        if type(rounds) is not list:
            raise ValueError("История раундов игрока (history) должна быть списком")
        return Player(
            name=name,
            balance=balance,
            rounds=[CasinoSaveCodec.decode_result(item) for item in rounds],
        )

    @staticmethod
    def encode_blackjack(snapshot: BlackjackSnapshot | None) -> str | None:
        state = BlackjackStateCodec.encode(snapshot)
        return json.dumps(state, ensure_ascii=False) if state is not None else None

    @staticmethod
    def decode_blackjack(value: str | None) -> BlackjackSnapshot | None:
        if not value:
            return None
        decoded = json.loads(value)
        if not isinstance(decoded, dict):
            raise ValueError("Saved blackjack state must be an object")
        return BlackjackStateCodec.decode(decoded)

    @staticmethod
    def encode_object(value: dict) -> str:
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def decode_object(value: str) -> dict:
        decoded = json.loads(value)
        if not isinstance(decoded, dict):
            raise ValueError("Saved response must be an object")
        return decoded
