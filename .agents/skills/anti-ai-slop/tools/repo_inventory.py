from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


SKIP = {".git", ".codex", "__pycache__", "node_modules", ".venv", "venv"}
PRIORITY_FILES = [
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    ".specify/memory/constitution.md",
    "tools/validators/check_all.py",
]


def should_skip(path: Path, root: Path) -> bool:
    try:
        check_path = path.relative_to(root)
    except ValueError:
        check_path = path
    return any(part in SKIP for part in check_path.parts)


def iter_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file() and not should_skip(path, root):
            yield path


def inventory_data(root: Path) -> dict[str, object]:
    files = list(iter_files(root))
    suffixes = Counter(path.suffix.lower() or "[none]" for path in files)
    dirs = Counter(path.relative_to(root).parts[0] for path in files if path.relative_to(root).parts)
    priority_files = {rel: "present" if (root / rel).exists() else "missing" for rel in PRIORITY_FILES}
    return {
        "root": str(root),
        "file_count": len(files),
        "top_directories": dict(dirs.most_common(20)),
        "file_types": dict(suffixes.most_common(20)),
        "priority_files": priority_files,
    }


def inventory(root: Path) -> str:
    data = inventory_data(root)
    lines = [
        "# Existing Code Scan",
        "",
        f"- Root: `{data['root']}`",
        f"- Files: {data['file_count']}",
        "",
        "## Top Directories",
        "",
    ]
    for name, count in data["top_directories"].items():
        lines.append(f"- `{name}`: {count}")
    lines.extend(["", "## File Types", ""])
    for suffix, count in data["file_types"].items():
        lines.append(f"- `{suffix}`: {count}")
    lines.extend(["", "## Priority Files", ""])
    for rel, status in data["priority_files"].items():
        lines.append(f"- `{rel}`: {status}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a compact repository inventory.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default=None)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    text = json.dumps(inventory_data(root), indent=2, ensure_ascii=False) + "\n" if args.format == "json" else inventory(root)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
