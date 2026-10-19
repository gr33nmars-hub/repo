from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from casino.session_report import SessionReport, SessionReportWriter


class SessionReportTests(unittest.TestCase):
    def test_report_uses_required_date_format_and_is_written_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.txt"
            writer = SessionReportWriter(
                datetime(2026, 10, 19, 11, 12, 13, tzinfo=timezone.utc), path
            )

            writer.record("Гость", datetime(2026, 10, 19, 14, 15, 16, tzinfo=timezone.utc))
            writer.record("Другой", datetime(2026, 10, 19, 14, 15, 17, tzinfo=timezone.utc))

            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "+------------------------------------+\n"
                "| login | time_in | time_out |\n"
                "|-------|---------|----------|\n"
                "| Гость | 19.10.2026 11:12:13 | 19.10.2026 14:15:16 |\n"
                "+------------------------------------+\n",
            )

    def test_report_entity_is_comparable_and_displayable(self) -> None:
        report = SessionReport(
            "Гость",
            datetime(2026, 10, 19, 11, 12, 13, tzinfo=timezone.utc),
            datetime(2026, 10, 19, 14, 15, 16, tzinfo=timezone.utc),
        )
        self.assertEqual(report, report)
        self.assertIn("Гость", str(report))
        self.assertIn("SessionReport", repr(report))


if __name__ == "__main__":
    unittest.main()
