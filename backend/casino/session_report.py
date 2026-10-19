"""Session report required by the educational desktop-app brief."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from casino.domain.oop import ComparableEntity


class SessionReport(ComparableEntity):
    """One completed local application session in the required text-table format."""

    def __init__(self, login: str, time_in: datetime, time_out: datetime) -> None:
        self.login = login
        self.time_in = time_in
        self.time_out = time_out

    def comparison_key(self) -> tuple[object, ...]:
        return (self.login, self.time_in, self.time_out)

    @property
    def time_in_text(self) -> str:
        return self.time_in.strftime("%d.%m.%Y %H:%M:%S")

    @property
    def time_out_text(self) -> str:
        return self.time_out.strftime("%d.%m.%Y %H:%M:%S")

    def to_row(self) -> str:
        return f"| {self.login} | {self.time_in_text} | {self.time_out_text} |"


class SessionReportWriter:
    """Writes one report row once, even when desktop shutdown is requested repeatedly."""

    def __init__(self, started_at: datetime | None = None, path: Path | None = None) -> None:
        self._started_at = started_at or datetime.now().astimezone()
        configured = os.environ.get("NOIR_CASINO_SESSION_REPORT_PATH")
        if path is not None:
            self._path = path
        elif configured:
            self._path = Path(configured)
        else:
            self._path = Path.home() / ".noir-casino" / "session-report.txt"
        self._written = False

    @property
    def path(self) -> Path:
        return self._path

    def record(self, login: str, finished_at: datetime | None = None) -> Path:
        if self._written:
            return self._path
        report = SessionReport(login, self._started_at, finished_at or datetime.now().astimezone())
        self._path.parent.mkdir(parents=True, exist_ok=True)
        needs_header = not self._path.exists() or self._path.stat().st_size == 0
        with self._path.open("a", encoding="utf-8", newline="\n") as report_file:
            if needs_header:
                report_file.write("+------------------------------------+\n")
                report_file.write("| login | time_in | time_out |\n")
                report_file.write("|-------|---------|----------|\n")
            report_file.write(f"{report.to_row()}\n")
            report_file.write("+------------------------------------+\n")
        self._written = True
        return self._path
