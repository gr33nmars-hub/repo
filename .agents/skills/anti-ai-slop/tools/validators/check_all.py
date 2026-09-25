from __future__ import annotations

import argparse
import importlib
import traceback
from pathlib import Path

try:
    from .common import SEVERITIES, Finding, json_report, markdown_report, write_or_print
except ImportError:
    from common import SEVERITIES, Finding, json_report, markdown_report, write_or_print


CHECKS = [
    "check_config_integrity",
    "check_task_traceability",
    "check_spec_coverage",
    "check_evidence_links",
    "check_glossary_terms",
    "check_architecture_boundaries",
    "check_dependency_justification",
    "check_manifest_integrity",
    "check_resource_catalog_freshness",
    "check_template_tokens",
    "check_workflow_integrity",
    "check_vague_language",
    "check_placeholders",
]
PROFILES = {
    "pack-self": "Full guardrail pack self-check.",
    "target-repo": "Target repository check focused on code, specs, tests, tools, and workflows.",
    "feature": "Single feature check scoped to specs/<feature>/ findings.",
    "ci-strict": "CI gate; currently the same full scope as pack-self.",
}
TARGET_REPO_PREFIXES = (
    "src/",
    "app/",
    "packages/",
    "lib/",
    "tests/",
    "specs/",
    "tools/",
    ".github/",
    "config/",
)
ALWAYS_KEEP_RULES = {"CHECK_CRASH", "config-integrity"}


def load_check(name: str):
    try:
        return importlib.import_module(f"tools.validators.{name}")
    except ModuleNotFoundError:
        return importlib.import_module(name)


def finding_in_profile(finding: Finding, profile: str, feature: str | None) -> bool:
    if finding.rule in ALWAYS_KEEP_RULES:
        return True
    if profile in {"pack-self", "ci-strict"}:
        return True
    if profile == "target-repo":
        return finding.path.startswith(TARGET_REPO_PREFIXES)
    if profile == "feature":
        prefix = f"specs/{feature}/" if feature else "specs/"
        return finding.path.startswith(prefix)
    raise ValueError(f"Unknown validation profile: {profile}")


def check(root: Path, profile: str = "pack-self", feature: str | None = None) -> list[Finding]:
    if profile not in PROFILES:
        raise ValueError(f"Unknown validation profile: {profile}")
    findings: list[Finding] = []
    for name in CHECKS:
        try:
            module = load_check(name)
            findings.extend(module.check(root))
        except Exception as exc:
            details = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            findings.append(
                Finding(
                    severity="CRITICAL",
                    rule="CHECK_CRASH",
                    path=f"tools/validators/{name}.py",
                    message=f"Validator {name} crashed: {details}",
                    fix="Fix the crashing validator or its configuration; check_all must not report a clean score while a checker cannot run.",
                    evidence=traceback.format_exc(limit=3).strip(),
                )
            )
    return [finding for finding in findings if finding_in_profile(finding, profile, feature)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all anti-ai-slop coherence validators.")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="pack-self", help="Validation scan profile")
    parser.add_argument("--feature", default=None, help="Feature directory for --profile feature")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    findings = check(Path(args.root).resolve(), profile=args.profile, feature=args.feature)
    title = f"Anti-AI Slop Coherence Report ({args.profile})"
    report = json_report(findings) if args.format == "json" else markdown_report(findings, title)
    write_or_print(report, args.out)
    return 1 if any(SEVERITIES[f.severity] >= SEVERITIES["HIGH"] for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
