# Field-Reported AI-Smell Pattern Register

Use this file as a research-backed pattern register for output design review. It consolidates recurring “AI smell,” “AI slop,” and generic-output signals reported in public communities, GitHub repositories, style tools, and open-source maintainer discussions.

This file is an operational checklist, not an authorship detector. A pattern means: “this output contains a visible choice that commonly reduces credibility, specificity, or purpose-fit.” It does **not** mean: “this was written or designed by AI.”

Last reviewed: 2026-06-07

---

## 1. How to Use This Register

Use this file after the normal output-design gate when the task asks for one of the following:

- reducing AI-smell, slop, genericness, template feel, or chatbot voice;
- reviewing public-facing writing, landing pages, documentation, reports, decks, code, PRs, or generated visuals;
- creating a lint checklist, acceptance criteria, editorial QA pass, or style guide;
- recording new recurring patterns discovered during review.

Run the review in this order:

1. Identify the output purpose and audience.
2. Select the relevant modality file under `dimensions/`.
3. Use this register to check whether the output also shows field-reported patterns.
4. Cluster findings. Do not flag isolated words unless they form a pattern or undermine the task.
5. Pair every finding with a concrete revision rule.

---

## 2. Evidence Labels

Use these labels when adding or citing a pattern inside a review note.

| Label | Meaning | Reliability for review |
|---|---|---|
| `R-COMMUNITY` | Reddit, Hacker News, forum, or social-web pattern reports | Useful for field language and emerging tells; noisy and subjective |
| `G-OSS` | GitHub repo, style package, linter, skill, detector, or maintainer policy | Useful for operationalization and repeatable rule design |
| `M-METRIC` | Scoring, stylometry, regex, n-gram, or measurement tool | Useful for repeatability; still not a forensic detector |
| `N-INDUSTRY` | News or maintainer incident showing operational harm | Useful for code, bug reports, PR hygiene, and disclosure policy |
| `D-DICTIONARY` | Dictionary or language authority documenting term adoption | Useful for terminology, not for detection |
| `A-ACADEMIC` | Paper, preprint, technical report, or formal study | Useful for empirical framing; check scope and domain |

When in doubt, mark the evidence as `R-COMMUNITY` and keep the confidence low.

---

## 3. High-Level Pattern Families

| Family | Main symptom | Typical output purpose affected | Review action |
|---|---|---|---|
| Lexical inflation | Fancy, over-polished words where plain words would work | Writing, reports, marketing, README | Replace with concrete verbs and task nouns |
| Generic throat-clearing | Broad openers before the actual point | Explainers, blogs, academic intros, landing pages | Start with the claim, fact, user problem, or decision |
| Rhetorical crutches | Reused contrast templates and faux insight structures | Marketing, essays, social posts, reports | Rebuild the sentence around the actual claim |
| Structural symmetry | Equal sections, 3-item lists, balanced pros/cons regardless of substance | Reports, slides, docs, UI sections | Weight sections by importance and evidence |
| List abuse | Bullets substitute for reasoning or prose | Chat responses, docs, assignments, decks | Convert weak lists into explanation, examples, or a table |
| Tonal flatness | Safe, balanced, complete, helpful, and anonymous voice | Public writing, executive comms, essays | Add point of view, stakes, names, constraints, and tradeoffs |
| Pseudo-depth | Fancier restatement plus obvious considerations | Thought leadership, essays, strategy notes | Add data, counterexample, source, edge case, or lived constraint |
| Proof-shaped unreliability | Fake or mismatched citations, invented claims, unverifiable precision | Academic, legal, research, bug reports | Verify sources; remove unsupported specificity |
| UI slop | Modern SaaS average aesthetic without product reason | Websites, apps, design systems | Tie visual choices to hierarchy, state, brand, and interaction |
| Code/PR slop | Unowned generated code, fake APIs, missing tests, non-reproducible reports | Code, GitHub issues, bug bounty reports | Require disclosure, reproduction, tests, and maintainer-ready evidence |
| Machine artifact leakage | Tool signatures copied into output | Any published artifact | Strip or rewrite immediately; treat as high-confidence quality failure |

