from __future__ import annotations

import ast
from pathlib import Path

try:
    from .common import Finding, read_text, relpath, run_cli
except ImportError:
    from common import Finding, read_text, relpath, run_cli


REQUIRED_BOUNDARIES = [
    "tools/validators/",
    ".specify/",
    "codex/prompts/",
    ".agents/skills/",
    "docs/process/",
]

MUTATING_CALLS = {"write_text", "unlink", "rmtree", "remove"}


def has_mutating_call(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in MUTATING_CALLS:
            return True
        if isinstance(func, ast.Name) and func.id in MUTATING_CALLS:
            return True
    return False


def check(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    principles = root / ".specify/memory/architecture-principles.md"
    if not principles.exists():
        return [Finding("HIGH", "architecture-boundaries", relpath(principles, root), "Architecture principles are missing.", "Add .specify/memory/architecture-principles.md.")]
    text = read_text(principles)
    for boundary in REQUIRED_BOUNDARIES:
        if boundary not in text:
            findings.append(Finding("MEDIUM", "architecture-boundaries", relpath(principles, root), f"Boundary `{boundary}` is not documented.", "Document the boundary or remove it from the required list."))
    for path in (root / "tools/validators").glob("*.py") if (root / "tools/validators").exists() else []:
        validator_text = read_text(path)
        if has_mutating_call(validator_text) and path.name != "common.py":
            findings.append(Finding("HIGH", "architecture-boundaries", relpath(path, root), "Validator appears to mutate repository files.", "Keep validators read-only; move mutation into explicit tools."))
    return findings


if __name__ == "__main__":
    raise SystemExit(run_cli(check, "Architecture Boundaries Check"))
