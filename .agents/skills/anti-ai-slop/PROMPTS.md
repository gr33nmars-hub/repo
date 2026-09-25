# Anti-AI Slop Prompt Collection

Use these prompts when you want a ready-to-run request for the `anti-ai-slop` skill. Replace bracketed placeholders with your artifact, audience, or constraints.

Each prompt assumes the skill should avoid authorship claims and focus on visible output quality, false positives, concrete fixes, and verification criteria.

## Review Prompts

```text
$anti-ai-slop Review the following [artifact type] for AI slop, generic-output patterns, unsupported claims, and weak purpose-fit. Give a verdict, signal clusters, priority findings, concrete fixes, and acceptance criteria.
```

```text
$anti-ai-slop Audit this [README/report/page/deck] for template-like structure, vague claims, proof-shaped unreliability, and missing audience specificity. Do not rewrite yet; produce a prioritized review report.
```

```text
$anti-ai-slop Run an evidence-to-revision review on this output. For each finding, include visible evidence, signal category, false-positive check, contract impact, fix, example revision, and verification criterion.
```

## Rewrite Prompts

```text
$anti-ai-slop Rewrite this [copy/document/section] so it sounds purpose-built, specific, credible, and less AI-scented. Preserve the intended meaning and list the main changes after the rewrite.
```

```text
$anti-ai-slop Remove generic throat-clearing, inflated diction, empty professionalism, and safe over-completion from this text. Keep useful structure and clarity.
```

```text
$anti-ai-slop Improve this output for [target audience]. Replace generic benefits with concrete mechanisms, proof, user terminology, and a specific next action.
```

## UI and Visual Prompts

```text
$anti-ai-slop Review this UI concept for SaaS-average design slop: decorative gradients, meaningless status badges, repeated card grids, fake metrics, weak hierarchy, and inaccessible states. Give component-level fixes.
```

```text
$anti-ai-slop Audit this landing page for AI-slop patterns in copy, layout, visual hierarchy, trust claims, metrics, and CTA intent. Return a section-by-section revision plan.
```

```text
$anti-ai-slop Review this generated image or visual direction for synthetic polish, broken text, physics issues, context mismatch, generic AI tropes, and brand fit. Give edit instructions.
```

## Code and PR Prompts

```text
$anti-ai-slop Review this PR description and code snippet for generated-code slop: happy-path-only logic, fake APIs, missing tests, placeholder values, generic error handling, and weak ownership. Give maintainer-ready fixes.
```

```text
$anti-ai-slop Audit this technical documentation for buzzword layers, delayed setup instructions, hallucinated APIs, missing version assumptions, and non-reproducible examples.
```

```text
$anti-ai-slop Review this security or bug report for AI slop: unverifiable claims, nonexistent code paths, missing reproduction, fake precision, and unclear impact. Return what must be proven before triage.
```

## Data, Localization, and Planning Prompts

```text
$anti-ai-slop Review this dashboard or analytics mockup for data/chart slop: fake-looking sample data, missing metric definitions, impossible distributions, unreadable labels, and unsupported benchmarks.
```

```text
$anti-ai-slop Review this localized or bilingual output for translationese, locale-format errors, mixed register, inconsistent terminology, and cultural mismatch.
```

```text
$anti-ai-slop Review this implementation plan for operational slop: vague phases, missing owners, deadlines, dependencies, approval paths, rollback triggers, and acceptance criteria.
```

## Research-Aware Prompts

```text
$anti-ai-slop Use the field-reported AI-smell register to audit this artifact. Include only clustered patterns, label false-positive risks, and avoid authorship claims.
```

```text
$anti-ai-slop Compare this draft against field-reported AI slop patterns such as lexical inflation, generic throat-clearing, not-X-but-Y contrast, list abuse, tonal flatness, proof-shaped citations, and machine artifact leakage.
```

```text
$anti-ai-slop Create a compact anti-slop QA checklist for [team/project/artifact type] using the research register and the relevant dimension files.
```

## Template Prompts

```text
$anti-ai-slop Produce a review report using templates/review_report_template.md for this [artifact].
```

```text
$anti-ai-slop Produce a rewrite brief using templates/rewrite_brief_template.md. Include missing context, specificity inputs, pattern-to-revision matrix, and final deliverable.
```

```text
$anti-ai-slop Add a design review addendum using templates/design_review_addendum.md. Keep it short and focused on acceptance criteria.
```