---

## 4. Pattern Register

### P01 — Lexical Inflation Cluster

**Evidence labels:** `R-COMMUNITY`, `G-OSS`, `M-METRIC`

**Observed forms**

- Over-formal verbs: `delve`, `utilize`, `leverage`, `facilitate`, `elucidate`, `embark`, `endeavor`, `encompass`.
- Over-grand nouns: `tapestry`, `landscape`, `realm`, `paradigm`, `ecosystem`, `framework`, `symphony`, `crucible`.
- Over-significance adjectives: `pivotal`, `crucial`, `robust`, `comprehensive`, `multifaceted`, `nuanced`, `commendable`, `meticulous`, `intricate`.

**Why it smells generic**

The output tries to look sophisticated before it earns specificity. The words are not wrong individually. The risk appears when many of them appear near each other, especially in low-stakes or concrete tasks.

**False positives**

- Legal, policy, academic, or technical contexts where terms have domain-specific meanings.
- Brand voice that intentionally uses elevated language.
- Historical or literary writing.

**Review move**

Replace one abstract word with one concrete actor, action, object, constraint, or result.

```md
Weak: This framework leverages a multifaceted approach to streamline collaboration.
Better: The review queue assigns each draft to one editor and blocks publishing until sources are checked.
```

---

### P02 — Generic Throat-Clearing

**Evidence labels:** `R-COMMUNITY`, `G-OSS`

**Observed forms**

- `In today's rapidly evolving landscape...`
- `In the modern digital era...`
- `It is important to note that...`
- `It is worth mentioning that...`
- `When it comes to...`
- `In this article, we will explore...`
- `As we can see...`
- `At the end of the day...`

**Why it smells generic**

The opening delays the actual answer and creates a reusable preface that could fit almost any topic.

**False positives**

- Educational writing for novice readers where framing is useful.
- Legal or compliance text that must explicitly flag limitations.

**Review move**

Delete the frame and start with the content.

```md
Weak: In today's fast-paced digital world, password hygiene is more important than ever.
Better: Rotate shared admin passwords today; three current contractors still have access.
```

---

### P03 — “Not X, But Y” Contrast Crutch

**Evidence labels:** `R-COMMUNITY`, `G-OSS`, `M-METRIC`

**Observed forms**

- `It is not just X; it is Y.`
- `This is not merely X, but Y.`
- `Not only does it X, it also Y.`
- Cross-sentence contrast: `This is not about speed. It is about control.`

**Why it smells generic**

The pattern simulates insight by negating a weaker claim and replacing it with a grander one. It often appears in hooks, social posts, marketing copy, and conclusion paragraphs.

**False positives**

- True conceptual distinction where the contrast is necessary.
- Legal, philosophical, or analytical writing where scope is being narrowed.

**Review move**

State the actual claim directly, then prove it.

```md
Weak: This is not just a dashboard; it is a command center for your team.
Better: The dashboard lets dispatchers reassign drivers, message customers, and close delayed orders from one screen.
```

---

### P04 — Rhetorical Question Followed by Immediate Answer

**Evidence labels:** `R-COMMUNITY`

**Observed forms**

- `The question is: how do we solve it? The answer lies in...`
- `Why does this matter? Because...`
- `What makes this different? It starts with...`

**Why it smells generic**

It performs conversational pacing without real uncertainty. The question is often decorative and the answer is predictable.

**False positives**

- FAQs, teaching material, debate formats, landing pages with real user objections.

**Review move**

Use a real user objection, or remove the question.

```md
Weak: Why does onboarding matter? Because it sets the tone for success.
Better: New reps leave during week three, when they first handle live objections without a manager nearby.
```

---

