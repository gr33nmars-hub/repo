# Engineering notes

These notes describe the current implementation. The source and tests remain authoritative when behavior changes.

## Game and application layers

`backend/casino/domain/` contains game rules, result calculation, blackjack state, and fairness algorithms. It does not import FastAPI or SQLite. `application/commands.py` coordinates a game command with a wallet transaction; `application/queries.py` builds the state returned by the API. Persistence codecs translate blackjack snapshots to the versioned save format.

## Fairness proofs

The server publishes a SHA-256 commitment before a round. Results use HMAC-SHA256 with the server seed, client seed, nonce, and game-specific input. Bounded integers use rejection sampling to avoid modulo bias. The round verifier recalculates outcomes from stored proof data rather than calling the game payout implementation.

Any change to seed encoding, nonce use, shuffle order, wheel mapping, or reel-stop calculation changes the proof contract. Keep the existing test vectors and increment the game rule version when a change intentionally alters outcomes.

## SQLite and wallet updates

`PlayerRepository` opens write operations with `BEGIN IMMEDIATE`. Balance, ledger movements, blackjack state, and idempotent response records are committed in one transaction. The process lock prevents a second app instance from opening the same local save concurrently; SQLite still serializes writes from separate connections.

When changing a persisted schema, add a forward migration and keep fixtures for supported old saves. The repository creates an integrity-checked backup before migrating a non-empty database.

## Desktop boundary

Tauri v2 packages the React frontend and launches the Python API as a sidecar. In development, `frontend/scripts/dev-desktop.mjs` starts Vite and the API with a shared one-run token. In the packaged app, the frontend creates a fresh token and passes it to the sidecar process.

## Checks

Run the backend pytest, Ruff, and Mypy commands from the root README. Frontend checks run from `frontend/` with the scripts listed in `frontend/package.json`.
