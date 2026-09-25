# Finding Format and Scoring

Use this protocol when producing a review report or internal audit.

## Default finding block

```md
### P1 — Issue title
- Evidence: Quote or describe the exact visible pattern.
- Why it matters: Explain how it affects purpose, credibility, usability, conversion, trust, accessibility, or maintainability.
- Fix: Give a concrete change.
- Example revision: Provide replacement wording, layout change, or implementation direction when possible.
- Confidence: High / Medium / Low.
```

## Severity scale

| Severity | Label | Use when |
|---|---|---|
| P0 | Delivery blocker | Factual error, fabricated claim, legal/compliance risk, security issue, broken interaction, inaccessible core flow, unreadable artifact |
| P1 | Major purpose-fit issue | Generic positioning, weak recommendation, missing audience context, misleading hierarchy, unsupported core claim, serious usability flaw |
| P2 | Quality issue | Repetition, bland phrasing, decorative UI, weak examples, over-balanced wording, inconsistent visual rhythm |
| P3 | Polish issue | Minor wording, small layout improvement, optional differentiation, style preference |

## Generic / AI-smell risk

Do not score “probability of AI generation.” Score **generic-output risk**.

| Risk level | Definition |
|---|---|
| Low | One isolated pattern with no major impact |
| Medium | Multiple generic patterns, but the output remains usable |
| High | Repeated generic patterns replace context, judgment, proof, or meaningful design |
| Critical | Generic patterns combine with false claims, broken UI, inaccessible design, or unsafe code |

## Score anchors

Use `/5` scores only when a score will help prioritize revision. A lower score should point to a concrete edit, not a vague quality judgment.

| Score | Anchor |
|---:|---|
| 5 | Purpose-built, evidence-aware, and ready for the stated audience with only optional polish. |
| 4 | Strong fit with one or two contained issues that can be fixed without restructuring. |
| 3 | Usable draft, but important specificity, evidence, hierarchy, or modality gaps remain. |
| 2 | Major revision needed because generic patterns or missing context weaken the core job. |
| 1 | Not deliverable; the output is misleading, unusable, unsupported, inaccessible, unsafe, or mostly template residue. |

Apply the anchors to these areas:

| Area | Score question |
|---|---|
| Purpose fit | Does the output perform the actual job instead of the average version of the job? |
| Specificity | Could this be reused for unrelated users, brands, products, or contexts with minimal edits? |
| Credibility / evidence | Are claims sourced, qualified, testable, or visibly grounded in the artifact? |
| Structure / hierarchy | Does the structure follow priority and workflow rather than a default template? |
| Voice / brand fit | Does the tone match the author, brand, audience, and stakes? |
| Modality QA | Does the medium-specific surface work: UI states, chart labels, slide job, image realism, code failure paths, etc.? |

## Readiness thresholds

| Readiness | Use when |
|---|---|
| Ship | No P0/P1 findings; average score is at least 4; AI-smell risk is Low or Medium with clear justification. |
| Revise before delivery | Any P1 finding, any area score of 2 or 3, or AI-smell risk is High without safety/security/factual blockers. |
| Block | Any P0 finding, Critical AI-smell risk, fabricated evidence, broken core interaction, inaccessible core flow, unsafe code, or unsupported compliance/security claim. |

When risk and score disagree, follow the risk. For example, a polished deck with strong structure still blocks if it contains fabricated metrics or fake source citations.

## Confidence labels

| Confidence | Meaning |
|---|---|
| High | Evidence is visible and directly linked to the output's purpose |
| Medium | Pattern is visible, but impact depends on audience or context |
| Low | Weak signal; mention only as optional consideration |

## Review tone

Use direct, evidence-based wording:

- Good: “The hero line is generic because it does not name the workflow, user, or outcome.”
- Good: “The blinking dot reads as decorative because no live state, notification, or status is attached to it.”
- Avoid: “This was clearly AI-generated.”
- Avoid: “This feels soulless” unless translated into specific evidence.

## Minimum useful review

For short outputs, provide:

1. One-sentence verdict.
2. Top 3 issues.
3. Concrete fixes.
4. Revised example when possible.

## Deep review

For high-stakes outputs, include:

- purpose-fit score;
- specificity score;
- evidence score;
- design/usability score;
- Generic / AI-smell risk level;
- recommended revision order;
- acceptance criteria.
