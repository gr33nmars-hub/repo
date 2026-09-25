# Review Report Template

Use this template when the user asks for critique, audit, QA, or design review.

```md
# Output Design Review

## Verdict

[One to three sentences: readiness, main issue, main fix.]

## Output contract

| Field | Assessment |
|---|---|
| Audience |  |
| Job to be done |  |
| Medium |  |
| Success condition |  |
| Main constraint |  |

## Scores

| Area | Score | Notes |
|---|---:|---|
| Purpose fit | /5 |  |
| Specificity | /5 |  |
| Credibility / evidence | /5 |  |
| Structure / hierarchy | /5 |  |
| Voice / brand fit | /5 |  |
| Modality QA | /5 |  |
| Generic / AI-smell risk | Low / Medium / High / Critical |  |
| Readiness | Ship / Revise before delivery / Block |  |

## Signal clusters

| Visible evidence | Signal category | False-positive check | Contract impact | Fix direction |
|---|---|---|---|---|
|  |  |  |  |  |

## Before / after revision plan

| Target | Before | Revision instruction | After / example | Verification criterion |
|---|---|---|---|---|
|  |  |  |  |  |

## Priority findings

### P1 — [Issue]
- Evidence:
- Why it matters:
- Fix:
- Example revision:
- Confidence:

### P2 — [Issue]
- Evidence:
- Why it matters:
- Fix:
- Example revision:
- Confidence:

## Recommended revision order

1. [Highest leverage fix]
2. [Second fix]
3. [Polish]

## Acceptance criteria

- [ ] The output names the target user or audience.
- [ ] The first section/screen/slide communicates the real job.
- [ ] Generic phrases are replaced with concrete mechanisms.
- [ ] Claims are sourced, qualified, or removed.
- [ ] Signal clusters were checked against false positives before being reported.
- [ ] Every accepted AI-smell issue has a concrete revision and verification criterion.
- [ ] Medium-specific risks are addressed, including UI, slide, visual, code, data/chart, localization, or operational-plan issues when relevant.
- [ ] Next action is explicit.
```
