---
name: spec-first-anti-slop
description: Run a Spec Kit style anti-slop workflow from output contract to spec, plan, tasks, implementation evidence, and PR review.
---

# Spec-First Anti-Slop

Use this local workflow when a task needs traceable requirements and anti-slop validation.

## Steps

1. Read `.specify/memory/constitution.md`, `glossary.md`, and `architecture-principles.md`.
2. Draft or update `spec.md` before implementation.
3. Create a plan that names reuse candidates, dependencies, validation commands, and documentation targets.
4. Write tasks with requirement IDs and validation IDs.
5. Run `python tools/validators/check_all.py --root . --format markdown`.
6. Record evidence in the implementation log or PR description.

## Rule

Do not convert style suspicion into authorship claims.
