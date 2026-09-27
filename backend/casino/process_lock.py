"""Small cross-process lock shared by the backend service and save restoration."""

from __future__ import annotations

import os
import threading
from pathlib import Path
from types import TracebackType


_held_paths: set[Path] = set()
_held_paths_lock = threading.Lock()


class BackendProcessLock:
    """Hold an OS file lock for one save path until the owning process exits."""

    def __init__(self, database_path: Path) -> None:
        self.path = database_path.resolve().with_suffix(
            database_path.suffix + ".backend.lock"
        )
        self._file = None

    def acquire(self) -> None:
        with _held_paths_lock:
            if self.path in _held_paths:
                raise RuntimeError("Another backend or restore operation owns this save")
            _held_paths.add(self.path)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._file = self.path.open("a+b")
            if os.name == "nt":
                import msvcrt

                self._file.seek(0)
                if self._file.read(1) == b"":
                    self._file.seek(0)
                    self._file.write(b"\0")
                    self._file.flush()
                self._file.seek(0)
                msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, RuntimeError) as error:
            if self._file is not None:
                self._file.close()
                self._file = None
            with _held_paths_lock:
                _held_paths.discard(self.path)
            if isinstance(error, OSError):
                raise RuntimeError("Another backend or restore operation owns this save") from error
            raise

    def release(self) -> None:
        if self._file is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                self._file.seek(0)
                msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        finally:
            self._file.close()
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
