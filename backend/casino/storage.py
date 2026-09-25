from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from casino.models import Player


class PlayerRepository:
    """SQLite persistence; each profile update, ledger entry, and request key commits together."""

    def __init__(self, path: Path | None = None) -> None:
        configured = os.environ.get("NOIR_CASINO_SAVE_PATH")
        if path is not None:
            self.path = path
            self.legacy_path = None
        elif configured:
            configured_path = Path(configured)
            self.path = configured_path.with_suffix(".sqlite3") if configured_path.suffix.lower() == ".json" else configured_path
            self.legacy_path = configured_path if configured_path.suffix.lower() == ".json" else None
        else:
            directory = Path.home() / ".noir-casino"
            self.path = directory / "casino.sqlite3"
            self.legacy_path = directory / "player.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        db = self._connect()
        try:
            yield db
        finally:
            db.close()

    def _initialize(self) -> None:
        with self._connection() as db:
            db.executescript("""
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    name TEXT NOT NULL,
                    balance INTEGER NOT NULL CHECK (balance >= 0),
                    rounds_json TEXT NOT NULL,
                    blackjack_json TEXT
                );
                CREATE TABLE IF NOT EXISTS ledger (
                    id INTEGER PRIMARY KEY,
                    request_key TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    delta INTEGER NOT NULL,
                    balance_after INTEGER NOT NULL CHECK (balance_after >= 0),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS processed_requests (
                    request_key TEXT PRIMARY KEY,
                    response_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """)
            exists = db.execute("SELECT 1 FROM profile WHERE id=1").fetchone()
            migrated = db.execute("SELECT value FROM metadata WHERE key='legacy_imported'").fetchone()
            if not exists and not migrated:
                player = Player()
                blackjack = None
                if self.legacy_path and self.legacy_path.exists():
                    try:
                        old = json.loads(self.legacy_path.read_text(encoding="utf-8"))
                        if not isinstance(old, dict) or int(old.get("balance", 2500)) < 0:
                            raise ValueError("старый профиль должен быть объектом с неотрицательным балансом")
                        if "rounds" in old and not isinstance(old["rounds"], list):
                            raise ValueError("история старого профиля должна быть списком")
                        player = Player.from_dict(old)
                        blackjack = old.get("blackjack")
                        if blackjack is not None:
                            # Validate persisted card state before accepting it.
                            from casino.games import Blackjack
                            Blackjack().restore_state(blackjack)
                    except (OSError, json.JSONDecodeError, ValueError, TypeError, KeyError, AttributeError) as error:
                        raise RuntimeError(f"Не удалось безопасно импортировать старый профиль {self.legacy_path}: {error}") from error
                db.execute("BEGIN IMMEDIATE")
                try:
                    self._write_profile(db, player, blackjack)
                    db.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES('legacy_imported','1')")
                    db.commit()
                except Exception:
                    db.rollback()
                    raise

    @staticmethod
    def _write_profile(db: sqlite3.Connection, player: Player, blackjack: dict | None) -> None:
        db.execute("""INSERT INTO profile(id,name,balance,rounds_json,blackjack_json) VALUES(1,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET name=excluded.name,balance=excluded.balance,
            rounds_json=excluded.rounds_json,blackjack_json=excluded.blackjack_json""",
                   (player.name, player.balance, json.dumps([r.to_dict() for r in player.rounds[-100:]], ensure_ascii=False),
                    json.dumps(blackjack, ensure_ascii=False) if blackjack is not None else None))

    def load(self) -> Player:
        with self._connection() as db:
            row = db.execute("SELECT name,balance,rounds_json FROM profile WHERE id=1").fetchone()
        if row is None:
            raise RuntimeError("Casino profile is missing")
        rounds = json.loads(row["rounds_json"])
        return Player.from_dict({"name": row["name"], "balance": row["balance"], "rounds": rounds})

    def load_blackjack(self) -> dict | None:
        with self._connection() as db:
            row = db.execute("SELECT blackjack_json FROM profile WHERE id=1").fetchone()
        return json.loads(row["blackjack_json"]) if row and row["blackjack_json"] else None

    def get_request_response(self, request_key: str) -> dict | None:
        with self._connection() as db:
            row = db.execute("SELECT response_json FROM processed_requests WHERE request_key=?", (request_key,)).fetchone()
        return json.loads(row["response_json"]) if row is not None else None

    def save(self, player: Player, blackjack: dict | None = None, *, request_key: str | None = None,
             ledger_entries: list[tuple[str, int]] | None = None, response: dict | None = None) -> dict:
        """Atomically persist aggregate, immutable ledger movement, and idempotent response."""
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                if request_key and db.execute("SELECT 1 FROM processed_requests WHERE request_key=?", (request_key,)).fetchone():
                    db.rollback()
                    raise ValueError("Этот запрос уже обработан")
                self._write_profile(db, player, blackjack)
                if request_key:
                    db.execute("INSERT INTO processed_requests(request_key,response_json) VALUES(?,?)",
                               (request_key, json.dumps(response or {}, ensure_ascii=False)))
                    entries = ledger_entries or []
                    balance_after = player.balance - sum(delta for _, delta in entries)
                    for entry_type, delta in entries:
                        balance_after += delta
                        db.execute("INSERT INTO ledger(request_key,entry_type,delta,balance_after) VALUES(?,?,?,?)",
                                   (request_key, entry_type, delta, balance_after))
                db.commit()
            except Exception:
                if db.in_transaction:
                    db.rollback()
                raise
        return response or {}
