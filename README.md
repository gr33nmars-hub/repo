# NOIR Casino Club

Автономное десктопное приложение игрового симулятора в стилистике нео-нуар.
Включает клиент на React / TypeScript, локальный асинхронный сервер на FastAPI, встроенное хранилище SQLite (WAL-режим) и криптографический модуль **Provably Fair** на базе HMAC-SHA256 для детерминированной верификации честности каждого раунда.

> **Примечание:** Приложение оперирует исключительно виртуальными фишками. Реальные платежи и азартные игры на деньги отсутствуют.

---

## Архитектура и технологии

- **Desktop Shell:** PyWebView (интеграция с нативным системным WebView2)
- **Backend:** Python 3.10+, FastAPI, Uvicorn, SQLite3 (ACID, WAL mode, strict CHECK constraints)
- **Frontend:** React 19, TypeScript, Vite, CSS Custom Properties (темная нео-нуар тема)
- **Криптография:**
  - Генерация серверной энтропии через CSPRNG (`os.urandom`) вместо псевдослучайного MT19937.
  - Схема обязательства (Commitment Scheme): SHA-256 хеш сида отдается клиенту до размещения ставки.
  - Детерминированный срез исхода через `HMAC-SHA256(server_seed, f"{client_seed}:{nonce}")`.
  - Возможность ротации и раскрытия предыдущих сидов для независимой математической проверки.
- **Игровая логика:**
  - **Блэкджек (Blackjack):** башмак из 6 колод, тасование Фишера-Йетса, поддержка Hit, Stand, Double, Split (до 4 рук), Surrender, Insurance, правило Soft 17.
  - **Европейская рулетка:** 37 секторов (0–36), расчет выплат по цветам и зеро.
  - **Классические слоты 3×3:** независимые барабанные ленты, взвешенные символы, таблица выплат за пары и тройки (RTP 95.8%).

---

## Структура репозитория

```
├── app.py                     # Точка входа: инициализация FastAPI и окна PyWebView
├── pyproject.toml             # Зависимости Python
├── Semerka.spec               # Спецификация PyInstaller для сборки standalone .exe
├── backend/
│   ├── main.py                # REST API эндпоинты (FastAPI, CORS, Lifespan)
│   ├── database.py            # SQLite: транзакции, WAL, потокобезопасность
│   ├── games/
│   │   ├── provably_fair.py   # CSPRNG, Commitment Scheme, HMAC-SHA256
│   │   ├── blackjack.py       # Доменные модели: Card, Hand, Shoe, FSM
│   │   ├── roulette.py        # RouletteGame, секторы, коэффициенты
│   │   └── slots.py           # SlotGame, выплатные линии
│   └── tests/
│       ├── test_games_and_fairness.py         # Юнит-тесты правил и криптографии
│       └── test_transactions_concurrency.py   # Стресс-тест конкурентных списаний
└── frontend/
    ├── src/
    │   ├── types.ts           # Интерфейсы DTO и типизация
    │   ├── hooks/useCasino.ts # Управление состоянием клиента и API
    │   ├── components/        # Shell, Sidebar, Lobby
    │   └── features/          # Модули залов (Blackjack, Roulette, Slots, History)
    └── vite.config.ts         # Конфигурация сборщика Vite
```

---

## Запуск и разработка

### 1. Установка зависимостей Python
```powershell
uv sync
```

### 2. Запуск тестов
```powershell
$env:PYTHONPATH="backend"
uv run pytest backend/tests/ -v
```

### 3. Запуск десктопного приложения
```powershell
uv run python app.py
```

### 4. Режим веб-разработки (Hot Reload)
**Терминал 1 (API-сервер):**
```powershell
uv run python backend/main.py
```

**Терминал 2 (Frontend):**
```powershell
cd frontend
npm install
npm run dev
```
Интерфейс доступен по адресу `http://localhost:5173`.