### P05 — Topic-Sentence Machine

**Evidence labels:** `G-OSS`, `R-COMMUNITY`

**Observed forms**

Every paragraph follows the same rhythm:

```text
Topic sentence → broad explanation → generic example → therefore/conclusion sentence
```

**Why it smells generic**

The structure feels complete, but every paragraph carries the same amount of pressure. Nothing feels discovered, contested, or prioritized.

**False positives**

- Beginner textbooks.
- Rubric-driven school writing.
- Standardized compliance documentation.

**Review move**

Vary paragraph jobs: claim, evidence, exception, anecdote, procedure, warning, decision.

---

### P06 — Symmetry Addiction

**Evidence labels:** `G-OSS`, `R-COMMUNITY`

**Observed forms**

- Exactly 3 benefits, 3 risks, 3 examples.
- Equal paragraph lengths.
- Every section has the same number of bullets.
- Balanced `pros and cons` treatment even when one side is clearly stronger.

**Why it smells generic**

The output optimizes for visual balance rather than decision value. Real problems are lumpy.

**False positives**

- Slides, executive summaries, and classroom handouts where imposed symmetry improves comprehension.

**Review move**

Make the structure match importance. Allow one section to be long and another to be one sentence.

---

### P07 — List Abuse and Markdown Over-Formatting

**Evidence labels:** `R-COMMUNITY`, `G-OSS`

**Observed forms**

- Bullet points in casual conversation.
- Bullets where a single sentence would work.
- Repeated `**Topic:** explanation` listicle format.
- Nested lists three or more levels deep.
- Each bullet starts with the same verb: `Ensures`, `Provides`, `Enables`, `Supports`.

**Why it smells generic**

The structure creates scannability but hides weak reasoning. It can make a short answer look artificially complete.

**False positives**

- Checklists, specs, release notes, command references, issue templates.

**Review move**

Keep bullets only when order, comparison, or actionability matters.

---

### P08 — Transition Word Addiction

**Evidence labels:** `R-COMMUNITY`, `G-OSS`

**Observed forms**

- `Moreover`, `Furthermore`, `Additionally`, `Consequently`, `Nevertheless`, `Importantly`, `Notably`, `Ultimately`.
- Paragraphs chained by formal connectors instead of subject continuity.

**Why it smells generic**

The text signals logical flow instead of creating it. The reader sees connective tissue, not reasoning.

**False positives**

- Academic prose, legal analysis, policy memos, multilingual writing where explicit connectors are normal.

**Review move**

Start the next sentence with the real subject or action.

---

### P09 — Hedge Parade and Safety Blur

**Evidence labels:** `G-OSS`, `R-COMMUNITY`

**Observed forms**

- `may`, `might`, `could`, `can potentially`, `in some cases`, `depending on the context`, `it is possible that`.
- Balanced caveats where a direct answer is expected.

**Why it smells generic**

The output avoids responsibility. It sounds safe, complete, and neutral, but the user gets no decision.

**False positives**

- Medical, legal, financial, safety, or incomplete-evidence settings where hedging is required.

**Review move**

State the confidence and the action separately.

```md
Weak: This approach may potentially improve latency in some cases.
Better: Use caching for read-heavy endpoints. We have not benchmarked the write path yet.
```

---

### P10 — Tonal Flatness and Over-Completion

**Evidence labels:** `R-COMMUNITY`

**Observed forms**

- Perfect grammar but no authorial position.
- Every loop closed, every caveat resolved, every paragraph neatly rounded off.
- Voice that feels like a prepared script rather than a person with stakes.
- Polished but interchangeable corporate prose.

**Why it smells generic**

The output has readability but no ownership. It lacks the writer's constraint, risk, mistake, taste, or priority.

**False positives**

- Institutional communication where neutrality is intentional.
- Translation or non-native writing optimized for correctness.

**Review move**

Add one of: a named actor, a decision, a tradeoff, a rejected option, a concrete example, or a sentence the writer would defend.

