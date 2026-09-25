from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence


SEVERITIES = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
TEXT_SUFFIXES = {".md", ".txt", ".py", ".yml", ".yaml", ".json", ".toml"}
SKIP_PARTS = {".git", ".codex", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv"}
TEMPLATE_PARTS = {"templates", "overrides"}


@dataclass(frozen=True)
class Finding:
    severity: str
    rule: str
    path: str
    message: str
    fix: str
    evidence: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def repo_path(root: Path, *parts: str) -> Path:
    return root.joinpath(*parts)


def relpath(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def should_skip(path: Path, root: Path | None = None) -> bool:
    check_path = path
    if root is not None:
        try:
            check_path = path.relative_to(root)
        except ValueError:
            check_path = path
    return any(part in SKIP_PARTS for part in check_path.parts)


def is_template_path(path: Path) -> bool:
    parts = set(path.parts)
    return bool(parts & TEMPLATE_PARTS) or path.name.endswith("-template.md")


def iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file() or should_skip(path, root):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def iter_non_fenced_lines(lines: Sequence[str]) -> Iterable[tuple[int, str]]:
    in_fence = False
    for idx, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield idx, line


def extract_ids(text: str, prefix: str) -> set[str]:
    return set(re.findall(rf"\b{re.escape(prefix)}-\d{{3,}}\b", text))


def markdown_report(findings: Sequence[Finding], title: str = "Validation Report") -> str:
    counts = {severity: 0 for severity in SEVERITIES}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    score = max(0, 100 - counts["CRITICAL"] * 35 - counts["HIGH"] * 20 - counts["MEDIUM"] * 8 - counts["LOW"] * 2)
    lines = [
        f"# {title}",
        "",
        f"Score: {score}",
        f"CRITICAL: {counts['CRITICAL']}",
        f"HIGH: {counts['HIGH']}",
        f"MEDIUM: {counts['MEDIUM']}",
        f"LOW: {counts['LOW']}",
        "",
    ]
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"
    for finding in findings:
        lines.extend(
            [
                f"## {finding.severity} - {finding.rule}",
                "",
                f"- Path: `{finding.path}`",
                f"- Message: {finding.message}",
                f"- Fix: {finding.fix}",
            ]
        )
        if finding.evidence:
            lines.append(f"- Evidence: {finding.evidence}")
        lines.append("")
    return "\n".join(lines)


def json_report(findings: Sequence[Finding]) -> str:
    return json.dumps([finding.to_dict() for finding in findings], indent=2, ensure_ascii=False) + "\n"


def write_or_print(text: str, out: str | None) -> None:
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def build_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--out", default=None, help="Optional output path")
    return parser


def run_cli(check_fn, description: str) -> int:
    parser = build_parser(description)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    findings = check_fn(root)
    report = json_report(findings) if args.format == "json" else markdown_report(findings, description)
    write_or_print(report, args.out)
    return 1 if any(SEVERITIES[f.severity] >= SEVERITIES["HIGH"] for f in findings) else 0
