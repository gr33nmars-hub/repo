# Frontend

React and TypeScript frontend for NOIR Casino Club. The same UI runs in a browser for development and in Tauri for desktop release.

## Local development

Install dependencies with `npm install`. Run `npm run tauri:dev` to start the Tauri window; its `beforeDevCommand` starts the local API and Vite. To work in a browser, start the API from the repository root with `uv run --directory backend python run_api.py`, then run `npm run dev` here.

## Production build

`npm run build` type-checks and builds the Vite assets. `npm run build:desktop` also packages `backend/run_api.py` as the Windows sidecar under `src-tauri/binaries`. `npm run tauri build` creates the configured Windows installer and invokes `build:desktop` through Tauri's `beforeBuildCommand`.

On Windows, `scripts/tauri.mjs` selects the rustup `stable-x86_64-pc-windows-msvc` compiler, loads the Visual Studio C++ and Windows SDK environment through `VsDevCmd`, and uses `build/tauri-msvc` as an isolated Cargo target directory. Both `npm run tauri build` and `npm run tauri:dev` use this wrapper, even when another Rust installation appears earlier on `PATH`. The machine needs rustup, Visual Studio C++ x64 tools, and a Windows SDK.

## Source boundaries

- `src/App.tsx` composes navigation and feature pages.
- `src/features/` contains blackjack, roulette, slots, and history UI.
- `src/hooks/useCasino.ts` owns UI state and operation feedback.
- `src/lib/casino.api.ts` declares endpoint operations; `httpClient.ts` handles HTTP; `casino.commands.ts` persists pending mutations and retries.
- `src/platform/desktopBackend.ts` starts the Tauri sidecar, checks its token/instance nonce, and stops it when the window closes.
- `src-tauri/` configures the native window, permissions, sidecar, and installer bundle.

Run `npm run lint` and `npm run test:unit` for frontend checks. `npm run tauri build` has produced both configured Windows bundles; sidecar shutdown, retry after restart, and restore still need an installed-app smoke check.