---

### P11 — Pseudo-Depth and Faux Insight

**Evidence labels:** `R-COMMUNITY`, `G-OSS`

**Observed forms**

- Restating the premise in fancier language.
- Listing obvious considerations without ranking them.
- Ending with vague reflection: `Ultimately, the key is balance.`
- Aphoristic lines that sound profound but do not move the argument.
- Poetic framing for mundane tasks.

**Why it smells generic**

The output imitates depth through tone. It does not add information, evidence, or judgment.

**False positives**

- Speeches, essays, narrative copy, or founder letters where reflective pacing is intended.

**Review move**

Ask: “What would be missing if this sentence were deleted?” Delete or replace anything with no answer.

---

### P12 — Unearned Punchy Sentence Fragments

**Evidence labels:** `R-COMMUNITY`

**Observed forms**

- `Full stop.`
- `That's the point.`
- `And that matters.`
- `Every time.`
- A sequence of short fragments meant to create drama.

**Why it smells generic**

Short fragments can work, but AI-assisted drafts often use them as prepackaged emphasis without prior tension.

**False positives**

- Ad copy, speeches, social posts, newsletters, or op-eds with a deliberate rhythm.

**Review move**

Keep the fragment only if the previous sentence earns the emphasis.

---

### P13 — Metaphor Overproduction

**Evidence labels:** `R-COMMUNITY`, `G-OSS`

**Observed forms**

- `symphony`, `tapestry`, `dance`, `journey`, `labyrinth`, `beacon`, `crucible`, `unlock`, `unleash`.
- Objects or abstractions described as if they have human agency.
- Extended analogies unrelated to the user's concrete problem.

**Why it smells generic**

The text borrows emotional weight instead of earning it through detail.

**False positives**

- Brand campaigns, literary writing, speeches, poetry, editorial essays.

**Review move**

Replace metaphor with mechanism unless the metaphor clarifies a complex idea.

---

### P14 — Generic Positive Closure

**Evidence labels:** `R-COMMUNITY`, `G-OSS`

**Observed forms**

- `In conclusion...`
- `Ultimately...`
- `By embracing X, we can create a better future.`
- `The key is to stay adaptable and thoughtful.`
- Positive ending that does not follow from the evidence.

**Why it smells generic**

The conclusion resolves discomfort without doing the final analytical work.

**False positives**

- Motivational writing, classroom summaries, campaign copy.

**Review move**

End with the strongest implication, next action, risk, or unresolved question.

---

### P15 — Proof-Shaped Citations and Fabricated Specificity

**Evidence labels:** `R-COMMUNITY`, `N-INDUSTRY`

**Observed forms**

- Fake sources, fake author-title pairings, incorrect legal citations, or mismatched references.
- Specific numbers without source trail.
- Bug reports that cite nonexistent changelogs, impossible function signatures, or unreproducible vulnerabilities.
- `Research shows...` without a source.

**Why it smells generic**

The output imitates verification. This is higher risk than style because it can mislead readers and waste reviewer time.

**False positives**

- Drafts with placeholder citations clearly marked as placeholders.

**Review move**

Do not rewrite around the issue. Verify, replace, or remove the claim.

---

### P16 — Machine Artifact Leakage

**Evidence labels:** `G-OSS`

**Observed forms**

- AI-tool tracking parameters in URLs, such as ChatGPT/Copilot/OpenAI/Claude/Perplexity/Grok source or referrer parameters.
- Residual model phrases: `As an AI language model`, `I don't have access to`, `Certainly!`, `Great question!` where inappropriate.
- Citation-markup remnants or generated-source artifacts copied into the final text.
- Prompt scaffolding accidentally published: `Here is a polished version`, `Below is...`, `Let's break it down`.

**Why it smells generic**

Unlike subtle style signals, this is an explicit production hygiene failure. It breaks trust even when the content is otherwise useful.

