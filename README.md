# NOIR Casino Club

NOIR Casino Club is a local desktop simulator for blackjack, European roulette, and three-reel slots with a single payline. It uses virtual points only: there are no deposits, withdrawals, payments, or real-money prizes.

## Stack

- Python 3.10+, FastAPI, SQLite in WAL mode
- Tauri v2 with a Python API sidecar
- React 19, TypeScript, and Vite
- HMAC-SHA256 round proofs with server-seed commitments and deterministic outcome verification

## Run on Windows

Install [uv](https://docs.astral.sh/uv/), [Node.js](https://nodejs.org/), Rust with the MSVC target, and the Visual Studio C++ build tools.

```powershell
uv sync --all-groups
cd frontend
npm ci
npm run tauri:dev
```

To create the Windows installer:

```powershell
npm run tauri:build
```

The Tauri build runs Vite and packages the FastAPI service as a sidecar. The app stores its local profile under `~/.astoria-casino` to preserve existing saves.

## Development checks

From the repository root:

```powershell
uv run --directory backend --group test pytest -q
uv run --directory backend --group quality ruff check casino tests run_api.py
uv run --directory backend --group quality ruff format --check casino tests run_api.py
uv run --directory backend --group quality mypy --python-version 3.10 casino
```

From `frontend/`:

```powershell
npm run test:unit
npm run lint
npm run build
```

## Project layout

```text
backend/casino/domain/       Game rules, state transitions, fairness algorithms
backend/casino/application/  Use cases and read models
backend/casino/persistence/  SQLite repository, migrations, save codecs
backend/tests/               Domain, API, persistence, and concurrency tests
frontend/src/                React UI and typed API client
frontend/src-tauri/          Tauri v2 app, permissions, and Windows packaging
```

## Fairness

Each round publishes a hash commitment to the server seed. Outcomes are derived from the revealed seed, client seed, and nonce with HMAC-SHA256. The client can verify completed rounds from the disclosed proof data. Changes to the proof format or outcome mapping require compatibility tests and a protocol version change.

## License

MIT. See [LICENSE](LICENSE).
