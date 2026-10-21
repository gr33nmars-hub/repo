# Backend audit and refactor status

Updated 2026-10-21 from the current working tree. The audit checks the Python domain, application and SQLite layers, tests, API boundary, and the Windows desktop integration. It describes code behavior; it does not infer who or what authored it. The follow-up fixes recorded here are local and have not been pushed to GitHub.

## Findings and changes

| Priority | Finding | Current status |
| --- | --- | --- |
| High | Blackjack actions could bypass balance checks, and mutable card collections were exposed from round state. | Fixed: `act(action, balance)` is the action entry point; `hand` returns a detached copy; `PlayerHand.cards` and `Shoe` card views are tuples. The engine alone mutates a hand's card list. Tests cover denied double/split, invalid phases, detached state, and immutable card views. |
| High | Blackjack combined game rules, API catalog projection, and save-version handling; `GameResult` also owned API and persistence dictionaries. | Fixed: state, result, and game-catalog projections live in `application/queries.py`; profile/history encoding and decoding live in `persistence/codecs.py`; blackjack save compatibility lives in `persistence/blackjack_codec.py`. Domain models no longer expose API `catalog_info` or `to_dict`/`from_dict` methods. |
| High | Same-balance writes needed a different-key race test. | Covered: `test_concurrency.py` races independent services against one SQLite file and checks the wallet, ledger, and idempotency results. Writes begin with `BEGIN IMMEDIATE`. |
| Medium | API result projections shared mutable nested values with stored game results. | Fixed: `game_result_view()` copies list fields and deep-copies proof, rules, and outcome dictionaries. A regression test mutates every projected value and confirms the domain result is unchanged. |
| Medium | Blackjack retained the caller's mutable fairness proof and returned aliased draw-order/event data from `result()`. | Fixed: proof data is deep-copied at input/output boundaries; draw order and event dictionaries are copied into results. A regression test mutates proof and draw-trace values and confirms round state stays unchanged. |
| Medium | Saved-state validation accepted a doubled stake with `doubled=False`, allowing an impossible hand to resume and offer another double. | Fixed: restored hands must pair the doubled flag with a doubled stake and exactly one drawn card; a regression test rejects the malformed snapshot. |
| Medium | A stale service refresh could publish the new player/Blackjack state and revision before discovering an invalid server seed, leaving an internally mixed snapshot after the refresh failed. | Fixed: load the full persisted snapshot first, checkpoint Blackjack while validating its ledger, then publish player/revision/seed together. Regression test confirms a failed seed load leaves the old in-memory state untouched. |
| Low | Shared server-seed generation and commitment hashing lived in the slots-only module and were imported by Blackjack and application queries. | Fixed: shared helpers now live in `domain/provably_fair.py`; slot-module aliases preserve existing imports and outcome algorithms. Compatibility tests pin those aliases. |
| Low | `DESIGN.md` documented Space/Enter/Escape controls that the Blackjack UI does not implement. | Fixed: the documented shortcuts now match the implemented `1–5` actions and `1–2` insurance choices. |
| Medium | Slots and roulette relied on the application service to reject invalid direct bets; float values and out-of-range amounts were not checked by the domain engines. | Fixed: `GameRules.validate_bet` enforces exact integer type and table limits; slots, roulette, and blackjack call it at their domain boundary. The application service delegates the same rule check before checking wallet balance. |
| Low | Roulette choice and deterministic slot-stop helpers assumed runtime inputs matched their annotations; unhashable roulette choices or a non-list stop container could raise incidental `TypeError`s. | Fixed: roulette validates a string choice before set membership in both ordinary and committed-result paths; slots validate the stop container before inspecting its length. Tests cover malformed values and prove roulette rejects them before drawing. |
| Low | `GameResult` trusted its `fairness` type annotation while persistence/API JSON encoding could reject nested values later. | Fixed: the domain model requires an object-or-`None`, checks strict JSON serialization (`allow_nan=False`), and types the field as `dict[str, Any] | None`; regression tests cover wrong top-level values, unsupported objects, and NaN. |
| Medium | Tests used hand-built ASGI plumbing and inconsistent assertion patterns. | Simplified: backend tests use pytest, and API tests use FastAPI `TestClient` with a fresh database per test. The suite has no `unittest.TestCase` tests. |
| Medium | The checkout mixed Tauri configuration with a partial PyWebView migration. | Corrected: PyWebView entry points and dependency were removed; Tauri starts the API sidecar in packaged builds and the API/Vite processes during development. Public-facing product metadata now says NOIR Casino Club. |
| Medium | Repository docs and release metadata named the old product and described stale commands. | Updated: README, product notes, developer notes, frontend instructions, Tauri metadata, and license now match the current project. The existing `.astoria-casino` save directory and app identifier remain stable to preserve local data and upgrade identity. |
| Low | GitHub Actions used Node 20 action runtimes and floating `ubuntu-latest`. | Fixed in `checks.yml`: updated the official actions to Node 24-compatible releases and pinned Linux jobs to Ubuntu 24.04. |