**False positives**

- Articles intentionally discussing AI tools or showing examples.

**Review move**

Strip artifacts. Then inspect nearby text for unedited generated structure.

---

### P17 — Social Post “Synthetic Insight” Cadence

**Evidence labels:** `R-COMMUNITY`

**Observed forms**

- Many short lines.
- Repeated contrast hooks.
- Rhetorical questions followed by immediate answers.
- Line-by-line pseudo-confession without concrete event.
- Uniform emoji placement.
- Generic inspirational close.

**Why it smells generic**

The post imitates the outer shape of insight, but lacks the messy, specific situation that produced it.

**False positives**

- LinkedIn-style posts, newsletters, speeches, creator content using a deliberate hook structure.

**Review move**

Insert a real scene, decision, failure, number, or constraint in the first third of the post.

---

### P18 — Technical Documentation Buzzword Layer

**Evidence labels:** `G-OSS`

**Observed forms**

- `comprehensive guide`, `powerful tool`, `robust set of features`, `seamlessly integrates`, `cutting-edge`, `enterprise-grade`.
- README intro spends several paragraphs on why the project matters before showing how to run it.
- Commit messages with generic self-description: `This commit adds... ensuring consistency and robustness.`

**Why it smells generic**

Docs should reduce time-to-success. Buzzwords increase perceived polish but delay the first useful action.

**False positives**

- Product marketing README, investor-facing technical overviews.

**Review move**

Put installation, minimal example, supported versions, and known limitations before positioning language.

---

### P19 — AI-Generated Commit and PR Smell

**Evidence labels:** `G-OSS`, `N-INDUSTRY`

**Observed forms**

- PR description does not disclose AI involvement where policy requires it.
- Contributor cannot explain the change.
- Code compiles only in the generated happy path.
- Tests are missing, superficial, or generated without understanding.
- The PR fixes a visible issue but introduces regressions in adjacent paths.
- Generic commit prose over-justifies rather than describing the actual diff.

**Why it smells generic**

Maintainers need ownership, not just output. AI-assisted code is acceptable only when the contributor understands, tests, and can maintain it.

**False positives**

- Junior contributors writing cautious commit descriptions.
- Large mechanical refactors that naturally look repetitive.

**Review move**

Require:

```md
- Scope of AI involvement
- Human review performed
- Reproduction steps or test case
- Why the change is correct
- What adjacent behavior might regress
```

---

### P20 — AI Security Report Slop

**Evidence labels:** `N-INDUSTRY`, `G-OSS`

**Observed forms**

- Vulnerability report looks polished but is not reproducible.
- Claims a vulnerability without proving exploitability.
- References nonexistent changelogs, fake functions, or wrong signatures.
- Confuses a normal bug, configuration issue, or user error with a security flaw.
- Submits broad AI-generated reports to bounty programs with financial incentives.

**Why it smells generic**

The report transfers verification labor to maintainers. It appears legitimate enough to require triage but contains no actionable vulnerability.

**False positives**

- Early responsible disclosure reports where the reporter is still narrowing reproduction.

**Review move**

Reject or return for reproduction:

```md
- Affected version and environment
- Minimal proof of concept
- Expected vs actual security impact
- Exact code path or endpoint
- Confirmation that functions/files cited exist
```

---

### P21 — Web/UI “SaaS Average” Aesthetic

**Evidence labels:** `G-OSS`

**Observed forms**

- Purple-to-blue gradients everywhere.
- Glassmorphism, blurred orbs, neon glow.
- Inter or similar neutral sans used for every typographic role.
- Card grids nested inside card grids.
- Side-tab cards with colored borders.
- Hero → metrics → features → CTA template repeated across products.
- Motion without interaction meaning.
- Big generic icons, low contrast, decorative badges.

**Why it smells generic**

The page looks like an average of modern SaaS references rather than a product-specific interface.

**False positives**

