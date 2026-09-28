"""Versioned SQLite schema migrations for saved casino profiles."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

SCHEMA_VERSION = 4


class SQLiteSchemaMigrator:
    """Apply ordered schema upgrades inside the caller's transaction."""

    @staticmethod
    def _table_columns(db: sqlite3.Connection, table: str) -> set[str]:
        return {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}

    @classmethod
    def migrate(
        cls,
        db: sqlite3.Connection,
        schema_version: int,
        *,
        after_step: Callable[[str], None] | None = None,
    ) -> None:
        def execute(statement: str, step: str) -> None:
            db.execute(statement)
            if after_step is not None:
                after_step(step)

        if schema_version < 1:
            execute(
                """CREATE TABLE IF NOT EXISTS profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    name TEXT NOT NULL,
                    balance INTEGER NOT NULL CHECK (balance >= 0),
                    rounds_json TEXT NOT NULL,
                    blackjack_json TEXT
                )""",
                "v1.profile",
            )
            execute(
                """CREATE TABLE IF NOT EXISTS ledger (
                    id INTEGER PRIMARY KEY,
                    request_key TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    delta INTEGER NOT NULL,
                    balance_after INTEGER NOT NULL CHECK (balance_after >= 0),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )""",
                "v1.ledger",
            )
            execute(
                """CREATE TABLE IF NOT EXISTS processed_requests (
                    request_key TEXT PRIMARY KEY,
                    response_json TEXT NOT NULL
                )""",
                "v1.processed_requests",
            )
            execute(
                "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
                "v1.metadata",
            )
            execute("PRAGMA user_version = 1", "v1.user_version")
            schema_version = 1
        if schema_version < 2:
            request_columns = cls._table_columns(db, "processed_requests")
            if "signature" not in request_columns:
                execute("ALTER TABLE processed_requests ADD COLUMN signature TEXT", "v2.signature")
            execute("PRAGMA user_version = 2", "v2.user_version")
            schema_version = 2
        if schema_version < 3:
            ledger_columns = cls._table_columns(db, "ledger")
            if "round_id" not in ledger_columns:
                execute("ALTER TABLE ledger ADD COLUMN round_id TEXT", "v3.round_id")
            execute("PRAGMA user_version = 3", "v3.user_version")
            schema_version = 3
        if schema_version < 4:
            ledger_columns = cls._table_columns(db, "ledger")
            if "reason" not in ledger_columns:
                execute("ALTER TABLE ledger ADD COLUMN reason TEXT", "v4.reason")
            execute("PRAGMA user_version = 4", "v4.user_version")
            schema_version = 4
        if schema_version != SCHEMA_VERSION:
            raise RuntimeError(f"No migration path from save schema {schema_version}")
        request_columns = cls._table_columns(db, "processed_requests")
        if "signature" not in request_columns:
            execute("ALTER TABLE processed_requests ADD COLUMN signature TEXT", "final.signature")
        ledger_columns = cls._table_columns(db, "ledger")
        if "round_id" not in ledger_columns:
            execute("ALTER TABLE ledger ADD COLUMN round_id TEXT", "final.round_id")
        if "reason" not in ledger_columns:
            execute("ALTER TABLE ledger ADD COLUMN reason TEXT", "final.reason")
        execute(f"PRAGMA user_version = {SCHEMA_VERSION}", "final.user_version")
