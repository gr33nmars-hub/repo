from __future__ import annotations

from pathlib import Path

try:
    from .common import Finding, is_template_path, iter_non_fenced_lines, iter_text_files, read_text, relpath, run_cli
except ImportError:
    from common import Finding, is_template_path, iter_non_fenced_lines, iter_text_files, read_text, relpath, run_cli


KNOWN_TOKENS = [
    "[###-feature-name]",
    "[feature]",
    "[FEATURE_NAME]",
    "[FEATURE NAME]",
    "[DATE]",
    "$ARGUMENTS",
]
ALLOWED_LITERAL_PATHS = {
    "tools/bootstrap_feature.py",
    "tools/validators/check_template_tokens.py",
}


def check(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_text_files(root):
        rel = relpath(path, root)
        if (
            is_template_path(path)
            or rel.startswith("codex/prompts/")
            or rel.startswith(".codex/")
            or rel.startswith("tests/")
            or rel in ALLOWED_LITERAL_PATHS
        ):
            continue
        for lineno, line in iter_non_fenced_lines(read_text(path).splitlines()):
            for token in KNOWN_TOKENS:
                if token in line:
                    findings.append(
                        Finding(
                            "HIGH",
                            "template-tokens",
                            rel,
                            f"Unresolved template token `{token}` at line {lineno}.",
                            "Render the template with tools/bootstrap_feature.py or replace the token with the concrete feature path/value.",
                            evidence=line.strip()[:200],
                        )
                    )
                    break
    return findings


if __name__ == "__main__":
    raise SystemExit(run_cli(check, "Template Token Check"))
