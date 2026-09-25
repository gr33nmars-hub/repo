from __future__ import annotations

import re
from pathlib import Path

try:
    from .common import Finding, extract_ids, iter_non_fenced_lines, read_text, relpath, repo_path, run_cli
except ImportError:
    from common import Finding, extract_ids, iter_non_fenced_lines, read_text, relpath, repo_path, run_cli


TASK_RE = re.compile(r"\bT\d{3,}\b")
FILES_RE = re.compile(r"\bFiles:\s*(.+)$", re.IGNORECASE)
FILE_SPLIT_RE = re.compile(r"[,;]")


def ids_in_feature(feature_dir: Path, prefix: str) -> set[str]:
    ids: set[str] = set()
    for name in ("spec.md", "plan.md"):
        path = feature_dir / name
        if path.exists():
            ids.update(extract_ids(read_text(path), prefix))
    for path in (feature_dir / "adrs").glob("*.md") if (feature_dir / "adrs").exists() else []:
        ids.update(extract_ids(read_text(path), prefix))
    return ids


def task_files(line: str) -> list[str]:
    match = FILES_RE.search(line)
    if not match:
        return []
    raw = match.group(1)
    return [part.strip().strip("`") for part in FILE_SPLIT_RE.split(raw) if part.strip()]


def is_parallel_task(line: str) -> bool:
    return "[P]" in line or " parallel " in f" {line.lower()} "


def check(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for tasks_path in root.glob("specs/*/tasks.md"):
        text = read_text(tasks_path)
        spec_path = tasks_path.parent / "spec.md"
        spec_text = read_text(spec_path) if spec_path.exists() else ""
        spec_reqs = extract_ids(spec_text, "FR")
        defined_us = ids_in_feature(tasks_path.parent, "US")
        defined_sc = ids_in_feature(tasks_path.parent, "SC")
        defined_adr = ids_in_feature(tasks_path.parent, "ADR")
        task_lines = [line for _, line in iter_non_fenced_lines(text.splitlines()) if TASK_RE.search(line)]
        if not spec_path.exists():
            findings.append(Finding("HIGH", "task-traceability", relpath(tasks_path, root), "tasks.md has no sibling spec.md.", "Add spec.md with FR-* requirements."))
            continue
        referenced_reqs: set[str] = set()
        parallel_files: dict[str, list[str]] = {}
        for line in task_lines:
            task_id = TASK_RE.search(line).group(0)
            refs = extract_ids(line, "FR")
            referenced_reqs.update(refs)
            if not refs:
                findings.append(Finding("HIGH", "task-traceability", relpath(tasks_path, root), f"{task_id} does not reference an FR-* requirement.", "Add an FR-* reference in the traceability table or task line.", line.strip()))
            missing = refs - spec_reqs
            if missing:
                findings.append(Finding("HIGH", "task-traceability", relpath(tasks_path, root), f"{task_id} references missing requirements: {', '.join(sorted(missing))}.", "Define the requirement in spec.md or correct the task reference.", line.strip()))
            missing_us = extract_ids(line, "US") - defined_us
            if missing_us:
                findings.append(Finding("HIGH", "task-traceability", relpath(tasks_path, root), f"{task_id} references missing US references: {', '.join(sorted(missing_us))}.", "Define the user story in spec/plan/tasks or correct the task reference.", line.strip()))
            missing_sc = extract_ids(line, "SC") - defined_sc
            if missing_sc:
                findings.append(Finding("HIGH", "task-traceability", relpath(tasks_path, root), f"{task_id} references missing SC references: {', '.join(sorted(missing_sc))}.", "Define the success criterion in spec/plan/tasks or correct the task reference.", line.strip()))
            adr_refs = extract_ids(line, "ADR")
            missing_adr = adr_refs - defined_adr
            if missing_adr:
                findings.append(Finding("HIGH", "task-traceability", relpath(tasks_path, root), f"{task_id} references missing ADR references: {', '.join(sorted(missing_adr))}.", "Add the ADR reference to plan/tasks/adrs or correct the task reference.", line.strip()))
            files = task_files(line)
            if len(files) > 5 and not (adr_refs & defined_adr):
                findings.append(Finding("HIGH", "task-traceability", relpath(tasks_path, root), f"{task_id} touches {len(files)} files without an ADR.", "Split the task or add an ADR reference justifying the wide change.", line.strip()))
            if is_parallel_task(line):
                for file_path in files:
                    parallel_files.setdefault(file_path, []).append(task_id)
        for file_path, task_ids in sorted(parallel_files.items()):
            if len(task_ids) > 1:
                findings.append(Finding("HIGH", "task-traceability", relpath(tasks_path, root), f"Parallel tasks share files: {file_path} in {', '.join(task_ids)}.", "Remove parallel markers or split file ownership so parallel tasks do not touch the same file.", file_path))
        for req in sorted(spec_reqs - referenced_reqs):
            findings.append(Finding("HIGH", "task-traceability", relpath(tasks_path, root), f"{req} is not referenced by any task.", "Add at least one task referencing the requirement or remove the requirement.", req))
        if not task_lines:
            findings.append(Finding("MEDIUM", "task-traceability", relpath(tasks_path, root), "tasks.md contains no T### tasks.", "Add traceable T### task IDs."))
    if not list(root.glob("specs/*/tasks.md")):
        findings.append(Finding("MEDIUM", "task-traceability", "specs/", "No feature tasks.md files found.", "Add specs/<feature>/tasks.md for traceable implementation work."))
    return findings


if __name__ == "__main__":
    raise SystemExit(run_cli(check, "Task Traceability Check"))
