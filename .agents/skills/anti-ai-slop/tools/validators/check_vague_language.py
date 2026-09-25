from __future__ import annotations

import re
from pathlib import Path

try:
    from .common import Finding, iter_non_fenced_lines, iter_text_files, read_text, relpath, run_cli
except ImportError:
    from common import Finding, iter_non_fenced_lines, iter_text_files, read_text, relpath, run_cli


VAGUE_TERMS = [
    "seamless", "robust", "comprehensive", "powerful", "cutting-edge", "revolutionary",
    "leverage", "unlock", "supercharge", "innovative", "world-class", "best-in-class",
]
EVIDENCE_TERMS = ["because", "measured", "evidence", "example", "acceptance", "validation", "specific"]
ALLOWED_PATTERN_DOCS = {
    "checklists/global_ai_smell_checklist.md",
    "dimensions/marketing_brand.md",
    "protocols/output_design_review_gate.md",
}


def check(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    pattern = re.compile(r"\b(" + "|".join(re.escape(term) for term in VAGUE_TERMS) + r")\b", re.IGNORECASE)
    for path in iter_text_files(root):
        rel = relpath(path, root)
        if rel.startswith(".github/") or rel.startswith("research/") or path.suffix == ".py" or rel in ALLOWED_PATTERN_DOCS:
            continue
        text = "\n".join(line for _, line in iter_non_fenced_lines(read_text(path).splitlines()))
        matches = pattern.findall(text)
        if not matches:
            continue
        lower = text.lower()
        evidence_count = sum(lower.count(term) for term in EVIDENCE_TERMS)
        severity = "HIGH" if len(matches) >= 8 and evidence_count == 0 else "LOW"
        if severity == "LOW" and len(matches) < 4:
            continue
        findings.append(Finding(severity, "vague-language", rel, f"Vague terms appear {len(matches)} times.", "Replace vague claims with mechanism, audience, constraint, or validation evidence.", ", ".join(sorted(set(m.lower() for m in matches)))[:200]))
    return findings


if __name__ == "__main__":
    raise SystemExit(run_cli(check, "Vague Language Check"))