- Early prototypes, hackathon demos, internal tools, or generic design-system examples.

**Review move**

Tie each visual decision to one of: hierarchy, state, task flow, trust, brand memory, accessibility, or conversion.

---

### P22 — Blinking Dot / Status Badge Decoration

**Evidence labels:** `G-OSS`, `R-COMMUNITY`

**Observed forms**

- Pill badge with pulsing dot: `Live`, `New`, `AI-powered`, `Now available`.
- Dot signals activity when there is no real state change.
- Multiple animated attention cues compete on the page.

**Why it smells generic**

The dot borrows urgency from real-time systems. If it does not represent live status, recording, syncing, availability, or notification state, it becomes decoration.

**False positives**

- Actual online, recording, streaming, deploy, monitoring, or incident states.

**Review move**

Keep the dot only if it maps to state. Otherwise replace with static hierarchy or copy.

---

### P23 — Copy-Paste Layout Grammar

**Evidence labels:** `G-OSS`

**Observed forms**

- Same section anatomy repeated: eyebrow, headline, subhead, 3 cards, CTA.
- Feature cards with identical icon size, heading length, and copy rhythm.
- Metrics with large numbers but no source or context.
- `01 / 02 / 03` steps without a real sequence.

**Why it smells generic**

The layout is filled rather than designed. It distributes attention evenly even when user intent is uneven.

**False positives**

- Design-system documentation, pricing pages, onboarding steps, course modules.

**Review move**

Collapse repeated sections. Promote the one user task or proof point that matters most.

---

### P24 — Generated Image and Visual Slop

**Evidence labels:** `R-COMMUNITY`, `G-OSS`

**Observed forms**

- Over-polished skin, glossy objects, synthetic lighting.
- Broken small text, labels, hands, teeth, reflections, shadows, or repeated background patterns.
- Generic 3D objects in presentations or hero sections.
- Inconsistent brand, era, geography, or cultural context.

**Why it smells generic**

The image optimizes for surface appeal but misses physical, textual, or contextual constraints.

**False positives**

- Deliberately surreal, stylized, 3D, or speculative art direction.

**Review move**

Check the visual against the use case: what must the viewer believe, understand, or do after seeing it?

---

### P25 — Detector Overreach and False-Positive Risk

**Evidence labels:** `M-METRIC`, `R-COMMUNITY`, `G-OSS`

**Observed forms**

- Declaring authorship from one word such as `delve`.
- Treating clean grammar, clear structure, or low typo rate as proof of AI origin.
- Penalizing non-native writers, technical writers, corporate style, or academic conventions.
- Optimizing for detector evasion instead of output quality.

**Why it matters**

The skill should improve outputs, not police authorship. A good review flags weak patterns and gives fixes; it does not accuse.

**Review move**

Use cluster-based language:

```md
Use: “This passage has a high generic-output risk: broad opener, inflated vocabulary, and unsupported conclusion.”
Avoid: “This was clearly written by AI.”
```

---

## 5. Cluster Scoring Guide

Use scoring only to prioritize revision. Do not present it as authorship probability.

| Score | Meaning | Typical action |
|---:|---|---|
| 0 | No visible generic-output concern | No action |
| 1 | One mild pattern, likely acceptable | Leave unless it weakens the purpose |
| 2 | Two or three mild patterns | Edit locally |
| 3 | Cluster of style patterns in one section | Rewrite the section |
| 4 | Multiple clusters across output | Rebuild structure and voice |
| 5 | Machine artifacts, fake citations, non-reproducible claims, or unowned code | Block delivery until verified or rewritten |

Suggested confidence levels:

| Confidence | Use when |
|---|---|
| Low | Pattern is subjective or genre-dependent |
| Medium | Several visible patterns recur in one passage |
| High | Explicit artifacts, fabricated references, or repeated structural templates are present |

---

## 6. Pattern Intake Template

Use this template when adding new field-reported patterns.

