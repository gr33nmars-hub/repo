from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.validators.common import Finding, markdown_report, read_text, write_or_print


REQUIRED_FIELDS = ("verified_at", "maintenance_status", "license_checked")


def parse_resources(text: str) -> list[dict[str, str]]:
    resources: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "resources:":
            continue
        if stripped.startswith("- "):
            if current is not None:
                resources.append(current)
            current = {}
            stripped = stripped[2:].strip()
        if current is None or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        current[key.strip()] = value.strip().strip("\"'")
    if current is not None:
        resources.append(current)
    return resources


def check(root: Path) -> list[Finding]:
    path = root / "docs/references/resource-catalog.yaml"
    if not path.exists():
        return [
            Finding(
                "HIGH",
                "resource-catalog-freshness",
                "docs/references/resource-catalog.yaml",
                "Resource catalog is missing.",
                "Add docs/references/resource-catalog.yaml with freshness metadata.",
            )
        ]
    resources = parse_resources(read_text(path))
    findings: list[Finding] = []
    if not resources:
        findings.append(
            Finding(
                "HIGH",
                "resource-catalog-freshness",
                "docs/references/resource-catalog.yaml",
                "Resource catalog has no resources.",
                "Add at least one resource entry with freshness metadata.",
            )
        )
    for resource in resources:
        name = resource.get("name", "[unnamed]")
        missing = [field for field in REQUIRED_FIELDS if field not in resource or not resource[field]]
        if missing:
            findings.append(
                Finding(
                    "HIGH",
                    "resource-catalog-freshness",
                    "docs/references/resource-catalog.yaml",
                    f"Resource `{name}` is missing freshness metadata: {', '.join(missing)}.",
                    "Add verified_at, maintenance_status, and license_checked to the resource entry.",
                )
            )
    return findings


def report(root: Path) -> str:
    findings = check(root)
    return markdown_report(findings, "Resource Catalog Freshness Report")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check resource catalog freshness metadata.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    findings = check(Path(args.root).resolve())
    write_or_print(markdown_report(findings, "Resource Catalog Freshness Report"), args.out)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
