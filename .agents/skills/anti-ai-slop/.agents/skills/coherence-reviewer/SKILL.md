---
name: coherence-reviewer
description: Review a repo for requirement, task, glossary, architecture, dependency, vague-language, and placeholder coherence.
---

# Coherence Reviewer

Use this workflow before merging guardrail, spec, or validator changes.

## Inputs

- `.specify/memory/*`
- `specs/**/spec.md`
- `specs/**/plan.md`
- `specs/**/tasks.md`
- `docs/process/*`
- `tools/validators/*`

## Checks

- Every task references a requirement.
- Glossary terms are used consistently.
- Architecture boundaries are respected.
- Dependency additions have recorded justification.
- Placeholder text is not present outside templates.
- Vague language is either removed or backed by evidence.
