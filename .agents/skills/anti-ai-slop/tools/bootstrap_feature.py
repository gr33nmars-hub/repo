from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path


TEMPLATE_OUTPUTS = {
    "spec-template.md": "spec.md",
    "plan-template.md": "plan.md",
    "tasks-template.md": "tasks.md",
    "checklist-template.md": "checklists/coherence.md",
}
TOKEN_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    slug = TOKEN_RE.sub("-", value.lower()).strip("-")
    return slug or "feature"


def render_template(text: str, feature_dir: str, feature_name: str, arguments: str) -> str:
    replacements = {
        "[FEATURE NAME]": feature_name,
        "[FEATURE_NAME]": feature_name,
        "[###-feature-name]": feature_dir,
        "[feature]": feature_dir,
        "[DATE]": date.today().isoformat(),
        "$ARGUMENTS": arguments,
    }
    for token, value in replacements.items():
        text = text.replace(token, value)
    return text


def bootstrap(root: Path | str, feature: str, feature_name: str | None = None, arguments: str = "") -> list[Path]:
    root = Path(root)
    feature_dir = slugify(feature)
    display_name = feature_name or feature_dir.replace("-", " ").title()
    template_root = root / ".specify/templates/overrides"
    output_root = root / "specs" / feature_dir
    created: list[Path] = []

    for template_name, output_name in TEMPLATE_OUTPUTS.items():
        template_path = template_root / template_name
        if not template_path.exists():
            continue
        output_path = output_root / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        rendered = render_template(template_path.read_text(encoding="utf-8"), feature_dir, display_name, arguments)
        output_path.write_text(rendered, encoding="utf-8")
        created.append(output_path)

    for dirname in ("evidence", "contracts", "decisions", "data-model"):
        (output_root / dirname).mkdir(parents=True, exist_ok=True)

    return created


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap a Spec Kit feature from local override templates.")
    parser.add_argument("feature", help="Feature directory name or title")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--name", default=None, help="Display feature name")
    parser.add_argument("--arguments", default="", help="Original feature prompt or arguments")
    args = parser.parse_args()

    for path in bootstrap(Path(args.root).resolve(), args.feature, args.name, args.arguments):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
