---
name: NOIR Casino Club
description: A restrained night-club interface for real local casino state and virtual-chip tables.
colors:
  canvas: "#101311"
  surface: "#171b18"
  surface-raised: "#1e231f"
  ink: "#eee9df"
  muted: "#a7aaa0"
  rule: "#343a32"
  brass: "#cfb77c"
  brass-strong: "#e6d19c"
  emerald: "#93b99c"
  danger: "#d78d83"
typography:
  display:
    fontFamily: "Outfit, 'Segoe UI', Arial, sans-serif"
    fontSize: "clamp(31px, 3.2vw, 43px)"
    fontWeight: 450
    lineHeight: 1.07
    letterSpacing: "-0.045em"
  title:
    fontFamily: "Outfit, 'Segoe UI', Arial, sans-serif"
    fontSize: "17px"
    fontWeight: 500
    lineHeight: 1.3
  body:
    fontFamily: "Outfit, 'Segoe UI', Arial, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "'Cascadia Mono', Consolas, 'Courier New', monospace"
    fontSize: "10px"
    fontWeight: 400
    lineHeight: 1.4
rounded:
  square: "0px"
  circle: "50%"
spacing:
  xs: "4px"
  sm: "8px"
  md: "14px"
  lg: "18px"
  xl: "27px"
components:
  navigation-current:
    backgroundColor: "#22241e"
    textColor: "{colors.brass-strong}"
    rounded: "{rounded.square}"
    padding: "0 11px"
    height: "42px"
  account-ledger:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.square}"
    padding: "17px 18px"
  table-entry:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.square}"
    padding: "15px 10px"
    height: "106px"
  table-count:
    textColor: "{colors.muted}"
    typography: "{typography.label}"
---

# Design System: NOIR Casino Club

## Overview

**Creative North Star: "The Night Ledger"**

The interface treats NOIR as a composed private club whose tables are easy to read and enter. A persistent navigation rail and a clear table register provide operational structure; the player ledger and recent rounds carry the real account context next to it. Visual character comes from dark green-black surfaces, fine dividing rules, Outfit's adaptable weights, and sparse brass and emerald accents.

Depth stays tonal and mostly flat. The custom adult hostess illustration is a small authored identity element, while gameplay remains the primary experience. Functional transitions are brief and quiet; the interface stays legible at the minimum desktop window and honors reduced-motion preferences.

**Key Characteristics:**
- Operate-first navigation and table selection.
- API-fed balances, limits, statistics, and history.
- Restrained color and flat, finely ruled surfaces.

## Colors

Charcoal green-black grounds the app, warm near-white carries text, and brass or muted emerald is reserved for emphasis and positive state.

### Primary
- **Muted Brass**: The balance and selected navigation accent; use sparingly to mark actionable or selected state.
- **Muted Emerald**: Positive results and the secondary table accent.

### Neutral
- **Club Canvas**: Application background.
- **Ledger Surface**: Account and supporting surface background.
- **Raised Surface**: Hover or nested surface.
- **Warm Ink**: Primary text.
- **Quiet Ink**: Supporting copy and labels.
- **Club Rule**: Fine dividers and boundaries.

### Named Rules
**The Real State Rule.** Use color to clarify actual account, result, or selection state; never imply activity the API has not supplied.

## Typography

**Display Font:** Outfit (self-hosted, with Segoe UI and Arial fallbacks)
**Body Font:** Outfit (with Segoe UI and Arial fallbacks)
**Label/Mono Font:** Cascadia Mono (with Consolas and Courier New fallbacks)

**Character:** Outfit is direct and compact across Russian UI labels and expressive room titles. Tabular monospace is limited to numeric limits and short metadata.

### Hierarchy
- **Display** (450, 31–43px, 1.07): Lobby and page headings.
- **Title** (500, 17px, 1.3): Section and supporting panel headings.
- **Body** (400, 13px, 1.55): Descriptions and explanatory copy.
- **Label** (400, 9–10px, 1.4): Numeric limits and compact ledger metadata.

### Named Rules
**The Readable Room Rule.** Scale expressive titles for the current room; keep operational labels compact but comfortably readable.

## Layout

Desktop uses a persistent 226px navigation rail and a flexible main pane. At the 920px application minimum, the rail contracts and the lobby companion ledger moves below the table register. The 1280×860 default window supports a two-column lobby. Content stays scrollable in shorter windows; table rows are a vertical register, not a repeated card grid.

## Elevation & Depth

The system is mostly flat. Use distinct dark tones, borders, and space to establish hierarchy; reserve shadows for gameplay surfaces that already use them. The lobby account ledger receives a single fine brass-gray boundary rather than a floating-card treatment.

## Shapes

Shell surfaces, table rows, and navigation are square-cornered. Circular clipping is reserved for the hostess portrait and player initial. Borders are fine and low contrast at rest, with stronger contrast for keyboard focus and active controls.

## Components

- **Persistent navigation:** authored SVG pictograms, exact room labels, a clear active state, and `aria-current` on the selected room.
- **Table register:** one row per server-provided game, with the API name and wager limits, concise rule context, and a button-sized entry target.
- **Player ledger:** current balance, rounds, wins/win rate, and turnover from API state.
- **Recent rounds:** short list of API results with sign-coded profit and an explicit empty state.
- **Shell feedback:** visible connection/error, loading, and notice states with retry affordances where applicable.
- **Focus:** 2px brass-strong visible outline with 3px offset.

## Do's and Don'ts

- Do keep the five existing routes stable: lobby, blackjack, slots, roulette, and history.
- Do keep backend state as the source for the player's balance, statistics, limits, and round results.
- Do keep icons in the shell and lobby within the authored SVG set.
- Do respect `prefers-reduced-motion` and keep transitions short.
- Don't invent live-player counts, online activity, recommendations, results, or account metrics.
- Don't turn the operating surface into a marketing landing page or decorative KPI dashboard.
- Don't use emoji as interface icons.
