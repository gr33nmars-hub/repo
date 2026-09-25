from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


GUARDRAIL_DIRS = [".specify", ".agents", "codex", "docs/process", "docs/references", "checklists", "tools", "specs"]
GENERATED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
GENERATED_SUFFIXES = {".pyc", ".pyo"}
TEST_ONLY_PARTS = {"tests"}
MANIFEST_PATH = Path("manifest.txt")


def read_version_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    version = path.read_text(encoding="utf-8").strip()
    return version or None


def pack_version(source_root: Path) -> str:
    local_root = Path(__file__).resolve().parents[1]
    return read_version_file(source_root / "VERSION") or read_version_file(local_root / "VERSION") or "unknown"


def path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def validate_report_output_path(path: Path | None, target: Path, mode: str) -> None:
    if path is None or mode != "dry-run":
        return
    if path == target or path_is_relative_to(path, target):
        raise SystemExit(f"Dry-run report output cannot be inside the target repository: {path}")


def is_generated_artifact(rel: Path) -> bool:
    return bool(set(rel.parts) & GENERATED_PARTS) or rel.suffix.lower() in GENERATED_SUFFIXES


def is_test_only_artifact(rel: Path) -> bool:
    return bool(set(rel.parts) & TEST_ONLY_PARTS)


def should_copy(rel: Path) -> bool:
    return not is_generated_artifact(rel) and not is_test_only_artifact(rel)


def iter_manifest_files(source_root: Path) -> tuple[list[Path], list[str]]:
    manifest = source_root / MANIFEST_PATH
    if not manifest.exists():
        return [], []
    files: list[Path] = []
    warnings: list[str] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        item = line.strip()
        if not item:
            continue
        rel = Path(item)
        if rel.is_absolute() or ".." in rel.parts:
            warnings.append(f"unsafe manifest entry {item}")
            continue
        if not should_copy(rel):
            continue
        source = source_root / rel
        if source.is_file():
            files.append(source)
        else:
            warnings.append(f"missing manifest entry {rel.as_posix()}")
    return files, warnings


def iter_legacy_guardrail_files(source_root: Path) -> list[Path]:
    files: list[Path] = []
    for dirname in GUARDRAIL_DIRS:
        source_dir = source_root / dirname
        if not source_dir.exists():
            continue
        for source in source_dir.rglob("*"):
            if not source.is_file():
                continue
            rel = source.relative_to(source_root)
            if should_copy(rel):
                files.append(source)
    return files


def iter_copy_sources(source_root: Path) -> tuple[list[Path], list[str]]:
    manifest_files, warnings = iter_manifest_files(source_root)
    if (source_root / MANIFEST_PATH).exists():
        return manifest_files, warnings
    return iter_legacy_guardrail_files(source_root), warnings


def copy_missing(source_root: Path, target_root: Path, mode: str) -> tuple[list[str], list[str]]:
    actions: list[str] = []
    sources, warnings = iter_copy_sources(source_root)
    for source in sources:
        rel = source.relative_to(source_root)
        target = target_root / rel
        if target.exists():
            actions.append(f"skip existing {rel.as_posix()}")
            continue
        actions.append(f"copy {rel.as_posix()}")
        if mode == "merge":
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    return actions, warnings


def build_report(source: Path, target: Path, mode: str, actions: list[str], warnings: list[str]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "tool": "apply_guardrails",
        "tool_version": pack_version(source),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "source": str(source),
        "target": str(target),
        "target_exists": target.exists(),
        "changed": mode == "merge" and any(action.startswith("copy ") for action in actions),
        "actions": actions,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply anti-ai-slop guardrail files to another repository.")
    parser.add_argument("--source", default=".", help="Pack source root")
    parser.add_argument("--target", required=True, help="Target repository")
    parser.add_argument("--mode", choices=["dry-run", "merge"], default="dry-run")
    parser.add_argument("--json-out", default=None, help="Optional path for a machine-readable apply report")
    parser.add_argument("--manifest-out", default=None, help="Optional durable apply manifest path; never overwritten")
    args = parser.parse_args()
    source = Path(args.source).resolve()
    target = Path(args.target).resolve()
    if not source.exists() or not source.is_dir():
        raise SystemExit(f"Source is not a directory: {source}")
    if args.mode == "merge" and (not target.exists() or not target.is_dir()):
        raise SystemExit(f"Target is not a directory: {target}")
    if args.mode == "dry-run" and target.exists() and not target.is_dir():
        raise SystemExit(f"Target exists but is not a directory: {target}")
    manifest_out = Path(args.manifest_out).resolve() if args.manifest_out else None
    json_out = Path(args.json_out).resolve() if args.json_out else None
    validate_report_output_path(manifest_out, target, args.mode)
    validate_report_output_path(json_out, target, args.mode)
    if manifest_out and manifest_out.exists():
        raise SystemExit(f"Manifest already exists: {manifest_out}")
    actions, warnings = copy_missing(source, target, args.mode)
    report = build_report(source, target, args.mode, actions, warnings)
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if manifest_out:
        manifest_out.parent.mkdir(parents=True, exist_ok=True)
        manifest_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for action in actions:
        print(action)
    for warning in warnings:
        print(warning, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
