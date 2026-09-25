# Dimension Review: Operational Plans

Use for roadmaps, launch plans, implementation plans, migration plans, project specs, rollout checklists, and strategy-to-execution documents.

## Purpose

Operational plans should make execution possible. They should not only present plausible phases or confident sequencing.

## Common generic / AI-smell patterns

| Pattern | Visible sign | Risk |
|---|---|---|
| Plausible phase list | Discovery → build → launch → optimize with no real constraints | Looks complete but cannot be executed |
| Ownerless action | Tasks use passive voice or “team will” without role or accountable owner | No one can act or be held responsible |
| Deadline blur | “soon,” “next phase,” “ongoing,” or no date/timebox | Prevents prioritization and coordination |
| Dependency omission | Plan ignores approvals, data access, procurement, legal, design, security, or migration blockers | Causes surprise delays |
| No failure trigger | Plan lacks rollback, stop condition, escalation path, or risk threshold | Makes recovery ad hoc |
| Acceptance theater | “completed successfully” without measurable acceptance criteria | Hides quality and readiness gaps |
| Budget/resource silence | No staffing, cost, capacity, tool, or review constraint | Makes the plan aspirational |

## Review checklist

- Who owns each workstream or decision?
- What date, timebox, or sequence constraint governs each step?
- What dependencies must be satisfied before work starts?
- What approval path, compliance review, or stakeholder signoff is required?
- What risk trigger changes the plan?
- What rollback, fallback, or escalation path exists?
- What acceptance criterion proves the work is done?
- What resource, budget, staffing, or capacity constraint matters?

## Repair patterns

| Weak pattern | Better direction |
|---|---|
| “Phase 1: research and planning” | Name owner, output, due date, source inputs, and decision gate. |
| “Launch when ready” | Define readiness checklist, blocker threshold, and accountable approver. |
| “Monitor performance” | Name metric, owner, cadence, threshold, and action if the threshold is crossed. |
| “Mitigate risks” | Tie each risk to trigger, prevention, fallback, and escalation owner. |
| “Improve adoption” | Define target cohort, training path, usage metric, support owner, and review date. |

## Acceptance criteria

- Each major action has owner, deadline/timebox, dependency, and acceptance criterion.
- Risks have triggers and response paths.
- Approvals and constraints are visible.
- The plan distinguishes assumptions from committed work.
- A team could execute the next step without asking what happens next.
