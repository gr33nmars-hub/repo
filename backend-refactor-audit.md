# Backend audit and refactor status

Updated 2026-10-21 from the current working tree. The audit checks the Python domain, application and SQLite layers, tests, API boundary, and the Windows desktop integration. It describes code behavior; it does not infer who or what authored it.

## Findings and changes

| Priority | Finding | Current status |
| --- | --- | --- |
| High | Blackjack actions could bypass balance checks, and mutable card collections were exposed from round state. | Fixed: `act(action, balance)` is the action entry point; `hand` returns a detached copy; `PlayerHand.cards` and `Shoe` card views are tuples. The engine alone mutates a hand's card list. Tests cover denied double/split, invalid phases, detached state, and immutable card views. |
| High | Blackjack combined game rules, API catalog projection, and save-version handling; `GameResult` also owned API and persistence dictionaries. | Fixed: state, result, and game-catalog projections live in `application/queries.py`; profile/history encoding and decoding live in `persistence/codecs.py`; blackjack save compatibility lives in `persistence/blackjack_codec.py`. Domain models no longer expose API `catalog_info` or `to_dict`/`from_dict` methods. |
| High | Same-balance writes needed a different-key race test. | Covered: `test_concurrency.py` races independent services against one SQLite file and checks the wallet, ledger, and idempotency results. Writes begin with `BEGIN IMMEDIATE`. |
| Medium | Tests used hand-built ASGI plumbing and inconsistent assertion patterns. | Simplified: backend tests use pytest, and API tests use FastAPI `TestClient` with a fresh database per test. The suite has no `unittest.TestCase` tests. |
| Medium | The checkout mixed Tauri configuration with a partial PyWebView migration. | Corrected: PyWebView entry points and dependency were removed; Tauri starts the API sidecar in packaged builds and the API/Vite processes during development. Public-facing product metadata now says NOIR Casino Club. |
| Medium | Repository docs and release metadata named the old product and described stale commands. | Updated: README, product notes, developer notes, frontend instructions, Tauri metadata, and license now match the current project. The existing `.astoria-casino` save directory and app identifier remain stable to preserve local data and upgrade identity. |

## Decisions that affect compatibility

- Each committed blackjack round uses a fresh, deterministically shuffled six-deck shoe. A shared shoe across rounds would require a different seed/nonce and save protocol; it is not introduced as a side effect of this refactor.
- The fairness verifier now implements its own proof verification primitives instead of importing production generation helpers. Keep seed encoding, nonce use, shuffle order, wheel mapping, and reel mapping covered by fixed vectors.
- Provably fair bounded sampling rejects ranges outside the SHA-256 space instead of looping forever.
- SQLite save migrations remain forward-only and preserve legacy fixtures. The repository makes an integrity-checked backup before migrating a non-empty save.
- The API token header and save-path environment names retain their Astoria spelling for compatibility. They are internal names, not user-facing product branding.

## Remaining verification

- The local Windows environment has no Cargo or Visual Studio C++ Build Tools, so the installer cannot be built here. GitHub Actions completed the Windows installer build and packaged-sidecar smoke test successfully.
- The backend suite emits one upstream deprecation warning from Starlette/AnyIO while importing `TestClient`; there are no project test failures.

## Checks run

- `uv run --group test pytest -q` — 345 passed.
- `uv run --directory backend --group quality ruff check casino tests run_api.py` — passed.
- `uv run --directory backend --group quality ruff format --check casino tests run_api.py` — passed.
- `uv run --group quality mypy --show-error-codes --python-version 3.10 backend/casino backend/run_api.py` — passed for both `linux` and `win32` targets.
- `npm run test:unit` — 15 passed.
- `npm run lint` and `npm run build` — passed.
- `npm run build:desktop` and `npm run smoke:sidecar` — passed on Windows.
- `npm run tauri:build` — not available locally because Cargo and Visual Studio C++ Build Tools are missing.
- [GitHub Actions run 39625137964](https://github.com/gr33nmars-hub/repo/actions/runs/39625137964) for `8b8d199` — backend Python 3.10/3.12, frontend, Windows installer, and sidecar smoke-test jobs succeeded.
