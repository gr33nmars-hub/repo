# Task Purpose Matrix

Use this matrix to classify the output by the job it is trying to perform. Review patterns only after the purpose is clear.

| Work purpose | Typical output | Common generic / AI-smell pattern | Review question | Primary fix |
|---|---|---|---|---|
| Inform quickly | Summary, explainer, manual, onboarding note | Over-structured sections, excessive bullets, broad opening, obvious definitions | Does the output help the reader act faster, or does it merely look organized? | Start with the actual decision, constraint, or user problem. Remove obvious setup. |
| Look professional | Report, memo, research note, executive brief | Formal abstract wording, passive neutrality, over-balanced paragraphs, weak judgment | Does professionalism hide the actual recommendation? | Add decision criteria, tradeoffs, confidence level, and concrete recommendation. |
| Persuade or sell | Landing page, ad copy, sales one-pager, pitch | “Not just X but Y,” “unlock,” “supercharge,” “seamless,” vague transformation claims | Does the copy state a specific user, pain, mechanism, and outcome? | Replace generic benefits with product-specific verbs, workflows, proof, and objections. |
| Sound helpful and safe | FAQ, support reply, chatbot answer, policy note | Too many caveats, “it depends,” equal weighting, no priority | Does the reader know what to do next? | Give a default recommendation, then state exceptions. |
| Create insight or emotion | Essay, social post, founder note, thought leadership | Aphoristic sentences, polished vulnerability, lesson-like ending | Does the piece contain lived detail, real tension, or a specific scene? | Add concrete memory, conflict, detail, and unresolved nuance. |
| Look like modern SaaS | Website, app UI, product prototype | Inter/Geist-style typography, pill badge, blinking dot, purple gradient, uniform feature cards | Do visual choices encode meaning or only signal “tech product”? | Tie visual elements to product state, hierarchy, brand, and interaction purpose. |
| Present clearly | Slide deck, pitch deck, lecture material | Three bullets per slide, generic icons, glossy 3D objects, weak CTA | Does each slide support a talk track, decision, or memory hook? | Give every slide one job, one message, and a visible evidence path. |
| Ship code quickly | Script, PR, generated UI, integration snippet | Plausible boilerplate, hardcoded values, generic error handling, missing edge cases | Does the code respect the local system, data model, and failure modes? | Add real inputs, explicit errors, tests, security checks, and integration assumptions. |
| Create visuals | Hero image, ad visual, thumbnail, concept art | Over-polished skin, broken text, impossible anatomy, repeated background patterns | Does the visual support the message without artifact distraction? | Inspect details, simplify prompt/design, remove broken text, align lighting and context. |
| Show data | Dashboard, chart, analytics slide, KPI report | Decorative chart, fake sample data, over-precise metric, missing axis/source/definition | Does the visualization support a real decision or only signal analytics polish? | Define metric, source, scope, denominator, time period, and decision implication. |
| Localize or translate | Multilingual UI, translated copy, regional report | Translationese, wrong locale format, mixed register, generic “global” phrasing | Does this sound native to the audience and respect local conventions? | Fix register, locale formats, culturally specific examples, and terminology consistency. |
| Plan operations | Roadmap, implementation plan, launch checklist, strategy spec | Plausible phases without owner, date, dependency, approval, fallback, or acceptance criteria | Could a team execute this without asking what happens next? | Add owner, deadline, dependency, risk trigger, rollback, budget/constraint, and acceptance test. |

## Classification rule

If an output has multiple purposes, choose the dominant purpose by asking:

> What would make this output fail in front of its intended audience?

Examples:

- A landing page with technical diagrams is still primarily persuasion if its failure mode is weak conversion.
- A report with a polished cover is still primarily professional decision support if its failure mode is weak recommendation.
- A UI prototype with marketing copy is primarily interface design if its failure mode is usability confusion.

## False-positive rule

The matrix names common patterns, not automatic defects. Do not flag a pattern when it is justified by the output contract, brand system, teaching goal, executive scanning need, accessibility requirement, or technical convention. Report it only when it weakens purpose, specificity, credibility, usability, or actionability.