## Decisions that affect compatibility

- Each committed blackjack round uses a fresh, deterministically shuffled six-deck shoe. A shared shoe across rounds would require a different seed/nonce and save protocol; it is not introduced as a side effect of this refactor.
- The fairness verifier now implements its own proof verification primitives instead of importing production generation helpers. Keep seed encoding, nonce use, shuffle order, wheel mapping, and reel mapping covered by fixed vectors.
- Provably fair bounded sampling rejects ranges outside the SHA-256 space instead of looping forever.
- SQLite save migrations remain forward-only and preserve legacy fixtures. The repository makes an integrity-checked backup before migrating a non-empty save.
- The API token header and save-path environment names retain their Astoria spelling for compatibility. They are internal names, not user-facing product branding.

## Maintainability and publication hygiene

- Ruff reports no unused imports or other configured lint findings. The only `print()` and `console.log()` calls found are deliberate success output from the recovery CLI and packaged-sidecar smoke test; there are no TODO/FIXME/XXX markers, debugger statements, or commented-out code in the reviewed backend/frontend application paths.
- The shared game interface is used by the three shipped games, and SQLite unit-of-work/codec boundaries have multiple concrete responsibilities; no one-use factory or speculative extension point was found worth removing. Keep abstractions that enforce transaction or fairness boundaries.
- The source inventory contains no tracked environment files, credentials, SQLite profiles, compiled executables/libraries, Python bytecode, dependency directories, or build output. `.gitignore` covers local save data and generated artifacts.

## Remaining verification

- The local Windows environment has no Cargo or Visual Studio C++ Build Tools, so the installer cannot be built here. GitHub Actions completed the Windows installer build and packaged-sidecar smoke test successfully.
- The Node 24 action update and Ubuntu 24.04 pin passed in [GitHub Actions run 39628458556](https://github.com/gr33nmars-hub/repo/actions/runs/39628458556). The latest code and workflow passed all jobs, including Windows packaging and sidecar smoke, in [run 39629304074](https://github.com/gr33nmars-hub/repo/actions/runs/39629304074).
- The documentation-only run for `2a0ea26` was still `In progress` when checked on 2026-10-21; frontend and both backend matrix jobs were complete, while the Windows job had no terminal result in the public run summary: [run 39630456080](https://github.com/gr33nmars-hub/repo/actions/runs/39630456080).
- The backend suite emits one upstream deprecation warning from Starlette/AnyIO while importing `TestClient`; there are no project test failures.

## Public repository

- The GitHub repository is public and advertises the MIT license. Its README describes the virtual-chip scope, stack, Windows setup, checks, and fairness model.
- GitHub's About section has no short description or topics yet. Add those when preparing the clean repository reupload; this is presentation metadata, not a source-code blocker.

## Checks run

- On the current working tree, backend pytest reports 371 passed with one upstream Starlette/AnyIO deprecation warning. Ruff check/format and mypy for Python 3.10 on Linux and Windows pass after the atomic stale-refresh fix.
- In a fresh copy of the current source (161 files including the audit/plan; initially no `.git`, `.venv`, Python caches, `node_modules`, or prebuilt sidecar), `uv sync --all-groups` under Python 3.10.21 succeeded and backend pytest reported 371 passed, with one upstream Starlette/AnyIO warning.
- The same clean copy passed Ruff check/format and mypy for Python 3.10 with both `linux` and `win32` targets.
- From the clean copy's `frontend/`, `npm ci` passed with 0 reported vulnerabilities; unit tests reported 15 passed; lint, Vite build, Python 3.10 PyInstaller `build:desktop`, and packaged sidecar smoke passed.
- Full `tauri:build` was not run because Cargo and the MSVC `cl` compiler are unavailable locally. Hosted CI results are for earlier commits and must be rerun after publishing the final source revision.
- [GitHub Actions run 39629304074](https://github.com/gr33nmars-hub/repo/actions/runs/39629304074) for `f5f72a1` — backend Python 3.10/3.12, frontend, Windows installer, and sidecar smoke-test jobs succeeded with the updated action runtimes and Ubuntu 24.04 runners.