```md
### PXX — Pattern Name

**Evidence labels:** `R-COMMUNITY` / `G-OSS` / `M-METRIC` / `N-INDUSTRY` / `D-DICTIONARY` / `A-ACADEMIC`

**Source anchors**

- Source title:
- Source type:
- Date observed:
- URL or repository:
- Notes on source reliability:

**Observed forms**

- Phrase, component, layout, code shape, or behavior:
- Common modality:
- Common task purpose:

**Why it smells generic**

Explain the purpose-fit failure. Do not claim authorship.

**False positives**

List contexts where the pattern is acceptable.

**Review move**

Give a concrete replacement rule or rewrite pattern.
```

---

## 7. Source-Informed Review Notes

Use these notes when writing final review comments.

### 7.1 Words are weak evidence; clusters are stronger

Many community lists contain normal words. A single word such as `delve`, `landscape`, or `robust` should not trigger a finding by itself. Flag it when the surrounding paragraph also has broad claims, filler framing, low specificity, and template structure.

### 7.2 Machine artifacts are stronger than style signals

Tool tracking parameters, copied assistant scaffolding, residual generated citations, impossible references, and unowned code are high-confidence quality failures. They still do not prove authorship, but they do justify blocking delivery.

### 7.3 Design slop is often average taste, not an error

Inter-like fonts, cards, gradients, glassmorphism, blinking dots, and motion are not defects by themselves. They become defects when they have no connection to brand, hierarchy, task flow, state, or accessibility.

### 7.4 Code slop is a process failure

The main review question is not “was AI used?” The question is whether the contributor understands the code, can reproduce the issue, tested the change, disclosed automation where required, and reduced maintainer work rather than shifting it downstream.

---

## 8. Source Index for Future Updates

Use these sources as starting points for future refreshes. Prefer direct GitHub repositories, maintainer policies, and measurement tools for operational rules. Use Reddit and Hacker News for emergent vocabulary and perception patterns, not final judgment.

### Community reports

