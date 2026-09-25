from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any

try:
    from .common import Finding, read_text, relpath, run_cli
except ImportError:
    from common import Finding, read_text, relpath, run_cli


CONFIG_PATHS = [
    Path("config/guardrails.json"),
    Path("config/guardrails.yaml"),
    Path("config/guardrails.yml"),
]
UNSUPPORTED_CONFIG_PATHS = [
    Path("config/guardrails.local.json"),
]
LIST_FIELDS = {"include_dirs", "exclude_dirs", "include_files", "exclude_files"}
DICT_FIELDS = {"profiles", "severity_thresholds"}
YAML_SUBSET = (
    "Supported YAML subset: top-level `key: value`, inline lists such as "
    "`include_dirs: [tools, specs]`, and block lists only for list fields. "
    "Nested mappings are intentionally rejected; use JSON for nested profiles."
)


def structure_findings(data: Any, path: Path, root: Path) -> list[Finding]:
    if not isinstance(data, dict):
        return [
            Finding(
                "CRITICAL",
                "config-integrity",
                relpath(path, root),
                "Guardrails config must be a JSON/YAML object at the top level.",
                "Use a mapping with keys such as include_dirs, exclude_dirs, and profiles.",
            )
        ]

    findings: list[Finding] = []
    for field in sorted(LIST_FIELDS):
        if field in data and not (
            isinstance(data[field], list) and all(isinstance(item, str) and item for item in data[field])
        ):
            findings.append(
                Finding(
                    "HIGH",
                    "config-integrity",
                    relpath(path, root),
                    f"`{field}` must be a non-empty string list when present.",
                    f"Set `{field}` to an array of path strings or remove it.",
                    evidence=repr(data[field]),
                )
            )
    for field in sorted(DICT_FIELDS):
        if field in data and not isinstance(data[field], dict):
            findings.append(
                Finding(
                    "HIGH",
                    "config-integrity",
                    relpath(path, root),
                    f"`{field}` must be an object when present.",
                    f"Set `{field}` to a mapping or remove it.",
                    evidence=repr(data[field]),
                )
            )
    return findings


def parse_simple_yaml_mapping(text: str, path: Path, root: Path) -> tuple[dict[str, Any], list[Finding]]:
    data: dict[str, Any] = {}
    findings: list[Finding] = []
    active_list_key: str | None = None

    for lineno, raw_line in enumerate(text.splitlines(), 1):
        if "\t" in raw_line[: len(raw_line) - len(raw_line.lstrip())]:
            findings.append(
                Finding(
                    "CRITICAL",
                    "config-integrity",
                    relpath(path, root),
                    "YAML indentation must use spaces, not tabs.",
                    "Replace tab indentation with spaces.",
                    evidence=f"line {lineno}: {raw_line}",
                )
            )
            continue

        line = raw_line.split("#", 1)[0].rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip(" "))
        if stripped.startswith("- "):
            if active_list_key is None:
                findings.append(
                    Finding(
                        "CRITICAL",
                        "config-integrity",
                        relpath(path, root),
                        "YAML list item appears before a mapping key.",
                        "Nest list items under a key such as include_dirs.",
                        evidence=f"line {lineno}: {raw_line}",
                    )
                )
                continue
            item = stripped[2:].strip().strip("\"'")
            if item:
                data.setdefault(active_list_key, []).append(item)
            continue
        if indent > 0:
            findings.append(
                Finding(
                    "CRITICAL",
                    "config-integrity",
                    relpath(path, root),
                    "Nested YAML mappings are not supported by the guardrails config parser.",
                    YAML_SUBSET,
                    evidence=f"line {lineno}: {raw_line}",
                )
            )
            active_list_key = None
            continue

        active_list_key = None
        if ":" not in stripped:
            findings.append(
                Finding(
                    "CRITICAL",
                    "config-integrity",
                    relpath(path, root),
                    "YAML mapping line is missing `:`.",
                    "Use `key: value` syntax.",
                    evidence=f"line {lineno}: {raw_line}",
                )
            )
            continue

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            findings.append(
                Finding(
                    "CRITICAL",
                    "config-integrity",
                    relpath(path, root),
                    "YAML mapping key is empty.",
                    "Add a non-empty key before `:`.",
                    evidence=f"line {lineno}: {raw_line}",
                )
            )
            continue
        if value == "":
            data[key] = [] if key in LIST_FIELDS else {}
            active_list_key = key if key in LIST_FIELDS else None
        elif value.startswith("[") and value.endswith("]"):
            items = [item.strip().strip("\"'") for item in value[1:-1].split(",") if item.strip()]
            data[key] = items
        elif value in {"{}", "[]"}:
            data[key] = {} if value == "{}" else []
        else:
            data[key] = value.strip("\"'")

    return data, findings


def check(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for rel in UNSUPPORTED_CONFIG_PATHS:
        path = root / rel
        if path.exists():
            findings.append(
                Finding(
                    "HIGH",
                    "config-integrity",
                    relpath(path, root),
                    "Local guardrails config overlays are not supported yet.",
                    "Use --profile for scan selection, or move shared config into config/guardrails.json.",
                )
            )
    for rel in CONFIG_PATHS:
        path = root / rel
        if not path.exists():
            continue
        text = read_text(path)
        if path.suffix == ".json":
            try:
                data = json.loads(text)
            except JSONDecodeError as exc:
                findings.append(
                    Finding(
                        "CRITICAL",
                        "config-integrity",
                        relpath(path, root),
                        f"Invalid JSON syntax: {exc.msg}.",
                        "Fix the JSON syntax before running downstream validators.",
                        evidence=f"line {exc.lineno}, column {exc.colno}",
                    )
                )
                continue
            findings.extend(structure_findings(data, path, root))
            continue

        data, yaml_findings = parse_simple_yaml_mapping(text, path, root)
        findings.extend(yaml_findings)
        if not yaml_findings:
            findings.extend(structure_findings(data, path, root))
    return findings


if __name__ == "__main__":
    raise SystemExit(run_cli(check, "Config Integrity Check"))
