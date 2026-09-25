# Output Design Addendum Checklist

Use this file when the user asks to add output design review considerations to a deliverable.

The addendum can be internal, appended to the final answer, or delivered as a separate review section depending on the task.

## Minimal addendum

Use for short outputs.

```md
## Output Design Review

- Purpose fit: [Does the output perform the intended job?]
- Specificity: [What makes this fit the target audience/context?]
- Credibility: [Which claims need evidence or qualification?]
- AI-smell risk: [Which generic patterns were removed or intentionally kept?]
- Final action: [What should the reader/user do next?]
```

## Standard addendum

Use for drafts, landing pages, reports, UI concepts, and decks.

```md
## Output Design Review

| Area | Check | Decision |
|---|---|---|
| Purpose | Does the output solve the actual job rather than look generally polished? |  |
| Audience | Is the language, depth, and visual hierarchy matched to the recipient? |  |
| Specificity | Are user, context, workflow, constraints, examples, or data concrete enough? |  |
| Evidence | Are factual claims, metrics, and comparisons sourced or qualified? |  |
| Structure | Is the structure functional rather than a default 3-step / 6-card pattern? |  |
| Voice / brand | Does this sound owned by the author or brand? |  |
| Modality QA | Are writing, UI, slide, visual, code, data/chart, localization, or operational-plan risks checked as relevant? |  |
| AI-smell risk | Are generic phrases, decorative design, and over-smoothed rhythm reduced? |  |
| Next action | Is the intended next step explicit? |  |
```

## Deep addendum

Use for high-stakes or client-facing work.

```md
## Output Design Review

### 1. Output contract
- Audience:
- Job to be done:
- Medium:
- Constraints:
- Success condition:

### 2. Review verdict
- Overall readiness:
- Main risk:
- Recommended revision order:

### 3. Findings
| Priority | Issue | Evidence | Fix |
|---|---|---|---|
| P1 |  |  |  |
| P2 |  |  |  |

### 4. Generic / AI-smell risk assessment
- Risk level: Low / Medium / High / Critical
- Main pattern cluster:
- Patterns intentionally kept:
- Patterns removed or revised:

### 5. Acceptance criteria
- [ ] The output names the real audience or user.
- [ ] The first section/screen/slide states the actual job.
- [ ] Generic claims are replaced with concrete mechanisms or proof.
- [ ] Visual or structural elements have a functional reason.
- [ ] Data/chart, localization/register, or operational-plan risks are checked when relevant.
- [ ] Factual claims are sourced, qualified, or removed.
- [ ] Next action is explicit.
```

## When not to append an addendum

Do not append a visible addendum when:

- the user asked for final copy only;
- the output would become awkward or too long;
- the addendum would expose internal review steps unnecessarily;
- the artifact format does not allow extra commentary.

In those cases, apply the addendum internally and deliver the cleaned output.
