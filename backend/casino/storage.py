from __future__ import annotations

import json
import os
import secrets
import shutil
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from casino.errors import IdempotencyConflict
from casino.models import Player


def configured_save_paths(configured: str | None = None) -> tuple[Path, Path | None]:
    """Return the active SQLite path and any legacy JSON source for this process."""
    configured = os.environ.get("NOIR_CASINO_SAVE_PATH") if configured is None else configured
    if configured:
        configured_path = Path(configured)
        database_path = (
            configured_path.with_suffix(".sqlite3")
            if configured_path.suffix.lower() == ".json"
            else configured_path
        )
        legacy_path = configured_path if configured_path.suffix.lower() == ".json" else None
        return database_path, legacy_path
    directory = Path.home() / ".noir-casino"
    return directory / "casino.sqlite3", directory / "player.json"


class PlayerRepository:
    """SQLite persistence; each profile update, ledger entry, and request key commits together."""

    SCHEMA_VERSION = 3

    def __init__(self, path: Path | None = None) -> None:
        if path is not None:
            self.path = path
            self.legacy_path = None
        else:
            self.path, self.legacy_path = configured_save_paths()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def backup_to(self, destination: Path) -> Path:
        """Create a transactionally consistent SQLite backup at destination."""
        destination = destination.resolve()
        if destination == self.path.resolve():
            raise ValueError("Backup destination must differ from the active database")
        if destination.exists():
            raise FileExistsError(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        os.close(fd)
        temporary = Path(temporary_name)
        try:
            with self._connection() as source, sqlite3.connect(temporary) as target:
                source.backup(target)
                check = target.execute("PRAGMA quick_check").fetchone()
                if check is None or check[0] != "ok":
                    raise RuntimeError("SQLite backup failed its integrity check")
            os.replace(temporary, destination)
            return destination
        finally:
            for file_suffix in ("", "-wal", "-shm"):
                candidate = Path(f"{temporary}{file_suffix}")
                if candidate.exists():
                    candidate.unlink()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        db = self._connect()
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def write_transaction(self) -> Iterator[sqlite3.Connection]:
        """Serialize a complete read/decide/write operation across connections."""
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.commit()
            except Exception:
                if db.in_transaction:
                    db.rollback()
                raise

    @contextmanager
    def read_transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connection() as db:
            db.execute("BEGIN")
            try:
                yield db
                db.commit()
            except Exception:
                if db.in_transaction:
                    db.rollback()
                raise

    def _initialize(self) -> None:
        with self._connection() as db:
            db.execute("PRAGMA journal_mode = WAL")
            integrity = db.execute("PRAGMA quick_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                raise RuntimeError("SQLite integrity check failed; save was not modified")
            schema_version = db.execute("PRAGMA user_version").fetchone()[0]
            if schema_version > self.SCHEMA_VERSION:
                raise RuntimeError(
                    f"Save schema {schema_version} is newer than supported "
                    f"schema {self.SCHEMA_VERSION}"
                )
            if (
                schema_version < self.SCHEMA_VERSION
                and self.path.exists()
                and self.path.stat().st_size
            ):
                self._backup_before_migration(db)

            db.execute("BEGIN IMMEDIATE")
            try:
                # Another process may have completed the migration after our preflight backup.
                schema_version = db.execute("PRAGMA user_version").fetchone()[0]
                if schema_version > self.SCHEMA_VERSION:
                    raise RuntimeError(
                        f"Save schema {schema_version} is newer than supported "
                        f"schema {self.SCHEMA_VERSION}"
                    )
                self._migrate_schema(db, schema_version)
                self._import_legacy_profile(db)
                self._ensure_ledger_baseline(db)
                db.execute(
                    "INSERT OR IGNORE INTO metadata(key,value) VALUES('slots_server_seed',?)",
                    (secrets.token_hex(32),),
                )
                db.commit()
            except Exception:
                if db.in_transaction:
                    db.rollback()
                raise

    def _backup_before_migration(self, db: sqlite3.Connection) -> Path:
        """Keep a consistent, integrity-checked copy before changing an old database."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = self.path.with_name(
            f"{self.path.stem}.pre-migration-{timestamp}{self.path.suffix}"
        )
        suffix = 1
        while backup.exists():
            backup = self.path.with_name(
                f"{self.path.stem}.pre-migration-{timestamp}-{suffix}{self.path.suffix}"
            )
            suffix += 1
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{backup.name}.", suffix=".tmp", dir=backup.parent
        )
        os.close(fd)
        temporary = Path(temporary_name)
        temporary.unlink()
        try:
            target = sqlite3.connect(temporary)
            try:
                db.backup(target)
                check = target.execute("PRAGMA quick_check").fetchone()
                if check is None or check[0] != "ok":
                    raise RuntimeError("Pre-migration SQLite backup failed its integrity check")
            finally:
                target.close()
            os.replace(temporary, backup)
            return backup
        finally:
            for suffix in ("", "-wal", "-shm"):
                candidate = Path(f"{temporary}{suffix}")
                if candidate.exists():
                    candidate.unlink()

    @staticmethod
    def _table_columns(db: sqlite3.Connection, table: str) -> set[str]:
        return {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}

    def _migrate_schema(self, db: sqlite3.Connection, schema_version: int) -> None:
        """Apply schema upgrades in one transaction and publish the version last."""
        if schema_version < 1:
            db.execute(
                """CREATE TABLE IF NOT EXISTS profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    name TEXT NOT NULL,
                    balance INTEGER NOT NULL CHECK (balance >= 0),
                    rounds_json TEXT NOT NULL,
                    blackjack_json TEXT
                )"""
            )
            db.execute(
                """CREATE TABLE IF NOT EXISTS ledger (
                    id INTEGER PRIMARY KEY,
                    request_key TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    delta INTEGER NOT NULL,
                    balance_after INTEGER NOT NULL CHECK (balance_after >= 0),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            db.execute(
                """CREATE TABLE IF NOT EXISTS processed_requests (
                    request_key TEXT PRIMARY KEY,
                    response_json TEXT NOT NULL
                )"""
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            db.execute("PRAGMA user_version = 1")
            schema_version = 1
        if schema_version < 2:
            request_columns = self._table_columns(db, "processed_requests")
            if "signature" not in request_columns:
                db.execute("ALTER TABLE processed_requests ADD COLUMN signature TEXT")
            db.execute("PRAGMA user_version = 2")
            schema_version = 2
        if schema_version < 3:
            ledger_columns = self._table_columns(db, "ledger")
            if "round_id" not in ledger_columns:
                db.execute("ALTER TABLE ledger ADD COLUMN round_id TEXT")
            db.execute("PRAGMA user_version = 3")
            schema_version = 3
        if schema_version != self.SCHEMA_VERSION:
            raise RuntimeError(f"No migration path from save schema {schema_version}")
        # Keep these idempotent for partially reconstructed legacy databases.
        request_columns = self._table_columns(db, "processed_requests")
        if "signature" not in request_columns:
            db.execute("ALTER TABLE processed_requests ADD COLUMN signature TEXT")
        ledger_columns = self._table_columns(db, "ledger")
        if "round_id" not in ledger_columns:
            db.execute("ALTER TABLE ledger ADD COLUMN round_id TEXT")
        db.execute("PRAGMA user_version = 3")

    def _import_legacy_profile(self, db: sqlite3.Connection) -> None:
        exists = db.execute("SELECT 1 FROM profile WHERE id=1").fetchone()
        migrated = db.execute("SELECT value FROM metadata WHERE key='legacy_imported'").fetchone()
        if exists or migrated:
            return
        player = Player()
        blackjack = None
        if self.legacy_path and self.legacy_path.exists():
            try:
                self._backup_legacy_profile()
                old = json.loads(self.legacy_path.read_text(encoding="utf-8"))
                if not isinstance(old, dict):
                    raise ValueError("старый профиль должен быть объектом")
                if type(old.get("balance", 2500)) is not int or old.get("balance", 2500) < 0:
                    raise ValueError("баланс старого профиля должен быть неотрицательным целым")
                if "rounds" in old and not isinstance(old["rounds"], list):
                    raise ValueError("история старого профиля должна быть списком")
                player = Player.from_dict(old)
                blackjack = old.get("blackjack")
                if blackjack is not None:
                    # Validate persisted card state before accepting it.
                    from casino.blackjack import Blackjack

                    Blackjack().restore_state(blackjack)
            except (
                OSError,
                json.JSONDecodeError,
                ValueError,
                TypeError,
                KeyError,
                AttributeError,
            ) as error:
                raise RuntimeError(
                    f"Не удалось безопасно импортировать старый профиль {self.legacy_path}: {error}"
                ) from error
        self._write_profile(db, player, blackjack)
        db.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES('legacy_imported','1')")

    def _backup_legacy_profile(self) -> Path:
        if self.legacy_path is None:
            raise RuntimeError("Legacy profile path is not configured")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = self.legacy_path.with_name(
            f"{self.legacy_path.stem}.pre-migration-{timestamp}{self.legacy_path.suffix}"
        )
        suffix = 1
        while backup.exists():
            backup = self.legacy_path.with_name(
                f"{self.legacy_path.stem}.pre-migration-{timestamp}-{suffix}"
                f"{self.legacy_path.suffix}"
            )
            suffix += 1
        shutil.copy2(self.legacy_path, backup)
        return backup

    @staticmethod
    def _ensure_ledger_baseline(db: sqlite3.Connection) -> None:
        owns_transaction = not db.in_transaction
        if owns_transaction:
            db.execute("BEGIN IMMEDIATE")
        try:
            if db.execute("SELECT 1 FROM metadata WHERE key='ledger_baseline_v1'").fetchone():
                PlayerRepository._validate_ledger(db)
                if owns_transaction:
                    db.commit()
                return
            rows = db.execute("SELECT delta,balance_after FROM ledger ORDER BY id").fetchall()
            profile = db.execute("SELECT balance FROM profile WHERE id=1").fetchone()
            if profile is None:
                raise RuntimeError("Casino profile is missing")
            opening_balance = (
                rows[0]["balance_after"] - rows[0]["delta"] if rows else profile["balance"]
            )
            if opening_balance < 0:
                raise RuntimeError("Ledger starts from a negative balance")
            db.execute(
                "INSERT INTO ledger(id,request_key,entry_type,delta,balance_after) "
                "VALUES(0,'system:opening','opening_balance',?,?)",
                (opening_balance, opening_balance),
            )
            PlayerRepository._validate_ledger(db)
            db.execute("INSERT INTO metadata(key,value) VALUES('ledger_baseline_v1','1')")
            if owns_transaction:
                db.commit()
        except Exception:
            if owns_transaction and db.in_transaction:
                db.rollback()
            raise

    @staticmethod
    def _validate_ledger(db: sqlite3.Connection) -> None:
        balance = 0
        for row in db.execute("SELECT delta,balance_after FROM ledger ORDER BY id"):
            balance += row["delta"]
            if balance < 0 or balance != row["balance_after"]:
                raise RuntimeError("Ledger balance chain is inconsistent; profile was not modified")
        profile = db.execute("SELECT balance FROM profile WHERE id=1").fetchone()
        if profile is None or balance != profile["balance"]:
            raise RuntimeError("Ledger total does not match the saved profile balance")

    @staticmethod
    def _write_profile(db: sqlite3.Connection, player: Player, blackjack: dict | None) -> None:
        db.execute(
            """INSERT INTO profile(id,name,balance,rounds_json,blackjack_json) VALUES(1,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET name=excluded.name,balance=excluded.balance,
            rounds_json=excluded.rounds_json,blackjack_json=excluded.blackjack_json""",
            (
                player.name,
                player.balance,
                json.dumps([r.to_dict() for r in player.rounds], ensure_ascii=False),
                json.dumps(blackjack, ensure_ascii=False) if blackjack is not None else None,
            ),
        )

    @staticmethod
    def revision(db: sqlite3.Connection) -> int:
        row = db.execute("SELECT value FROM metadata WHERE key='profile_revision'").fetchone()
        return int(row["value"]) if row else 0

    @staticmethod
    def load_slot_seed(db: sqlite3.Connection) -> str:
        row = db.execute("SELECT value FROM metadata WHERE key='slots_server_seed'").fetchone()
        if (
            row is None
            or len(row["value"]) != 64
            or any(character not in "0123456789abcdef" for character in row["value"])
        ):
            raise RuntimeError("Slot seed commitment is missing or invalid")
        return row["value"]

    @staticmethod
    def set_slot_seed(db: sqlite3.Connection, seed: str) -> None:
        db.execute("UPDATE metadata SET value=? WHERE key='slots_server_seed'", (seed,))

    def load(self, db: sqlite3.Connection | None = None) -> Player:
        if db is None:
            with self._connection() as connection:
                return self.load(connection)
        row = db.execute("SELECT name,balance,rounds_json FROM profile WHERE id=1").fetchone()
        if row is None:
            raise RuntimeError("Casino profile is missing")
        rounds = json.loads(row["rounds_json"])
        return Player.from_dict({"name": row["name"], "balance": row["balance"], "rounds": rounds})

    def load_blackjack(self, db: sqlite3.Connection | None = None) -> dict | None:
        if db is None:
            with self._connection() as connection:
                return self.load_blackjack(connection)
        row = db.execute("SELECT blackjack_json FROM profile WHERE id=1").fetchone()
        return json.loads(row["blackjack_json"]) if row and row["blackjack_json"] else None

    @staticmethod
    def validate_active_blackjack_round(
        db: sqlite3.Connection, round_id: str | None, initial_bet: int, total_stake: int
    ) -> None:
        """Check that an active round's saved wagers match its durable stake entries."""
        if round_id is None:  # Legacy snapshots predate round-to-ledger links.
            return
        rows = db.execute(
            "SELECT entry_type,delta FROM ledger WHERE round_id=?",
            (round_id,),
        ).fetchall()
        stake_rows = [row for row in rows if row["entry_type"].endswith("stake")]
        known_stakes = {
            "blackjack_stake",
            "blackjack_double_stake",
            "blackjack_split_stake",
            "blackjack_insurance_stake",
        }
        if (
            sum(-row["delta"] for row in stake_rows) != total_stake
            or sum(row["entry_type"] == "blackjack_stake" for row in stake_rows) != 1
            or not any(
                row["entry_type"] == "blackjack_stake" and row["delta"] == -initial_bet
                for row in stake_rows
            )
            or any(row["entry_type"] not in known_stakes or row["delta"] >= 0 for row in stake_rows)
            or any(row["delta"] < 0 and row not in stake_rows for row in rows)
        ):
            raise RuntimeError("Active blackjack wagers do not match the durable ledger")

    def get_request_response(
        self,
        request_key: str,
        *,
        signature: str | None = None,
        db: sqlite3.Connection | None = None,
    ) -> dict | None:
        if db is None:
            with self.write_transaction() as connection:
                return self.get_request_response(request_key, signature=signature, db=connection)
        row = db.execute(
            "SELECT response_json,signature FROM processed_requests WHERE request_key=?",
            (request_key,),
        ).fetchone()
        if row is None:
            return None
        if row["signature"] is None and signature is not None:
            raise IdempotencyConflict(
                "Ключ из старой версии уже обработан, но исходную операцию нельзя определить"
            )
        elif row["signature"] != signature:
            raise IdempotencyConflict("Этот ключ запроса уже использован для другой операции")
        return json.loads(row["response_json"])

    def save(
        self,
        player: Player,
        blackjack: dict | None = None,
        *,
        request_key: str,
        signature: str,
        ledger_entries: list[tuple[str, int]],
        response: dict,
        round_id: str | None = None,
        db: sqlite3.Connection | None = None,
    ) -> dict:
        """Atomically persist aggregate, immutable ledger movement, and idempotent response."""
        if type(request_key) is not str or not 1 <= len(request_key) <= 128:
            raise ValueError("A bounded idempotency key is required for every profile write")
        if type(signature) is not str or not signature:
            raise ValueError("A request signature is required for every profile write")
        if type(ledger_entries) is not list or any(
            type(entry) is not tuple
            or len(entry) != 2
            or type(entry[0]) is not str
            or not entry[0]
            or type(entry[1]) is not int
            for entry in ledger_entries
        ):
            raise ValueError(
                "Explicit integer ledger movements are required for every profile write"
            )
        if type(response) is not dict:
            raise ValueError("A cached response object is required for every profile write")
        if db is None:
            with self.write_transaction() as connection:
                return self.save(
                    player,
                    blackjack,
                    request_key=request_key,
                    signature=signature,
                    ledger_entries=ledger_entries,
                    response=response,
                    round_id=round_id,
                    db=connection,
                )
        if not db.in_transaction:
            raise RuntimeError("Repository writes require an active SQLite transaction")
        if db.execute(
            "SELECT 1 FROM processed_requests WHERE request_key=?", (request_key,)
        ).fetchone():
            raise IdempotencyConflict("Этот запрос уже обработан")
        old_profile = db.execute("SELECT balance FROM profile WHERE id=1").fetchone()
        old_balance = old_profile["balance"] if old_profile else 0
        entries = list(ledger_entries)
        if old_balance + sum(delta for _, delta in entries) != player.balance:
            raise ValueError("Ledger movements must equal the profile balance change")
        self._write_profile(db, player, blackjack)
        db.execute(
            "INSERT INTO processed_requests(request_key,response_json,signature) VALUES(?,?,?)",
            (request_key, json.dumps(response, ensure_ascii=False), signature),
        )
        balance_after = old_balance
        for entry_type, delta in entries:
            balance_after += delta
            db.execute(
                "INSERT INTO ledger(request_key,round_id,entry_type,delta,balance_after) "
                "VALUES(?,?,?,?,?)",
                (request_key, round_id, entry_type, delta, balance_after),
            )
        if balance_after != player.balance:
            raise ValueError("Ledger movements must equal the profile balance change")
        self._validate_ledger(db)
        next_revision = self.revision(db) + 1
        db.execute(
            "INSERT INTO metadata(key,value) VALUES('profile_revision',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(next_revision),),
        )
        return response
