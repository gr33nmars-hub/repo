from __future__ import annotations

import re
from pathlib import Path

try:
    from .common import Finding, read_text, relpath, run_cli
except ImportError:
    from common import Finding, read_text, relpath, run_cli


DEPRECATED_ACTIONS = {
    "github/codeql-action/init@v3": "Use github/codeql-action/init@v4.",
    "github/codeql-action/analyze@v3": "Use github/codeql-action/analyze@v4.",
    "github/codeql-action/autobuild@v3": "Use github/codeql-action/autobuild@v4.",
    "github/codeql-action/upload-sarif@v3": "Use github/codeql-action/upload-sarif@v4.",
    "gitleaks/gitleaks-action@v2": "Use gitleaks/gitleaks-action@v3.",
    "semgrep/semgrep-action@v1": "Use native Semgrep CLI, for example `semgrep scan --config p/default --error`.",
    "google/osv-scanner-action@v1": "Use google/osv-scanner-action reusable workflows such as osv-scanner-reusable-pr.yml@v2.3.8.",
}
SECURITY_WORKFLOWS = {"codeql.yml", "gitleaks.yml", "semgrep.yml", "osv-scanner.yml"}
USES_RE = re.compile(r"\buses:\s*['\"]?([^'\"\s]+)")
BRANCH_REFS = {"main", "master", "dev", "develop", "latest"}


def action_ref(value: str) -> tuple[str, str | None]:
    if "@" not in value:
        return value, None
    action, ref = value.rsplit("@", 1)
    return action, ref


def has_workflow_key(text: str, key: str) -> bool:
    return re.search(rf"^\s*{re.escape(key)}:\s*$", text, re.MULTILINE) is not None


def check(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    workflow_root = root / ".github" / "workflows"
    if not workflow_root.exists():
        return findings

    for path in sorted(workflow_root.glob("*.yml")) + sorted(workflow_root.glob("*.yaml")):
        rel = relpath(path, root)
        text = read_text(path)
        for line_no, line in enumerate(text.splitlines(), 1):
            match = USES_RE.search(line)
            if not match:
                continue
            value = match.group(1)
            if value in DEPRECATED_ACTIONS:
                findings.append(
                    Finding(
                        "HIGH",
                        "workflow-integrity",
                        rel,
                        f"Workflow uses deprecated action `{value}` at line {line_no}.",
                        DEPRECATED_ACTIONS[value],
                        evidence=line.strip(),
                    )
                )
            _, ref = action_ref(value)
            if ref is None:
                findings.append(
                    Finding(
                        "HIGH",
                        "workflow-integrity",
                        rel,
                        f"Workflow uses unpinned action `{value}` at line {line_no}.",
                        "Pin the action to a release tag or commit SHA.",
                        evidence=line.strip(),
                    )
                )
            elif ref in BRANCH_REFS:
                findings.append(
                    Finding(
                        "HIGH",
                        "workflow-integrity",
                        rel,
                        f"Workflow uses branch-pinned action `{value}` at line {line_no}.",
                        "Pin the action to a release tag or commit SHA instead of a moving branch.",
                        evidence=line.strip(),
                    )
                )
        if path.name in SECURITY_WORKFLOWS:
            if not has_workflow_key(text, "merge_group"):
                findings.append(
                    Finding(
                        "HIGH",
                        "workflow-integrity",
                        rel,
                        "Security workflow is missing merge_group trigger.",
                        "Add a merge_group trigger so merge queue checks run the same security gate.",
                    )
                )
            if not has_workflow_key(text, "permissions"):
                findings.append(
                    Finding(
                        "HIGH",
                        "workflow-integrity",
                        rel,
                        "Security workflow is missing permissions block.",
                        "Add least-privilege permissions for the workflow or job.",
                    )
                )
    return findings


if __name__ == "__main__":
    raise SystemExit(run_cli(check, "Workflow Integrity Check"))
