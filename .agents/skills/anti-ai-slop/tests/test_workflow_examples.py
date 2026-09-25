from __future__ import annotations

import tempfile
import unittest
from importlib import import_module
from pathlib import Path


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class WorkflowExampleTests(unittest.TestCase):
    def test_security_workflows_use_current_examples(self) -> None:
        root = Path(__file__).resolve().parents[1]
        codeql = (root / ".github/workflows/codeql.yml").read_text(encoding="utf-8")
        gitleaks = (root / ".github/workflows/gitleaks.yml").read_text(encoding="utf-8")
        semgrep = (root / ".github/workflows/semgrep.yml").read_text(encoding="utf-8")
        osv = (root / ".github/workflows/osv-scanner.yml").read_text(encoding="utf-8")

        self.assertIn("github/codeql-action/init@v4", codeql)
        self.assertIn("github/codeql-action/analyze@v4", codeql)
        self.assertIn("actions/checkout@v6", gitleaks)
        self.assertIn("gitleaks/gitleaks-action@v3", gitleaks)
        self.assertNotIn("semgrep/semgrep-action", semgrep)
        self.assertIn("semgrep scan --config p/default --error", semgrep)
        self.assertIn("google/osv-scanner-action/.github/workflows/osv-scanner-reusable-pr.yml@v2.3.8", osv)
        self.assertIn("merge_group:", osv)

    def test_semgrep_workflow_documents_floating_cli_policy(self) -> None:
        root = Path(__file__).resolve().parents[1]
        semgrep = (root / ".github/workflows/semgrep.yml").read_text(encoding="utf-8")
        source_catalog = (root / "docs/references/source-catalog.md").read_text(encoding="utf-8")

        self.assertIn("Semgrep version policy:", semgrep)
        self.assertIn("review monthly", semgrep)
        self.assertIn("pin during reproducibility incidents", semgrep)
        self.assertIn("Semgrep CLI version policy", source_catalog)

    def test_workflow_integrity_checker_flags_stale_and_unsafe_workflows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root / ".github/workflows/semgrep.yml",
                "name: semgrep\n"
                "on:\n"
                "  pull_request:\n"
                "jobs:\n"
                "  semgrep:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - uses: actions/checkout@main\n"
                "      - uses: semgrep/semgrep-action@v1\n",
            )
            check_workflow_integrity = import_module("tools.validators.check_workflow_integrity")

            findings = check_workflow_integrity.check(root)
            messages = "\n".join(f.message for f in findings)

            self.assertIn("deprecated action `semgrep/semgrep-action@v1`", messages)
            self.assertIn("branch-pinned action `actions/checkout@main`", messages)
            self.assertIn("missing merge_group trigger", messages)
            self.assertIn("missing permissions block", messages)


if __name__ == "__main__":
    unittest.main()
