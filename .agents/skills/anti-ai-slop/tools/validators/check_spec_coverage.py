from __future__ import annotations

from pathlib import Path

try:
    from .common import Finding, extract_ids, iter_non_fenced_lines, read_text, relpath, run_cli
except ImportError:
    from common import Finding, extract_ids, iter_non_fenced_lines, read_text, relpath, run_cli


REQUIRED_MEMORY = [
    ".specify/memory/constitution.md",
    ".specify/memory/glossary.md",
    ".specify/memory/architecture-principles.md",
    ".specify/memory/product-principles.md",
]
REQUIRED_PROMPTS = [
    "codex/prompts/00-apply-pack-to-existing-repo.md",
    "codex/prompts/01-run-coherence-check.md",
    "codex/prompts/02-pr-review.md",
]


def check(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for required in REQUIRED_MEMORY + REQUIRED_PROMPTS:
        if not (root / required).exists():
            findings.append(Finding("HIGH", "spec-coverage", required, "Required guardrail file is missing.", "Add the file or update the coverage policy."))
    feature_dirs = [path for path in (root / "specs").glob("*") if path.is_dir() and not path.name.startswith("_")] if (root / "specs").exists() else []
    if not feature_dirs:
        findings.append(Finding("HIGH", "spec-coverage", "specs/", "No feature specification directories found.", "Add specs/<feature>/spec.md, plan.md, and tasks.md."))
        return findings
    for feature in feature_dirs:
        for name in ("spec.md", "plan.md", "tasks.md"):
            path = feature / name
            if not path.exists():
                findings.append(Finding("HIGH", "spec-coverage", relpath(path, root), f"Feature is missing {name}.", f"Add {name} for this feature."))
        spec_path = feature / "spec.md"
        if spec_path.exists():
            text = read_text(spec_path)
            check_text = "\n".join(line for _, line in iter_non_fenced_lines(text.splitlines()))
            if not extract_ids(check_text, "FR"):
                findings.append(Finding("HIGH", "spec-coverage", relpath(spec_path, root), "spec.md has no FR-* requirements.", "Add functional requirements with FR-001 style IDs."))
            if "Out of Scope" not in check_text:
                findings.append(Finding("MEDIUM", "spec-coverage", relpath(spec_path, root), "spec.md does not define out-of-scope items.", "Add an Out of Scope section."))
    return findings


if __name__ == "__main__":
    raise SystemExit(run_cli(check, "Spec Coverage Check"))