- Reddit: [`r/ChatGPTPro` thread on overused ChatGPT terms](https://www.reddit.com/r/ChatGPTPro/comments/163ndbh/overused_chatgpt_terms_add_to_my_list/).
- Reddit: [`r/WritingWithAI` megathread on AI-isms in generated writing](https://www.reddit.com/r/WritingWithAI/comments/1mqse0s/megathread_what_aiisms_give_away_aigenerated/).
- Reddit: [`r/ChatGPT` thread on the `not just A, but B` construction](https://www.reddit.com/r/ChatGPT/comments/1sfrj68/this_its_not_just_a_its_b_sentence_construct_is/).
- Reddit: [`r/Professors` thread on AI-like assignment patterns](https://www.reddit.com/r/Professors/comments/1bne3h2/your_most_commonly_observed_signs_that_an/), including filler, fake references, generic writing, and unsuitable style.
- Reddit: [`r/AlwaysWhy` discussion on AI smell](https://www.reddit.com/r/AlwaysWhy/comments/1s8o0sl/why_does_ai_writing_always_have_an_ai_smell_even/) as “too balanced,” “too complete,” and voice-less writing.
- Reddit: [`r/LocalLLaMA` post on slop-forensics](https://www.reddit.com/r/LocalLLaMA/comments/1jw1g2a/a_slop_forensics_toolkit_for_llms_computing/), covering over-represented words and n-grams.
- Hacker News: [discussion of `not X, it is Y` / `not just X, it is Y`](https://news.ycombinator.com/item?id=45671160) as a recognizable LLM pattern.

### GitHub and OSS tools

- [`NousResearch/autonovel` — `ANTI-SLOP.md`](https://github.com/NousResearch/autonovel/blob/master/ANTI-SLOP.md), a writing-pattern field guide.
- [`sam-paech/slop-forensics`](https://github.com/sam-paech/slop-forensics), a toolkit for profiling over-represented words, bigrams, trigrams, and slop scores.
- [`sam-paech/slop-score`](https://github.com/sam-paech/slop-score), an in-browser writing metrics analyzer with weighted slop score components.
- [EQ-Bench Slop Score](https://eqbench.com/slop-score.html), public explanation of slop words, `not-x-but-y`, and trigram components.
- [`tbhb/vale-ai-tells`](https://github.com/tbhb/vale-ai-tells), a Vale package for AI-associated prose patterns in technical documentation and commit messages.
- [`bradleydwyer/sloppy`](https://github.com/bradleydwyer/sloppy), a regex-based CLI for AI prose tells with optional skill workflow.
- [`conorbronsdon/avoid-ai-writing`](https://github.com/conorbronsdon/avoid-ai-writing/blob/main/SKILL.md), a skill file including machine-artifact leakage and novelty inflation patterns.
- [`Aboudjem/humanizer-skill`](https://github.com/Aboudjem/humanizer-skill), a Markdown skill with pattern scoring and Reddit/HN-informed pattern discovery.
- [`BioInfo/slopless`](https://github.com/BioInfo/slopless), production-oriented anti-slop rules with real-world correction workflow.
- [Impeccable Slop](https://impeccable.style/slop/), a UI/design slop catalog for gradients, glassmorphism, typography, nested cards, layout repetition, and motion.

### Maintainer and industry incidents

- [`RPCS3/rpcs3`](https://github.com/RPCS3/rpcs3), repository policy requiring AI involvement disclosure in PRs and human review/testing details.
- [PC Gamer report on RPCS3 AI slop code](https://www.pcgamer.com/hardware/please-stop-submitting-ai-slop-code-team-behind-popular-ps3-emulator-call-time-on-user-submitted-vibe-coding/), summarizing maintainer concerns about unowned code and regressions.
- [ITPro report on curl bug bounty closure](https://www.itpro.com/software/open-source/curl-open-source-bug-bounty-program-scrapped), describing low-quality AI-generated vulnerability reports and non-reproducible claims.

### Terminology references

- [Simon Willison: `Slop is the new name for unwanted AI-generated content`](https://simonwillison.net/2024/May/8/slop/).
- [Macquarie Dictionary 2025 Word of the Year: `AI slop`](https://www.macquariedictionary.com.au/macquarie-dictionary-word-of-the-year-for-2025/).

---

## 9. Refresh Playbook

Run a source refresh when the user asks for “latest AI-smell patterns,” when adding a new modality, or when existing rules begin to overfit stale tells.

### 9.1 Search targets

Use these query shapes:

```text
site:reddit.com AI writing telltale signs AI slop words
site:reddit.com "not just" "but" ChatGPT writing
site:reddit.com AI generated assignment signs fake references
site:news.ycombinator.com AI writing smell "not X" "Y"
site:github.com AI slop writing patterns
site:github.com "AI slop" "commit" "pull request"
site:github.com "AI-generated" "disclosure" "pull request"
site:github.com "slop" "Vale" "AI" writing
site:github.com "AI slop" "bug bounty" "security report"
```

### 9.2 Inclusion rules

Add a pattern when at least one of these is true:

- It appears across two or more independent community discussions.
- It is implemented in an OSS linter, rule set, or skill.
- It is documented in a maintainer policy, issue template, or contribution guide.
- It caused a measurable operational problem, such as wasted maintainer time, false reports, regressions, or source verification failure.

### 9.3 Exclusion rules

Do not add a pattern when:

- It is just a single disliked word without context.
- It would penalize non-native writers, academic conventions, accessibility-friendly structure, or legitimate brand style.
- It encourages hiding AI use rather than improving output quality.
- It cannot be paired with a concrete fix.

### 9.4 Update format

When updating this file, add:

```md
- Pattern ID:
- Source labels:
- Source links:
- Short observed form:
- False-positive contexts:
- Review move:
- Date added:
```
