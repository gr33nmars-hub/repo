from __future__ import annotations

import re
from pathlib import Path

try:
    from .common import Finding, iter_non_fenced_lines, read_text, relpath, run_cli
except ImportError:
    from common import Finding, iter_non_fenced_lines, read_text, relpath, run_cli


EVIDENCE_RE = re.compile(r"\bEvidence:\s*(.+)$", re.IGNORECASE)
BACKTICK_RE = re.compile(r"`([^`]+)`")
PENDING_TEXT = "pending until implementation"


def evidence_refs(value: str) -> list[str]:
    backtick_refs = [match.strip() for match in BACKTICK_RE.findall(value) if match.strip()]
    if backtick_refs:
        return backtick_refs
    return [part.strip() for part in re.split(r"[,;]", value) if part.strip()]


def is_external_or_pending(value: str) -> bool:
    lowered = value.lower()
    return PENDING_TEXT in lowered or lowered.startswith(("http://", "https://"))


def check(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    tasks_paths = list(root.glob("specs/*/tasks.md"))
    for tasks_path in tasks_paths:
        for lineno, line in iter_non_fenced_lines(read_text(tasks_path).splitlines()):
            match = EVIDENCE_RE.search(line)
            if not match:
                continue
            raw_value = match.group(1).strip()
            if is_external_or_pending(raw_value):
                continue
            for ref in evidence_refs(raw_value):
                if is_external_or_pending(ref):
                    continue
                evidence_path = (root / ref).resolve()
                try:
                    evidence_path.relative_to(root.resolve())
                except ValueError:
                    findings.append(
                        Finding(
                            "HIGH",
                            "evidence-links",
                            relpath(tasks_path, root),
                            f"Evidence path escapes the repository at line {lineno}: {ref}.",
                            "Use a repository-relative evidence path or mark the task as `Evidence: Pending until implementation`.",
                            evidence=line.strip(),
                        )
                    )
                    continue
                if not evidence_path.exists():
                    findings.append(
                        Finding(
                            "HIGH",
                            "evidence-links",
                            relpath(tasks_path, root),
                            f"Evidence path does not exist at line {lineno}: {ref}.",
                            "Create the evidence file or use `Evidence: Pending until implementation` for incomplete work.",
                            evidence=line.strip(),
                        )
                    )
    return findings


if __name__ == "__main__":
    raise SystemExit(run_cli(check, "Evidence Link Check"))
