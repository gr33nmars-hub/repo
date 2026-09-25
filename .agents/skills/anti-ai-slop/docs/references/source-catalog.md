# Source Catalog

This pack is shaped by these source families:

- Spec-first development: spec, plan, tasks, implement.
- Codex repository guidance: `AGENTS.md` and reusable local workflows.
- AI-generated code review practice: test first, then static analysis, dependency review, context review, and AI-specific pitfall checks.
- Anti-slop pattern libraries: visible-output heuristics, false-positive notes, and concrete remediation patterns.

Keep new source claims in this file or `resource-catalog.yaml`. Resource catalog entries must include `verified_at`, `maintenance_status`, and `license_checked`; `python tools/validators/check_all.py --root . --profile pack-self` includes this freshness gate. You can also run `python tools/resource_catalog_freshness.py --root .` for a focused report.

Validator configuration uses a constrained stdlib YAML subset by design: top-level `key: value`, inline lists, and block lists for list fields. Use JSON for nested guardrail profiles or other nested configuration.

`tools/validators/check_all.py` supports scan profiles: `pack-self` for the full guardrail pack, `target-repo` for service-code-oriented paths, `feature` for a selected `specs/FEATURE/` directory, and `ci-strict` for CI gating. `config/guardrails.local.json` overlays are intentionally rejected until a merge strategy is implemented; use `--profile` for local scan selection.

## Workflow Version Policies

Semgrep CLI version policy: `.github/workflows/semgrep.yml` intentionally installs the latest CLI so security rules and engine updates land quickly. Owners review monthly through the source catalog freshness process, and the workflow should pin during reproducibility incidents or when an upstream Semgrep change breaks CI.
