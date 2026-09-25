# Repository Guidance

This repository is both a Codex skill and a Spec Kit style guardrail pack for reducing generic, template-like, and AI-slop output patterns.

## Operating Rules

- Preserve the core safety rule: never infer AI authorship from style alone.
- Start feature work from `.specify/memory/constitution.md`, `.specify/memory/glossary.md`, and `.specify/memory/architecture-principles.md`.
- For implementation work, maintain traceability across `spec.md`, `plan.md`, `tasks.md`, validation evidence, and PR review notes.
- Prefer the existing Markdown skill files before adding new policy language.
- Use `tools/validators/check_all.py --root . --format markdown` before delivery.

## Expected Workflow

```text
inventory
-> constitution / glossary / architecture principles
-> spec
-> clarify
-> checklist
-> plan
-> tasks
-> analyze
-> implementation
-> validation evidence
-> PR review
```

## Review Boundaries

- Findings must cite visible evidence.
- Claims must be paired with concrete fixes.
- Security, dependency, and public API changes need explicit justification.
- Templates may contain placeholders; shipped specs and docs should not.
