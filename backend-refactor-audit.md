# Backend audit and refactor status

Updated 2026-10-21 from the current working tree. The audit checks the Python domain, application and SQLite layers, tests, API boundary, and the Windows desktop integration. It describes code behavior; it does not infer who or what authored it.

## Findings and changes

| Priority | Finding | Current status |
| --- | --- | --- |
| High | Blackjack actions could bypass balance checks, and mutable round state escaped the engine. | Fixed: `act(action, balance)` is the action entry point; `hand` returns a detached copy; `Shoe` owns its lists and exposes tuples. Tests cover denied double/split, invalid phases, and immutable shoe views. |
| High | Blackjack combined game rules, API projection, and save-version handling; `GameResult` also owned API and persistence dictionaries. | Fixed: state and result projections live in `application/queries.py`; profile/history encoding and decoding live in `persistence/codecs.py`; blackjack save compatibility lives in `persistence/blackjack_codec.py`. Domain models no longer expose `to_dict`/`from_dict`. |
| High | Same-balance writes needed a different-key race test. | Covered: `test_concurrency.py` races independent services against one SQLite file and checks the wallet, ledger, and idempotency results. Writes begin with `BEGIN IMMEDIATE`. |
| Medium | Tests used hand-built ASGI plumbing and inconsistent assertion patterns. | Simplified: backend tests use pytest, and API tests use FastAPI `TestClient` with a fresh database per test. The suite has no `unittest.TestCase` tests. |
| Medium | The checkout mixed Tauri configuration with a partial PyWebView migration. | Corrected: PyWebView entry points and dependency were removed; Tauri starts the API sidecar in packaged builds and the API/Vite processes during development. Public-facing product metadata now says NOIR Casino Club. |
| Medium | Repository docs and release metadata named the old product and described stale commands. | Updated: README, product notes, developer notes, frontend instructions, Tauri metadata, and license now match the current project. The existing `.astoria-casino` save directory and app identifier remain stable to preserve local data and upgrade identity. |

## Decisions that affect compatibility

- Each committed blackjack round uses a fresh, deterministically shuffled six-deck shoe. A shared shoe across rounds would require a different seed/nonce and save protocol; it is not introduced as a side effect of this refactor.
- The fairness verifier recalculates results independently of the game payout methods. Keep seed encoding, nonce use, shuffle order, wheel mapping, and reel mapping covered by fixed vectors.
- SQLite save migrations remain forward-only and preserve legacy fixtures. The repository makes an integrity-checked backup before migrating a non-empty save.
- The API token header and save-path environment names retain their Astoria spelling for compatibility. They are internal names, not user-facing product branding.

## Remaining verification

- Full Tauri installer creation was attempted but could not run in this Windows environment because the Visual Studio C++ build tools were unavailable. The packaged sidecar itself did build and passed `npm run smoke:sidecar`.
- The backend suite emits one upstream deprecation warning from Starlette/AnyIO while importing `TestClient`; there are no project test failures.
- The Windows Tauri bundle still needs verification on a machine with the required native toolchain. The repository workflow now builds the Windows app and smoke-tests the packaged sidecar.

## Checks run

- `uv run --directory backend --group test pytest -q` — 339 passed.
- `uv run --directory backend --group quality ruff check casino tests run_api.py` — passed.
- `uv run --directory backend --group quality ruff format --check casino tests run_api.py` — passed.
- `uv run --directory backend --group quality mypy --python-version 3.10 casino run_api.py` — passed.
- `npm run test:unit` — 15 passed.
- `npm run lint` and `npm run build` — passed.
- `npm run build:desktop` and `npm run smoke:sidecar` — passed on Windows.
- `npm run tauri:build` — not completed because the local Visual Studio C++ toolchain check failed.
