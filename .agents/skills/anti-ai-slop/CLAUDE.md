# Claude Code Guidance

This repository is a Markdown-first review skill and a Spec Kit style guardrail pack for reducing generic, template-like, unsupported, or over-smoothed output patterns.

## Core Rule

Do not infer AI authorship from style alone. Review visible quality signals only: specificity, evidence, purpose fit, traceability, usability, maintainability, and false-positive risk.

## When Reviewing Artifacts

1. Read `SKILL.md`.
2. Define the output contract: audience, job, medium, constraints, evidence needs, and success condition.
3. Use `taxonomies/task_purpose_matrix.md` to classify the work.
4. Use `protocols/output_design_review_gate.md` for universal checks.
5. Load only the relevant files under `dimensions/`.
6. Use `protocols/finding_format.md` for findings.
7. Pair every finding with visible evidence, impact, fix, and verification.

## When Working on the Guardrail Pack

Start from:

- `.specify/memory/constitution.md`
- `.specify/memory/glossary.md`
- `.specify/memory/architecture-principles.md`

Maintain traceability across `spec.md`, `plan.md`, `tasks.md`, evidence, and review notes. Prefer existing Markdown guidance before adding new policy language.

## Validation

Before delivery, run:

```powershell
python tools\validators\check_all.py --root . --format markdown
python -m unittest discover -s tests
```

For target repositories that adopted the pack:

```powershell
python tools\validators\check_all.py --root . --profile target-repo --format markdown
```
