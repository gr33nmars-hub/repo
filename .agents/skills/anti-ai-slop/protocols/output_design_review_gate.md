# Universal Output Design Review Gate

Use this gate for every output before modality-specific review.

## Gate 1 — Purpose fit

Ask:

- What job is the output performing?
- Does the first screen, first paragraph, first slide, or first function make that job clear?
- Does the output optimize for action, understanding, persuasion, trust, usability, or implementation as required?

Red flags:

- broad setup before the actual point;
- “overview” structure when the user needs a decision;
- decorative polish that does not improve comprehension;
- no clear next action.

## Gate 2 — Audience fit

Ask:

- Who is this for?
- What does the audience already know?
- What objections, fears, constraints, or evaluation criteria matter to them?
- Is the language too generic, too formal, too casual, or too abstract for them?

Red flags:

- no industry, role, product, or context markers;
- equal explanations for obvious and non-obvious points;
- tone copied from generic SaaS, academic, or support templates.

## Gate 3 — Specificity

Ask:

- Could this output apply unchanged to many unrelated products, companies, or topics?
- Are there concrete nouns, verbs, constraints, examples, dates, systems, people, scenes, or data points?
- Does each section contain information that could not be guessed from the title alone?

Red flags:

- “streamline,” “empower,” “seamless,” “robust,” “comprehensive,” “innovative” without mechanism;
- generic metrics without source or context;
- feature lists that do not map to user tasks.

## Gate 4 — Evidence and claims

Ask:

- Which claims need proof?
- Are statistics, comparisons, quotes, or examples sourced or verifiable?
- Are assumptions labeled?
- Does the strength of the claim match the available evidence?

Red flags:

- fabricated-looking percentages;
- “studies show” without citation;
- superlatives without basis;
- code or design claims without tests, constraints, or validation.

## Gate 5 — Structure and rhythm

Ask:

- Does the structure follow the problem, or does it follow a default template?
- Are sections meaningfully different in length, weight, and purpose?
- Is the number of items functional or arbitrary?

Red flags:

- repeated 3-part, 4-step, or 6-card structures;
- every paragraph has the same cadence;
- every slide has the same layout;
- every feature card has the same icon-heading-copy pattern.

## Gate 6 — Voice and judgment

Ask:

- Does the output make a choice?
- Does it reveal priority, tradeoff, or editorial judgment?
- Does the voice fit the author or brand?

Red flags:

- no stance;
- excessive caveats;
- inspirational but content-light conclusion;
- safe and polished language that avoids the actual decision.

## Gate 7 — Accessibility and usability

Ask:

- Can the intended audience actually use this output?
- For UI or slides, are contrast, hierarchy, spacing, states, and interaction clear?
- For writing, is scanning easy without reducing meaning?
- For code, are errors, edge cases, and integration assumptions handled?

Red flags:

- low contrast;
- motion without purpose;
- small type in presentation or UI;
- inaccessible component state;
- code without error paths or tests.

## Gate 8 — Final actionability

Ask:

- What should the reader, viewer, user, reviewer, or developer do next?
- Is the next step visible and specific?
- Are success criteria stated?
- For plans, specs, or recommendations: who owns the next action, by when, with what dependency, approval path, rollback, and acceptance criterion?

Red flags:

- “learn more” or “get started” without a concrete path;
- report ends with “more research is needed” but no decision;
- code snippet has no integration instructions;
- deck ends with “Questions?” but no ask.
- operational plan has plausible phases but no owner, date, dependency, budget, risk trigger, or rollback.

## Gate 9 — Evidence-to-revision discipline

Ask:

- Did each AI-smell or generic-output finding cite visible evidence?
- Did the review check whether the pattern is justified by the contract?
- Did every accepted issue include a concrete repair and verification criterion?
- Is any missing context named instead of guessed?

Red flags:

- critique uses “generic,” “AI-like,” or “template-like” without evidence;
- finding names a common convention, font, layout, or phrase without explaining contract impact;
- fix says “make it more specific” but does not name the specificity input needed;
- revised output removes useful structure only to look less generated;
- review gives a score but no implementable next edit.

## Gate 10 — Localization and register fit

Ask:

- Is the language matched to the audience’s locale, formality level, and cultural context?
- Are dates, times, currency, units, addresses, names, examples, and legal/compliance references appropriate for the locale?
- For bilingual or translated output, is register consistent across languages?
- Does the output avoid translationese, idiom transfer, and generic “global audience” phrasing?

Red flags:

- US-centric examples in a non-US context without reason;
- mixed honorific/formality levels;
- English source syntax carried into another language;
- inconsistent date, currency, unit, or address formats;
- UI labels translated literally but not idiomatically.
