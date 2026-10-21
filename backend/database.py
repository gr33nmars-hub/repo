"""
Модуль персистентности и управления транзакциями SQLite.

Ключевые свойства:
1. Режим WAL (Write-Ahead Logging) для безопасного параллельного чтения/записи.
2. Проверка ограничений (CHECK constraints) на уровне схемы БД: баланс >= 0.
3. Атомарное списание средств: UPDATE ... WHERE id = 1 AND balance >= ?
4. Управление активной игровой сессией и историей с Provably Fair метаданными.
"""

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

DB_DIR = os.path.join(os.path.expanduser("~"), ".noir-casino")
DB_PATH = os.path.join(DB_DIR, "casino.sqlite3")

_db_lock = threading.Lock()
_is_initialized = False

def get_connection() -> sqlite3.Connection:
    """Возвращает соединение с SQLite с включенным режимом WAL и блокировками."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(force: bool = False):
    """Инициализация схемы базы данных. Выполняется один раз при старте приложения."""
    global _is_initialized
    with _db_lock:
        if _is_initialized and not force:
            return

        with get_connection() as conn:
            # Таблица профиля игрока со строгим CHECK-ограничением на неотрицательный баланс
            conn.execute("""
                CREATE TABLE IF NOT EXISTS player (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    balance INTEGER NOT NULL CHECK (balance >= 0),
                    rounds_played INTEGER NOT NULL DEFAULT 0,
                    wins INTEGER NOT NULL DEFAULT 0,
                    losses INTEGER NOT NULL DEFAULT 0,
                    total_wagered INTEGER NOT NULL DEFAULT 0,
                    client_seed TEXT NOT NULL DEFAULT 'student_seed_miem',
                    nonce INTEGER NOT NULL DEFAULT 0,
                    current_server_seed TEXT NOT NULL,
                    current_server_seed_hash TEXT NOT NULL
                )
            """)

            # Таблица аудита и истории раундов
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL,
                    game_name TEXT NOT NULL,
                    message TEXT NOT NULL,
                    bet INTEGER NOT NULL CHECK (bet > 0),
                    payout INTEGER NOT NULL CHECK (payout >= 0),
                    profit INTEGER NOT NULL,
                    details TEXT NOT NULL,
                    symbols_json TEXT,
                    reel_stops_json TEXT,
                    outcome_json TEXT,
                    fairness_json TEXT,
                    played_at TEXT NOT NULL
                )
            """)

            # Таблица активного состояния партии блэкджека
            conn.execute("""
                CREATE TABLE IF NOT EXISTS active_blackjack (
                    id INTEGER PRIMARY KEY,
                    state_json TEXT NOT NULL
                )
            """)

            cur = conn.execute("SELECT COUNT(*) FROM player WHERE id = 1")
            if cur.fetchone()[0] == 0:
                from games.provably_fair import ProvablyFairEngine
                initial_seed = ProvablyFairEngine.generate_server_seed()
                initial_hash = ProvablyFairEngine.hash_seed(initial_seed)

                conn.execute("""
                    INSERT INTO player (
                        id, name, balance, rounds_played, wins, losses, total_wagered,
                        client_seed, nonce, current_server_seed, current_server_seed_hash
                    )
                    VALUES (1, 'Player', 1000, 0, 0, 0, 0, 'noir_client_seed', 0, ?, ?)
                """, (initial_seed, initial_hash))

            conn.commit()
            _is_initialized = True

def get_player() -> Dict[str, Any]:
    """Возвращает агрегированную статистику профиля игрока."""
    with _db_lock:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM player WHERE id = 1").fetchone()
            if not row:
                raise RuntimeError("Профиль игрока не найден")
            total = row["rounds_played"]
            wins = row["wins"]
            win_rate = round(wins / total * 100) if total > 0 else 0
            return {
                "name": row["name"],
                "balance": row["balance"],
                "rounds_played": total,
                "wins": wins,
                "losses": row["losses"],
                "win_rate": win_rate,
                "total_wagered": row["total_wagered"],
                "client_seed": row["client_seed"],
                "nonce": row["nonce"],
                "current_server_seed_hash": row["current_server_seed_hash"]
            }

def get_provably_fair_context() -> Dict[str, Any]:
    """Возвращает текущие криптографические сиды для генерации раунда и инкрементирует nonce."""
    with _db_lock:
        with get_connection() as conn:
            row = conn.execute("SELECT current_server_seed, client_seed, nonce FROM player WHERE id = 1").fetchone()
            server_seed = row["current_server_seed"]
            client_seed = row["client_seed"]
            current_nonce = row["nonce"] + 1

            conn.execute("UPDATE player SET nonce = ? WHERE id = 1", (current_nonce,))
            conn.commit()

            return {
                "server_seed": server_seed,
                "client_seed": client_seed,
                "nonce": current_nonce
            }

