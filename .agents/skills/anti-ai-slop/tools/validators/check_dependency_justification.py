from __future__ import annotations

import json
import re
from json import JSONDecodeError
from pathlib import Path
from typing import Any

try:
    from .common import Finding, read_text, relpath, run_cli
except ImportError:
    from common import Finding, read_text, relpath, run_cli


MANIFESTS = ["requirements.txt", "pyproject.toml", "package.json", "pnpm-lock.yaml", "package-lock.json"]
BASELINE_PATH = Path("dependency-baseline.json")


def mentioned_in_catalog(root: Path, name: str) -> bool:
    catalog = root / "docs/references/resource-catalog.yaml"
    return catalog.exists() and name.lower() in read_text(catalog).lower()


def load_baseline(root: Path) -> tuple[set[str], set[str], list[Finding]]:
    path = root / BASELINE_PATH
    if not path.exists():
        return set(), set(), []
    try:
        data: Any = json.loads(read_text(path))
    except JSONDecodeError as exc:
        return (
            set(),
            set(),
            [
                Finding(
                    "HIGH",
                    "dependency-justification",
                    relpath(path, root),
                    f"Invalid dependency baseline JSON: {exc.msg}.",
                    "Fix dependency-baseline.json before dependency delta checks can be trusted.",
                    evidence=f"line {exc.lineno}, column {exc.colno}",
                )
            ],
        )
    if not isinstance(data, dict):
        return (
            set(),
            set(),
            [
                Finding(
                    "HIGH",
                    "dependency-justification",
                    relpath(path, root),
                    "Dependency baseline must be a JSON object.",
                    "Use keys `python_imports` and `manifests` with string arrays.",
                )
            ],
        )
    python_imports = data.get("python_imports", [])
    manifests = data.get("manifests", [])
    findings: list[Finding] = []
    if not isinstance(python_imports, list) or not all(isinstance(item, str) for item in python_imports):
        findings.append(Finding("HIGH", "dependency-justification", relpath(path, root), "`python_imports` must be a string array.", "Fix dependency-baseline.json."))
        python_imports = []
    if not isinstance(manifests, list) or not all(isinstance(item, str) for item in manifests):
        findings.append(Finding("HIGH", "dependency-justification", relpath(path, root), "`manifests` must be a string array.", "Fix dependency-baseline.json."))
        manifests = []
    return set(python_imports), set(manifests), findings


def python_imports(path: Path) -> set[str]:
    text = read_text(path)
    imports = set(re.findall(r"^\s*(?:import|from)\s+([a-zA-Z_][\w]*)", text, re.MULTILINE))
    stdlib_like = {
        "__future__", "argparse", "ast", "collections", "csv", "dataclasses", "datetime", "fnmatch",
        "importlib", "json", "os", "pathlib", "re", "shutil", "subprocess", "sys", "tempfile",
        "textwrap", "traceback", "typing", "unittest",
    }
    return {item for item in imports if item not in stdlib_like and not item.startswith("tools")}


def check(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    baseline_imports, baseline_manifests, baseline_findings = load_baseline(root)
    findings.extend(baseline_findings)
    for manifest in MANIFESTS:
        path = root / manifest
        if path.exists() and manifest not in baseline_manifests and not mentioned_in_catalog(root, manifest.split(".")[0]):
            findings.append(Finding("MEDIUM", "dependency-justification", relpath(path, root), "New dependency manifest exists but catalog justification is not explicit.", "Add dependency rationale to docs/references/resource-catalog.yaml or record it in dependency-baseline.json."))
    for path in list((root / "tools").rglob("*.py")) + list((root / "tests").rglob("*.py")) if (root / "tools").exists() else []:
        for dep in sorted(python_imports(path)):
            if dep in {"common"}:
                continue
            if dep in baseline_imports or mentioned_in_catalog(root, dep):
                continue
            findings.append(Finding("HIGH", "dependency-justification", relpath(path, root), f"New non-stdlib import `{dep}` found.", "Use stdlib, record the dependency in dependency-baseline.json, or justify it in the plan and resource catalog."))
    return findings


if __name__ == "__main__":
    raise SystemExit(run_cli(check, "Dependency Justification Check"))
