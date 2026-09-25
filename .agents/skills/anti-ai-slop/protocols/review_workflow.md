# Review Workflow

Apply this workflow before final delivery or when explicitly asked to audit an output.

## 1. Define the output contract

Capture the minimum contract:

| Field | Question |
|---|---|
| Audience | Who will read, use, approve, or judge this output? |
| Job to be done | What action, belief, decision, or behavior should the output produce? |
| Medium | Is this text, UI, slide, visual, code, or a mixed artifact? |
| Constraints | Length, tone, brand, deadline, legal/compliance, accessibility, platform, file type |
| Evidence requirement | Does it need citations, data, screenshots, tests, references, or source links? |
| Success condition | What would count as a good output in practical terms? |

If the contract is missing and asking the user would slow progress, make the smallest reasonable assumption and state it briefly.

## 2. Classify the work purpose

Use `taxonomies/task_purpose_matrix.md`.

Select one dominant purpose and any secondary purposes. Do not over-review every possible dimension.

## 3. Run the universal design gate

Use `protocols/output_design_review_gate.md`.

This gate checks purpose-fit, specificity, evidence, structure, voice, accessibility, and actionability.

## 4. Run modality-specific review

Use only the relevant dimension files:

- Writing: `dimensions/writing_information.md`
- Reporting: `dimensions/academic_reporting.md`
- Marketing: `dimensions/marketing_brand.md`
- Emotional/social: `dimensions/emotional_social.md`
- UI/web: `dimensions/web_ui_design.md`
- Slides: `dimensions/presentation_decks.md`
- Visuals: `dimensions/images_visuals.md`
- Code: `dimensions/code_developer_outputs.md`
- Data/charts/dashboards: `dimensions/data_charts_dashboards.md`
- Localization/register: `dimensions/localization_register.md`
- Operational plans: `dimensions/operational_plans.md`

## 5. Identify signal clusters, not isolated quirks

A single pattern is rarely meaningful. Treat a pattern as significant when at least two of the following are true:

- It repeats across the output.
- It weakens the actual purpose.
- It replaces concrete context with generic language or decoration.
- It causes usability, credibility, accessibility, or maintainability risk.
- It resembles the default structure of generated outputs without a functional reason.

Before writing a finding, complete this evidence-to-revision worksheet for each meaningful signal cluster:

| Field | Required note |
|---|---|
| Visible evidence | Quote the phrase, describe the component, name the slide, cite the function, or identify the visual region. |
| Signal category | Use the global checklist or a modality file; do not invent a vague label like “feels AI.” |
| Repetition / cluster | State whether the signal appears once, repeats, or combines with other signals. |
| False-positive check | Explain why the pattern is not justified by audience, brand, genre, accessibility, or functional clarity. |
| Contract impact | Map the signal to the output contract: purpose, audience, evidence, usability, brand fit, or actionability. |
| Specificity input needed | Name the missing fact, example, source, product detail, user term, screenshot, test, or constraint needed to repair it. |
| Remediation pattern | Select the repair pattern or dimension-specific fix to apply. |
| Concrete revision | Provide replacement text, a component change, a slide edit, a visual prompt correction, or a code/test requirement. |
| Verification criterion | State how to confirm the fix: source added, CTA changed, state represented, test added, chart relabeled, etc. |

If the false-positive check passes, do not report the pattern as an AI-smell issue. You may still mention it as a normal design, accessibility, or editorial tradeoff if it affects the output.

## 6. Prioritize findings

Use `protocols/finding_format.md`.

Default severity:

| Severity | Meaning |
|---|---|
| P0 | Blocks delivery or creates factual, legal, security, accessibility, or trust risk |
| P1 | Significantly weakens purpose, credibility, conversion, usability, or clarity |
| P2 | Noticeable polish or differentiation issue |
| P3 | Optional refinement |

## 7. Recommend fixes

Use `checklists/remediation_patterns.md`.

Every finding should include a concrete fix. For writing and copy, provide example replacement text. For UI, provide component-level changes. For code, provide exact refactoring or test requirements.

Minimum fix standard:

| Output type | Minimum useful fix |
|---|---|
| Writing / copy | Replacement sentence, section outline, or before/after wording. |
| Reports / research | Claim qualification, source requirement, recommendation, or decision rule. |
| UI / web | Component-level change, state/accessibility requirement, or hierarchy adjustment. |
| Slides | Revised claim title, evidence placement, visual replacement, or final ask. |
| Visuals | Prompt/edit instruction tied to anatomy, text, physics, brand, or context. |
| Code | Validation, error handling, version check, integration assumption, or test requirement. |

## 8. Decide final response mode

Choose one:

| Mode | Use when |
|---|---|
| Review report | User asked for critique, audit, or QA |
| Revised output | User asked to improve, rewrite, redesign, or fix |
| Design addendum | User asked to add output design review considerations |
| Mixed | User needs both issues and a revised version |

## 9. Final delivery checklist

Before finalizing:

- Does the output directly solve the stated task?
- Did you avoid unsupported claims about AI authorship?
- Did you remove or justify generic patterns?
- Did you preserve useful clarity and structure?
- Are fixes specific enough to implement?
- Are assumptions explicit when important?