def rotate_server_seed() -> Dict[str, str]:
    """Ротация серверного сида. Раскрывает старый сид игроку для независимой проверки."""
    from games.provably_fair import ProvablyFairEngine
    with _db_lock:
        with get_connection() as conn:
            row = conn.execute("SELECT current_server_seed FROM player WHERE id = 1").fetchone()
            old_seed = row["current_server_seed"]
            new_seed = ProvablyFairEngine.generate_server_seed()
            new_hash = ProvablyFairEngine.hash_seed(new_seed)

            conn.execute("""
                UPDATE player 
                SET current_server_seed = ?, current_server_seed_hash = ?, nonce = 0 
                WHERE id = 1
            """, (new_seed, new_hash))
            conn.commit()

            return {
                "revealed_previous_seed": old_seed,
                "new_server_seed_hash": new_hash
            }

def deduct_balance(amount: int):
    """Атомарное списание баланса с защитой от двойного списания и гонок (Race Condition)."""
    if amount <= 0:
        raise ValueError("Сумма списания должна быть строго положительной")

    with _db_lock:
        with get_connection() as conn:
            cur = conn.execute(
                "UPDATE player SET balance = balance - ? WHERE id = 1 AND balance >= ?",
                (amount, amount)
            )
            if cur.rowcount == 0:
                raise ValueError("Недостаточно фишек на балансе для совершения операции")
            conn.commit()

def complete_round(
    game_id: str,
    game_name: str,
    message: str,
    bet: int,
    payout: int,
    details: str,
    symbols=None,
    reel_stops=None,
    outcome=None,
    fairness=None,
    already_deducted: bool = False
) -> Dict[str, Any]:
    """Атомарная фиксация исхода раунда в таблице истории и пересчет баланса."""
    profit = payout - bet
    is_win = profit > 0
    is_loss = profit < 0
    balance_change = payout if already_deducted else (payout - bet)
    now = datetime.now(timezone.utc).isoformat()

    with _db_lock:
        with get_connection() as conn:
            conn.execute("""
                UPDATE player
                SET balance = balance + ?,
                    rounds_played = rounds_played + 1,
                    wins = wins + ?,
                    losses = losses + ?,
                    total_wagered = total_wagered + ?
                WHERE id = 1
            """, (balance_change, 1 if is_win else 0, 1 if is_loss else 0, bet))

            conn.execute("""
                INSERT INTO history (
                    game_id, game_name, message, bet, payout, profit, details,
                    symbols_json, reel_stops_json, outcome_json, fairness_json, played_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game_id, game_name, message, bet, payout, profit, details,
                json.dumps(symbols) if symbols else None,
                json.dumps(reel_stops) if reel_stops else None,
                json.dumps(outcome) if outcome else None,
                json.dumps(fairness) if fairness else None,
                now
            ))
            conn.commit()

    return {
        "game_id": game_id,
        "game_name": game_name,
        "message": message,
        "bet": bet,
        "payout": payout,
        "profit": profit,
        "details": details,
        "symbols": symbols,
        "reel_stops": reel_stops,
        "outcome": outcome,
        "fairness": fairness,
        "played_at": now
    }

def refill_player() -> int:
    """Пополнение баланса (виртуальный кран фишек при банкротстве)."""
    with _db_lock:
        with get_connection() as conn:
            conn.execute("UPDATE player SET balance = balance + 1000 WHERE id = 1")
            conn.commit()
            row = conn.execute("SELECT balance FROM player WHERE id = 1").fetchone()
            return row["balance"]

def get_history(limit: int = 15) -> List[Dict[str, Any]]:
    """Возвращает историю последних завершенных раундов."""
    with _db_lock:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM history ORDER BY id DESC LIMIT ?
            """, (limit,)).fetchall()
            result = []
            for r in rows:
                result.append({
                    "id": r["id"],
                    "game_id": r["game_id"],
                    "game_name": r["game_name"],
                    "message": r["message"],
                    "bet": r["bet"],
                    "payout": r["payout"],
                    "profit": r["profit"],
                    "details": r["details"],
                    "symbols": json.loads(r["symbols_json"]) if r["symbols_json"] else None,
                    "reel_stops": json.loads(r["reel_stops_json"]) if r["reel_stops_json"] else None,
                    "outcome": json.loads(r["outcome_json"]) if r["outcome_json"] else None,
                    "fairness": json.loads(r["fairness_json"]) if r["fairness_json"] else None,
                    "played_at": r["played_at"]
                })
            return result

def save_blackjack_state(state: Optional[Dict[str, Any]]):
    """Сохранение промежуточного состояния партии в блэкджек (FSM)."""
    with _db_lock:
        with get_connection() as conn:
            if state is None:
                conn.execute("DELETE FROM active_blackjack WHERE id = 1")
            else:
                conn.execute("""
                    INSERT INTO active_blackjack (id, state_json) VALUES (1, ?)
                    ON CONFLICT(id) DO UPDATE SET state_json = excluded.state_json
                """, (json.dumps(state),))
            conn.commit()

def load_blackjack_state() -> Optional[Dict[str, Any]]:
    """Чтение активной партии блэкджека."""
    with _db_lock:
        with get_connection() as conn:
            row = conn.execute("SELECT state_json FROM active_blackjack WHERE id = 1").fetchone()
            return json.loads(row["state_json"]) if row else None
