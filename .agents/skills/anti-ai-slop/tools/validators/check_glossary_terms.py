from __future__ import annotations

import re
from pathlib import Path

try:
    from .common import Finding, iter_text_files, read_text, relpath, run_cli
except ImportError:
    from common import Finding, iter_text_files, read_text, relpath, run_cli


SENSITIVE_TERMS = {
    "AI slop": ["AI-slop", "ai slop", "AI slop"],
    "AI-smell risk": ["AI-smell risk", "ai-smell risk"],
    "output contract": ["output contract", "Output Contract"],
    "evidence-to-revision": ["evidence-to-revision", "Evidence-to-revision"],
}


def normalize_term(term: str) -> str:
    return term.strip().lower()


def glossary_terms(glossary_text: str) -> set[str]:
    terms: set[str] = set()
    for line in glossary_text.splitlines():
        if line.startswith("|") and not line.startswith("|---"):
            parts = [part.strip() for part in line.strip("|").split("|")]
            if parts and parts[0] != "Term":
                terms.add(normalize_term(parts[0]))
    return terms


def check(root: Path) -> list[Finding]:
    glossary = root / ".specify/memory/glossary.md"
    if not glossary.exists():
        return [Finding("HIGH", "glossary-terms", ".specify/memory/glossary.md", "Glossary is missing.", "Add glossary.md with core terms.")]
    terms = glossary_terms(read_text(glossary))
    findings: list[Finding] = []
    required_terms = {normalize_term(term) for term in SENSITIVE_TERMS}
    missing = required_terms - terms
    if missing:
        findings.append(Finding("HIGH", "glossary-terms", "glossary.md", f"Glossary misses required terms: {', '.join(sorted(missing))}.", "Add the missing terms."))
    authorship_pattern = re.compile(r"\b(written|made|generated)\s+by\s+AI\b", re.IGNORECASE)
    allowed = {"research/field_reported_ai_smell_patterns.md"}
    for path in iter_text_files(root):
        rel = relpath(path, root)
        if rel in allowed:
            continue
        text = read_text(path)
        if authorship_pattern.search(text) and "not" not in text[max(0, authorship_pattern.search(text).start() - 40):authorship_pattern.search(text).end() + 40].lower():
            findings.append(Finding("HIGH", "glossary-terms", rel, "Text may imply AI authorship from style.", "Use 'generic pattern' or 'AI-smell risk' and add a false-positive note."))
    return findings


if __name__ == "__main__":
    raise SystemExit(run_cli(check, "Glossary Terms Check"))
