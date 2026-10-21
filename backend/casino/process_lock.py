"""Межпроцессная блокировка файла базы данных (Windows msvcrt / POSIX fcntl)."""

from __future__ import annotations

import importlib
import os
import threading
from pathlib import Path
from types import TracebackType
from typing import BinaryIO

_held_paths: set[Path] = set()
_held_paths_lock = threading.Lock()


class BackendProcessLock:
    """Файловая блокировка для защиты базы данных от одновременного доступа нескольких процессов."""

    def __init__(self, database_path: Path) -> None:
        self.path = database_path.resolve().with_suffix(database_path.suffix + ".backend.lock")
        self._file: BinaryIO | None = None

    def acquire(self) -> None:
        with _held_paths_lock:
            if self.path in _held_paths:
                raise RuntimeError("Another backend or restore operation owns this save")
            _held_paths.add(self.path)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            lock_file = self.path.open("a+b")
            self._file = lock_file
            if os.name == "nt":
                msvcrt = importlib.import_module("msvcrt")

                lock_file.seek(0)
                if lock_file.read(1) == b"":
                    lock_file.seek(0)
                    lock_file.write(b"\0")
                    lock_file.flush()
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl = importlib.import_module("fcntl")
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            if self._file is not None:
                self._file.close()
                self._file = None
            with _held_paths_lock:
                _held_paths.discard(self.path)
            raise RuntimeError("Another backend or restore operation owns this save") from error

    def release(self) -> None:
        lock_file = self._file
        if lock_file is None:
            return
        try:
            if os.name == "nt":
                msvcrt = importlib.import_module("msvcrt")

                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl = importlib.import_module("fcntl")
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        finally:
            lock_file.close()
            self._file = None
            with _held_paths_lock:
                _held_paths.discard(self.path)

    def __enter__(self) -> BackendProcessLock:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()
