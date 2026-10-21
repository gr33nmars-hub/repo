# Frontend и desktop shell

Интерфейс использует React 19, TypeScript и Vite. Для Windows приложение упаковывается Tauri v2, а FastAPI запускается как sidecar.

## Разработка

Из каталога `frontend`:

```powershell
npm ci
npm run tauri:dev
```

Команда запускает Vite и локальный API, затем открывает окно Tauri. Для браузерной разработки без desktop shell запустите API командой `uv run --directory backend python run_api.py`, затем выполните `npm run dev`.

## Сборка Windows

```powershell
npm run tauri:build
```

Tauri перед сборкой запускает `build:desktop`: он собирает Vite assets и sidecar `astoria-api-x86_64-pc-windows-msvc.exe` через PyInstaller. Установщик создаётся в `src-tauri/target/release/bundle`.

## Проверки

```powershell
npm run test:unit
npm run lint
npm run build
```

`npm run smoke:sidecar` проверяет собранный Windows sidecar: токен, игровой запрос, сохранение состояния, идемпотентный повтор и остановку API.
