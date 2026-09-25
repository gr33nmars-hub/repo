# Dimension Review: Web, UI, and Product Design

Use for websites, landing pages, SaaS interfaces, dashboards, design systems, app screens, component specs, and generated UI prototypes.

## Purpose

UI design should make state, hierarchy, action, and product meaning visible. It should not only resemble a modern SaaS template.

## Common generic / AI-smell patterns

| Area | Pattern | Risk |
|---|---|---|
| Typography | Inter, Geist, Space Grotesk, Instrument Serif, JetBrains Mono used without a brand or interaction reason | Familiar “generated SaaS” feel |
| Hero section | Large abstract headline with gradient text | High polish, low positioning |
| Badge | Pill/eyebrow label with blinking dot | Decorative urgency or false live status |
| Layout | Six identical feature cards with rounded icon tiles | Equal weighting hides actual product hierarchy |
| Color | Purple-blue gradients, cyan-on-dark, neon glow, beige studio background | Category cliché if not tied to brand |
| Motion | Hover scale, bounce easing, pulsing dots | Motion without information value |
| Metrics | Big number row with unsourced claims | Trust risk |
| Visuals | Floating dashboards, 3D glossy objects, abstract mesh | Does not show actual product use |
| Copy | “AI-powered,” “seamless,” “supercharge,” “for modern teams” | Generic positioning |

## Blinking dot review

A blinking dot is acceptable when it communicates a real state.

| Valid use | Requirements |
|---|---|
| Live status | State must be real, labeled, and not purely decorative |
| Recording / active process | Include accessible text and non-color cue |
| Notification | Dot should map to new/unread/change state |
| Sync / loading | Use appropriate motion duration and fallback |
| Scroll cue | Use sparingly; should not distract from primary CTA |

A blinking dot becomes generic or AI-scented when:

- it appears beside “New,” “Live,” or “AI-powered” without functional meaning;
- it is used on every badge;
- it pulses only to make the page feel dynamic;
- it competes with the primary CTA;
- it has no accessible label or reduced-motion consideration.

## Font review

Popular fonts are not defects. Review whether typography serves identity and hierarchy.

Ask:

- Is the font choice tied to brand, readability, technical context, or content type?
- Is there a clear type scale?
- Are headings, body, labels, code, captions, and numbers distinguishable?
- Does monospace text indicate code/data/state, or is it decorative?
- Does the type system work on mobile and dense content screens?

Repair options:

- keep the font but sharpen hierarchy;
- pair a neutral body font with a distinctive heading style;
- reduce decorative monospace labels;
- define a type scale with explicit roles;
- use brand-specific typography where available.

## Component review

### Hero

Check:

- Does the headline name the user, workflow, or outcome?
- Does the subhead explain the mechanism?
- Does the visual show real product behavior or only decorative abstraction?
- Is the CTA matched to intent?

### Feature cards

Check:

- Are cards ordered by user value?
- Can any cards be merged?
- Do icons clarify the feature?
- Does each card include an example input, output, state, or result?

### Dashboard / product visual

Check:

- Is data realistic?
- Are empty, loading, error, and permission states represented?
- Are labels readable?
- Is the screenshot aligned with the copy’s claim?

### Motion

Check:

- Does motion communicate state, direction, hierarchy, or feedback?
- Is there a reduced-motion alternative?
- Does animation frequency distract from reading or conversion?

## Accessibility checks

- Text contrast supports the use case.
- Interactive elements have visible focus states.
- Color is not the only status indicator.
- Motion can be reduced or paused.
- Tap targets are usable on mobile.
- Important text is not embedded only in images.
- Icons have labels where needed.

## AI-smell reduction patterns

| Generic pattern | Better design decision |
|---|---|
| “New” badge with blinking dot | Badge only if the feature is actually new; add date or release context |
| Gradient hero text | Use emphasis on the actual differentiator, not the whole promise |
| Six feature cards | Convert to a workflow: input → processing → review → output |
| Floating glass dashboard | Show a real screen with realistic data and state labels |
| Generic CTA | Use intent-specific CTA: “Upload transcript,” “Run audit,” “View sample report” |
| Decorative monospace | Reserve monospace for IDs, code, logs, metrics, or system states |

## Acceptance criteria

- Every decorative element has a functional or brand reason.
- The first screen explains the product’s specific value.
- Status indicators represent actual states.
- Typography has hierarchy, not only trend alignment.
- Feature structure follows user workflow or priority.
- Accessibility basics are satisfied.
