from __future__ import annotations

import re
from pathlib import Path

try:
    from .common import Finding, is_template_path, iter_non_fenced_lines, iter_text_files, read_text, relpath, run_cli
except ImportError:
    from common import Finding, is_template_path, iter_non_fenced_lines, iter_text_files, read_text, relpath, run_cli


PLACEHOLDER_RE = re.compile(r"(\bTBD\b|\bTODO\b|<[^>\n]+>|\[[A-Z][A-Z0-9 _-]{2,}\])")
ALLOWED_EXAMPLE_PATHS = {
    "checklists/global_ai_smell_checklist.md",
    "dimensions/code_developer_outputs.md",
}


def check(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_text_files(root):
        rel = relpath(path, root)
        if (
            is_template_path(path)
            or rel.startswith("codex/prompts/")
            or rel.startswith(".codex/")
            or rel.startswith("tests/")
            or path.suffix == ".py"
            or rel in ALLOWED_EXAMPLE_PATHS
        ):
            continue
        text = read_text(path)
        for idx, line in iter_non_fenced_lines(text.splitlines()):
            if "TODO policy" in line or "TODOs" in line or "TDD" in line:
                continue
            match = PLACEHOLDER_RE.search(line)
            if match:
                findings.append(Finding("MEDIUM", "placeholders", rel, f"Unresolved placeholder-like text at line {idx}.", "Resolve the placeholder or move it into a template file.", line.strip()[:200]))
                break
    return findings


if __name__ == "__main__":
    raise SystemExit(run_cli(check, "Placeholder Check"))
