"""Offline backup, validation, and restore commands for the local SQLite save."""

from __future__ import annotations

import argparse
import os
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from casino.application.service import CasinoService
from casino.persistence.sqlite import PlayerRepository
from casino.process_lock import BackendProcessLock


def validate_database(path: Path) -> None:
    """Проверка целостности резервной копии базы данных (профиль, леджер, блэкджек)."""
    path = path.resolve()
    with tempfile.TemporaryDirectory(prefix="astoria-casino-verify-") as directory:
        copy_path = Path(directory) / "validation.sqlite3"
        with (
            closing(sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)) as source,
            closing(sqlite3.connect(copy_path)) as target,
        ):
            source.backup(target)
            check = target.execute("PRAGMA quick_check").fetchone()
            if check is None or check[0] != "ok":
                raise RuntimeError("SQLite integrity check failed")
        repository = PlayerRepository(copy_path)
        CasinoService(repository)


def _raw_sqlite_backup(source: Path, destination: Path) -> Path:
    source, destination = source.resolve(), destination.resolve()
    if source == destination:
        raise ValueError("Backup destination must differ from the active database")
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    temporary.unlink()
    try:
        with (
            closing(sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True)) as source_db,
            closing(sqlite3.connect(temporary)) as target_db,
        ):
            source_db.backup(target_db)
            check = target_db.execute("PRAGMA quick_check").fetchone()
            if check is None or check[0] != "ok":
                raise RuntimeError("SQLite backup failed its integrity check")
        os.replace(temporary, destination)
        return destination
    finally:
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(f"{temporary}{suffix}")
            if candidate.exists():
                candidate.unlink()


def backup_database(source: Path, destination: Path) -> Path:
    backed_up = _raw_sqlite_backup(source, destination)
    validate_database(backed_up)
    return backed_up


def _prepare_restore_destination(destination: Path) -> None:
    """Checkpoint an existing destination so its WAL cannot affect the restored file."""
    sidecars = [Path(f"{destination}-wal"), Path(f"{destination}-shm")]
    if not destination.exists():
        if any(path.exists() for path in sidecars):
            raise RuntimeError("Restore destination has orphaned SQLite sidecar files")
        return

    try:
        db = sqlite3.connect(destination, timeout=10)
        try:
            db.execute("PRAGMA busy_timeout = 10000")
            checkpoint = db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            if checkpoint is not None and checkpoint[0] != 0:
                raise RuntimeError("Cannot restore while the destination WAL is busy")
            mode = db.execute("PRAGMA journal_mode = DELETE").fetchone()
            if mode is None or mode[0].lower() != "delete":
                raise RuntimeError("Cannot disable destination WAL before restore")
        finally:
            db.close()
    except sqlite3.Error as error:
        raise RuntimeError("Unable to prepare restore destination safely") from error


def restore_database(source: Path, destination: Path, *, replace: bool = False) -> Path:
    source, destination = source.resolve(), destination.resolve()
    with BackendProcessLock(destination):
        return _restore_database_locked(source, destination, replace=replace)


def _restore_database_locked(source: Path, destination: Path, *, replace: bool) -> Path:
    if source == destination:
        raise ValueError("Restore source and destination must differ")
    if destination.exists() and not replace:
        raise FileExistsError("Destination exists; pass --replace to restore over it")
    destination.parent.mkdir(parents=True, exist_ok=True)

    staged = destination.with_name(f".{destination.name}.{os.getpid()}.restore")
    if staged.exists():
        raise FileExistsError(staged)
    _raw_sqlite_backup(source, staged)
    try:
        validate_database(staged)
        if destination.exists():
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_path = destination.with_name(
                f"{destination.stem}.pre-restore-{timestamp}{destination.suffix}"
            )
            suffix = 1
            while backup_path.exists():
                backup_path = destination.with_name(
                    f"{destination.stem}.pre-restore-{timestamp}-{suffix}{destination.suffix}"
                )
                suffix += 1
            _raw_sqlite_backup(destination, backup_path)
        _prepare_restore_destination(destination)
        os.replace(staged, destination)
        return destination
    finally:
        for file_suffix in ("", "-wal", "-shm"):
            candidate = Path(f"{staged}{file_suffix}")
            if candidate.exists():
                candidate.unlink()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NOIR Casino Club save recovery")
    commands = parser.add_subparsers(dest="command", required=True)
    backup = commands.add_parser("backup", help="create and validate a SQLite backup")
    backup.add_argument("destination", type=Path)
    backup.add_argument("--source", type=Path, required=True)
    verify = commands.add_parser("verify", help="validate a save without changing it")
    verify.add_argument("database", type=Path)
    restore = commands.add_parser("restore", help="restore a validated backup")
    restore.add_argument("source", type=Path)
    restore.add_argument("destination", type=Path)
    restore.add_argument("--replace", action="store_true")
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "backup":
        result = backup_database(args.source, args.destination)
    elif args.command == "verify":
        validate_database(args.database)
        result = args.database
    else:
        result = restore_database(args.source, args.destination, replace=args.replace)
    print(f"OK: {result}")


if __name__ == "__main__":
    main()
