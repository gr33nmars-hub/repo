# Surface brief: NOIR desktop Operate

## THESIS
NOIR is a quiet night-club card ledger: a composed, functional place to choose a real game table and see the player's actual demo-chip account.

## OWN-WORLD
- Product: educational, local desktop casino with virtual demo chips only.
- Surface: Tauri desktop app, operated with mouse and keyboard; React/Vite frontend and real local FastAPI state.
- Primary palette: charcoal green-black, warm paper-white text, restrained brass and muted emerald.
- Typography: self-hosted Outfit for clear Russian UI and room titles; Cascadia Mono for numeric limits and compact labels.
- Atmosphere: private, nocturnal club; one original illustration of an adult, fully clothed hostess. No stock-photo collage or sexualized treatment.
- Material: mostly flat surfaces and fine rules; tone and spacing establish hierarchy instead of glass panels or decorative gradients.
- Icons: a consistent authored SVG set in shell navigation and lobby.
- Motion: short room transition and direct hover/focus feedback. No idle loop, scroll choreography, or autoplay.

## STORY
Players orient themselves from a persistent room navigation, read the server-provided table limits, and enter a table. The lobby ledger and round list reflect API data. Connectivity errors, loading, empty tables, and empty history remain explicit. The shell is shared by lobby, blackjack, slots, roulette, and history.

## FIRST VIEWPORT
At the 1280×860 Tauri window, a narrow persistent navigation rail sits beside a top bar and the lobby. The main region gives table selection primary space; an API-fed account ledger, hostess portrait, and recent API-fed rounds occupy the companion column. At the 920×640 minimum, the account companion moves below the table list and the content remains scrollable.

## FORM
Desktop-first, keyboard-operable. Navigation uses buttons with active-page state and visible focus; room content has a skip link target. Dynamic state is sourced from the existing API; no fake table availability, balance, player count, or game result is allowed. Respect `prefers-reduced-motion`.

## BOUNDARIES
- Keep `RoomRoute` stable: `lobby | blackjack | slots | roulette | history`.
- Keep API types and `useCasino` as the source of player balance, statistics, table limits, history, and game actions.
- Game-room components remain separate from the shell and can be replaced in a later frontend pass.
- Do not introduce landing-page sections, marketing claims, or invented navigation.
