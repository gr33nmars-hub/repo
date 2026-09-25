# Feature Specification: Anti-AI Slop Control Plane

## Output Contract

- Audience: Codex users and maintainers applying anti-slop guardrails.
- Job to be done: provide spec-first review, implementation, and validation gates.
- Medium: Markdown policy files plus Python validators.
- Constraints: standard-library Python, no authorship claims, no destructive default behavior.
- Success condition: a repository can run one command and receive actionable coherence findings.

## Requirements

### Functional Requirements

- FR-001: The pack must define durable principles under `.specify/memory/`.
- FR-002: The pack must provide Codex prompts for applying, validating, and reviewing the guardrails.
- FR-003: The pack must provide validators for task traceability, spec coverage, glossary use, architecture boundaries, dependency justification, vague language, and placeholders.
- FR-004: The pack must provide process docs and checklists for migration, validation, release, security, dependency, and PR review.
- FR-005: The pack must preserve the original anti-ai-slop review skill behavior.

### Coherence Requirements

- CR-001: Every task in `tasks.md` must reference at least one `FR-*` ID.
- CR-002: Validator reports must include severity, rule, path, message, and fix.
- CR-003: No validator may mutate repository content.

## Acceptance Criteria

- AC-001: `python tools/validators/check_all.py --root . --format markdown` exits successfully for this repo.
- AC-002: `python -m compileall tools` exits successfully.
- AC-003: README documents both skill usage and guardrail pack usage.

## Out of Scope

- AI authorship detection.
- Automatic dependency installation.
- Automatic destructive migration.
