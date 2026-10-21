# Product notes

NOIR Casino Club is a single-player desktop simulator for virtual chips. It has three tables:

- **Blackjack:** six-deck rounds, split up to four hands, double, late surrender, and insurance. The dealer stands on soft 17 by default.
- **European roulette:** one zero and bets on red, black, or zero.
- **Slots:** three independently configured reels with a published paytable.

The app stores one local player profile and completed-round history in SQLite. Chips have no cash value. The app does not accept payments or connect to a gambling service.

## Technical boundaries

- Tauri v2 owns the Windows desktop window and starts the packaged Python API sidecar.
- FastAPI exposes the local application API. The UI is React 19, TypeScript, and Vite.
- The domain owns game rules and transitions. The application layer coordinates commands and read models. SQLite persistence owns transactions, migrations, ledger entries, and save codecs.
- Round proofs use HMAC-SHA256, a server-seed commitment, a client seed, and a nonce. The verifier reproduces outcomes from the disclosed proof data.

The app keeps the existing `.astoria-casino` save directory and legacy environment variable names so a rebrand does not discard local profiles.
