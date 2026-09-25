# Changelog

## Unreleased

- Replaced the README demo GIF with a static workflow SVG and actual command-output excerpts.
- Removed the README GIF generator from the maintained pack surface.

## 0.2.0 - 2026-06-25

- Added Spec Kit style guardrail pack structure, Codex prompts, validators, workflow examples, and sample feature evidence.
- Added fail-closed aggregate validation, config integrity checks, workflow integrity checks, evidence link checks, template token checks, and resource catalog freshness checks.
- Connected resource catalog freshness checks to the aggregate `check_all.py` release gate.
- Connected `manifest.txt` integrity checks to the aggregate `check_all.py` release gate.
- Added feature bootstrap, guardrail apply tooling, repository inventory JSON output, apply manifests, validation profiles, and dependency baseline checks.
- Hardened `apply_guardrails.py` so dry-run reports cannot mutate the target repository through target-contained output paths.
- Updated `apply_guardrails.py` reports and manifests to emit the pack `VERSION` as `tool_version`.
- Updated `apply_guardrails.py` to ignore generated cache artifacts in dry-run and merge copy plans.
- Updated `apply_guardrails.py` to use the maintained `manifest.txt` pack surface for migration plans.
- Added manifest-entry warnings and an apply-to-target validation test for `apply_guardrails.py`.
- Added a README demo GIF for the guardrail pack workflow.
- Added a stdlib-only README demo GIF generator so the binary asset is reproducible.
- Added `CLAUDE.md` and README guidance for Claude Code and other agent runtimes.
- Updated workflow examples and documented Semgrep version policy.

## 0.1.0 - 2026-06-05

- Initial anti-ai-slop skill with review workflow, dimensions, checklists, templates, and field-reported pattern guidance.
