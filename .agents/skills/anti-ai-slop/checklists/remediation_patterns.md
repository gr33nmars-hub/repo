# Remediation Patterns

Use these repairs after identifying generic or AI-scented patterns.

## 1. Replace abstract value with concrete mechanism

| Weak pattern | Better direction |
|---|---|
| “Supercharge your workflow.” | Name the workflow and the measurable improvement. |
| “A seamless solution for modern teams.” | State what task is made easier and how. |
| “Unlock the power of data.” | Name the data source, user decision, and output. |
| “AI-powered productivity platform.” | Name the user, input, transformation, and result. |

Example:

```text
Before: Supercharge your customer support workflow.
After: Turn support-call transcripts into QA-ready coaching notes in under 3 minutes.
```

## 2. Cut generic openings

| Weak opening | Repair |
|---|---|
| “In today’s fast-paced world...” | Start with the specific problem or decision. |
| “As technology continues to evolve...” | Name the actual technology shift and consequence. |
| “X is becoming increasingly important...” | State who needs X and what happens without it. |

Example:

```text
Before: In today’s fast-paced world, teams need better tools to collaborate.
After: Product managers lose the thread when user interviews, Jira tickets, and Slack decisions live in separate systems.
```

## 3. Add editorial judgment

Convert neutral summaries into useful recommendations.

| Generic summary | Purpose-built recommendation |
|---|---|
| “Both options have pros and cons.” | “Choose Option B unless latency under 200ms is mandatory.” |
| “Further research is needed.” | “Run a 2-week pilot with 20 accounts before committing engineering time.” |
| “This depends on the context.” | “Default to X for small teams; switch to Y after the second approval layer appears.” |

## 4. Make structure uneven when reality is uneven

Do not force every section to have the same length. Give more space to the factor that drives the decision.

Use:

- short notes for obvious points;
- longer sections for tradeoffs and risks;
- clear priority order;
- explicit “most important” labels when useful.

## 5. Replace decorative UI with semantic UI

| Pattern | Review question | Repair |
|---|---|---|
| Blinking dot | What state is blinking? | Use only for live, recording, sync, notification, or active status. Add label and accessible state. |
| Gradient text | What distinction does the gradient encode? | Use brand color, emphasis, or remove it. |
| Six feature cards | Are all six equally important? | Merge, rank, or convert to workflow steps. |
| Icon tile | Does the icon clarify the concept? | Replace with product screenshot, state diagram, or example output. |
| Hover bounce | What feedback does it provide? | Use stateful interaction: focus, selected, loading, disabled, expanded. |

## 6. Ground emotional writing

| Weak pattern | Repair |
|---|---|
| Aphorism | Add a scene, person, object, time, or conflict. |
| Polished vulnerability | Include one concrete imperfection or unresolved tension. |
| Lesson ending | End with a decision, image, or consequence. |

Example:

```text
Before: Growth is not about speed. It is about direction.
After: I kept refreshing the dashboard even after we knew the campaign had failed. The mistake was not the budget. It was that nobody owned the first sentence users saw.
```

## 7. Repair unsupported claims

For every statistic or comparison:

- add source, date, definition, and scope;
- weaken the claim if evidence is limited;
- remove the number if it exists only for authority;
- convert to a testable hypothesis when evidence is not available.

## 8. Repair generated code

- Replace hardcoded placeholders with configuration.
- Add explicit input validation.
- Handle empty, null, malformed, and unauthorized cases.
- Confirm package and API versions.
- Add tests for failure paths, not only success paths.
- State integration assumptions.
- Remove comments that explain syntax rather than business rules.

## 9. Reduce “template scent” without reducing clarity

Do not remove structure just to look human. Instead:

- vary section lengths based on importance;
- use fewer, sharper headings;
- replace generic headings with task-specific headings;
- add concrete examples;
- remove duplicated lead-ins;
- use the user’s terminology;
- keep tables only where comparison is the real task.
