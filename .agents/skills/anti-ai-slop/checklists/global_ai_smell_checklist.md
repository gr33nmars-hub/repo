# Global Generic / AI-Smell Checklist

Use this checklist across all output types. Treat these as review heuristics, not proof of AI generation.

## High-level signals

| Signal | What it looks like | Why it matters |
|---|---|---|
| Average-shape output | The artifact has the generic structure of a good answer but lacks contextual judgment | It may appear competent while failing the real task |
| Over-smoothing | No rough edges, no prioritization, no tension, no concrete constraint | It can feel unowned or interchangeable |
| Symmetric structure | 3 benefits, 3 risks, 3 steps, 6 cards, equal paragraph lengths | Real priorities often require uneven weight |
| Empty professionalism | Formal words replace evidence or decision | It hides weak thinking behind tone |
| Safe neutrality | Every option is balanced and caveated | The user may not know what to do next |
| Generic transformation | “Unlock,” “supercharge,” “reimagine,” “seamless,” “future of X” | These phrases signal benefit without mechanism |
| Decorative modernity | Gradient text, glass cards, blinking dots, glossy objects | Visual style may not encode meaning |
| Pseudo-specificity | Precise-looking statistics, fake metrics, unnamed studies | Damages trust when unsupported |
| Polished but local-context poor | Code, UI, or copy ignores actual system, user, market, or brand | Breaks in real deployment |
| Prompt/template residue | “As an AI,” leaked instructions, bracket placeholders, unfilled variables, policy boilerplate | Reveals the artifact was not cleaned for the real audience |
| Synthetic operational plan | Plan has steps but no owner, deadline, dependency, budget, approval path, fallback, or acceptance criterion | Looks executable while hiding implementation risk |
| Compliance/security theater | Trust badges, “secure by design,” SOC 2/HIPAA/GDPR claims, or privacy promises without proof or scope | Creates legal, trust, and safety risk |
| Localization mismatch | Wrong locale formats, translationese, mixed register, generic “global” language, or culturally mismatched examples | Makes output feel imported rather than made for the audience |

## Writing signals

- Broad opening: “In today’s fast-paced world...”
- Generic importance claim: “This is important because...”
- Repeated connectors: “Additionally,” “Furthermore,” “Moreover,” “In conclusion.”
- Inflated adjectives: “pivotal,” “comprehensive,” “robust,” “innovative,” “transformative.”
- Formulaic contrast: “not merely X, but Y.”
- Lesson-like ending that adds no decision or evidence.
- Overuse of bullets where narrative or argument is needed.
- Placeholder residue: `[Company]`, `{insert statistic}`, “TODO,” “draft goes here,” or unused template sections.
- Policy-like boilerplate that refuses, apologizes, or caveats without resolving the user’s actual problem.
- SEO/content-farm pattern: keyword-stuffed headings, generic FAQ blocks, “ultimate guide” filler, duplicate-intent sections.

## UI and web signals

- Large hero headline with vague promise.
- Pill badge with blinking dot but no real status.
- Purple-blue gradient text used as a substitute for brand language.
- Inter/Geist/Space Grotesk/JetBrains Mono-like typography without a brand reason.
- Six identical feature cards with rounded icon tiles.
- Metrics row with unsourced numbers.
- Dark background, neon glow, and glassmorphism without product meaning.
- Hover or bounce animation that does not communicate state.

## Presentation signals

- Every slide has one heading and three bullets.
- Icons are generic placeholders rather than memory cues.
- Statistics appear precise but lack source, date, or definition.
- Glossy 3D objects add polish but not explanation.
- Final slide says “Questions?” without a decision, ask, or next step.
- Roadmaps or implementation plans omit owner, deadline, dependency, approval path, risk trigger, rollback, or acceptance criteria.
- Charts decorate the argument but lack axis labels, units, source, denominator, or metric definition.

## Code signals

- Works for the happy path only.
- Hardcoded values, mock data, or placeholder credentials remain.
- Generic error handling hides failure modes.
- Comments explain obvious code but not domain assumptions.
- API, package, or function names may be hallucinated or version-incompatible.
- Tests are absent or only confirm expected success.
- Demo-only artifacts remain: fake IDs, TODO comments, sample users, placeholder endpoints, or copied scaffold text.
- Security and privacy language appears in comments or docs without actual validation, permissions, encryption, retention, or audit behavior.

## Visual signals

- Over-polished skin, lighting, or texture.
- Incorrect text on signs, labels, book covers, or UI screens.
- Anatomical inconsistencies in hands, teeth, ears, eyes, or joints.
- Repeated background patterns or duplicated faces.
- Impossible reflections, shadows, straps, cables, or object interactions.
- Dashboard screenshots show fake-looking sample data, impossible distributions, over-precise benchmarks, or mismatched chart labels.
- Locale-specific details are wrong: date format, currency, address, units, signage language, dress, holidays, or formality level.

## False positives

These are not problems by themselves:

- clean formatting;
- concise bullets;
- simple language;
- popular fonts;
- status dots;
- templates;
- 3-part structures;
- polished visuals;
- generated code scaffolding.

They become problems when they replace specificity, evidence, usability, or judgment.

## Strong signal combinations

A strong generic-output signal usually appears as a cluster:

```text
Vague hero promise
+ pill badge with decorative blinking dot
+ purple gradient text
+ six uniform feature cards
+ “supercharge your workflow” copy
+ no concrete user, workflow, proof, or mechanism
```

or:

```text
Broad essay opening
+ repeated aphorisms
+ “not X but Y” contrasts
+ no scene, name, conflict, or lived detail
+ inspirational ending
```

or:

```text
Report-like structure
+ unsupported statistics
+ formal abstract language
+ balanced pros/cons
+ no recommendation or owner
```
