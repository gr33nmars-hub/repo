# Implementation Plan: Anti-AI Slop Control Plane

## Context

- Spec: `specs/000-anti-ai-slop-control-plane/spec.md`
- Existing reuse: current `SKILL.md`, `README.md`, review protocols, dimensions, checklists, templates, and research register.
- Minimal solution rung: reuse existing review knowledge, add only the guardrail structure and executable validators needed by the requested pack.

## Technical Approach

- Add `.specify/memory` and `.specify/templates/overrides`.
- Add local agent skills and Codex prompts.
- Add stdlib Python validators under `tools/validators`.
- Add process and reference docs.
- Update README, SKILL routing, and manifest.

## Validation

- Compile Python files with `python -m compileall tools tests`.
- Run `python tools/validators/check_all.py --root . --format markdown`.
- Run `python -m unittest discover -s tests`.

## Risks

| Risk | Mitigation | Owner |
|---|---|---|
| Validator false positives on templates | Exclude template directories from placeholder checks | Maintainer |
| Drift between Markdown rules and validators | Keep README, SKILL, manifest, and sample spec in validation scope | Maintainer |
| Overwriting user files during migration | Keep apply helper explicit with `dry-run` and `merge` modes | Maintainer |
