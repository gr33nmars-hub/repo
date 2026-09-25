from __future__ import annotations

from pathlib import Path

try:
    from .common import Finding, read_text, run_cli, should_skip
except ImportError:
    from common import Finding, read_text, run_cli, should_skip


GENERATED_SUFFIXES = {".pyc", ".pyo"}


def tracked_files(root: Path) -> set[str]:
    files: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_file() or should_skip(path, root) or path.suffix.lower() in GENERATED_SUFFIXES:
            continue
        rel = path.relative_to(root).as_posix()
        files.add(rel)
    return files


def manifest_entries(root: Path) -> set[str]:
    manifest = root / "manifest.txt"
    entries: set[str] = set()
    for line in read_text(manifest).splitlines():
        item = line.strip().replace("\\", "/")
        if item:
            entries.add(item)
    return entries


def check(root: Path) -> list[Finding]:
    manifest = root / "manifest.txt"
    if not manifest.exists():
        return []
    expected = tracked_files(root)
    actual = manifest_entries(root)
    findings: list[Finding] = []
    missing = sorted(expected - actual)
    stale = sorted(actual - expected)
    if missing:
        findings.append(
            Finding(
                "HIGH",
                "manifest-integrity",
                "manifest.txt",
                "manifest.txt is missing tracked files: " + ", ".join(missing[:20]),
                "Add missing tracked non-state files to manifest.txt.",
                evidence=f"missing_count={len(missing)}",
            )
        )
    if stale:
        findings.append(
            Finding(
                "HIGH",
                "manifest-integrity",
                "manifest.txt",
                "manifest.txt lists files that do not exist: " + ", ".join(stale[:20]),
                "Remove stale entries from manifest.txt or restore the listed files.",
                evidence=f"stale_count={len(stale)}",
            )
        )
    return findings


if __name__ == "__main__":
    raise SystemExit(run_cli(check, "Manifest Integrity Check"))
