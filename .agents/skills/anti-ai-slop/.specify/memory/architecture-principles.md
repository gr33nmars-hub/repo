# Architecture Principles

## Boundaries

- `SKILL.md`, `protocols/`, `dimensions/`, `checklists/`, `taxonomies/`, `research/`, and `templates/` define human review behavior.
- `.specify/` defines Spec Kit memory and reusable feature templates.
- `codex/prompts/` defines operator prompts for Codex sessions.
- `.agents/skills/` defines reusable local workflow skills that can be copied into agent systems.
- `tools/validators/` contains executable coherence checks. Validators may read repository files and emit reports, but they must not mutate project files.
- `tools/apply_guardrails.py` and `tools/repo_inventory.py` are operational helpers. Mutating apply behavior must be explicit through a mode flag.
- `docs/process/` and `docs/references/` explain workflow and tool choices.

## Dependency Policy

Validators use the Python standard library by default. Any non-stdlib dependency must be justified in `docs/references/resource-catalog.yaml` and in the relevant plan.

## Failure Policy

Validators should report actionable findings with severity, path, rule, evidence, and fix. Aggregators may produce a score, but individual findings remain the primary evidence.
