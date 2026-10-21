# NOIR Casino Club

Десктопное приложение игрового симулятора в стилистике нео-нуар с реализацией криптографической схемы доказательной честности (**Provably Fair** на базе HMAC-SHA256) и транзакционным реестром SQLite (ACID/WAL).

Проект разработан в рамках дисциплин **«Объектно-ориентированное программирование»** и **«Безопасность распределенных приложений»** (МИЭМ НИУ ВШЭ, направление «Информационная безопасность»). Приложение оперирует исключительно учебными виртуальными очками.

---

## Архитектурные особенности и ООП-дизайн

1. **Объектная модель домена (`backend/games/`):**
   - `Card`, `Hand`, `Shoe` — инкапсуляция колоды, динамический пересчет мягких тузов в блэкджеке, детерминированное тасование Фишера-Йетса.
   - `SlotGame`, `SlotConfig` — композиция барабанов и расчет комбинаций выплат.
   - `RouletteGame`, `RouletteConfig` — европейское колесо (37 секторов), вычисление матожидания и исходов.
2. **Криптографическая подсистема (`backend/games/provably_fair.py`):**
   - Генерация серверной энтропии через CSPRNG (`os.urandom`), исключающая уязвимости алгоритма Мерсенна Твистера (`MT19937`).
   - Схема обязательства (Commitment Scheme): хеш $\text{SHA-256}(S_{server})$ передается клиенту **до** размещения ставки.
   - Детерминированный срез исхода через $\text{HMAC-SHA256}(S_{server}, S_{client} : nonce)$.
3. **Персистентность и защита от гонок (`backend/database.py`):**
   - SQLite в режиме **WAL (Write-Ahead Logging)** со строгими `CHECK`-ограничениями на уровне схемы (`balance >= 0`).
   - Атомарное списание `UPDATE player SET balance = balance - ? WHERE id = 1 AND balance >= ?`, исключающее уязвимости состояния гонки (Race Condition / TOCTOU) при параллельных запросах.
4. **Desktop Shell & Presentation:**
   - Легковесный системный контейнер WebView2 через `pywebview` с локальным асинхронным бэкендом на FastAPI.
   - Клиент на React 19 + TypeScript со строгой статической типизацией, поддержкой accessible-стандартов (`aria-*`) и анимациями `requestAnimationFrame`.

---

## Структура репозитория

```
├── app.py                     # Точка входа: запуск Uvicorn-сервера и окна PyWebView
├── pyproject.toml             # Зависимости Python (uv)
├── Semerka.spec               # Конфигурация сборщика PyInstaller (GUI-режим без мигающей консоли)
├── backend/
│   ├── main.py                # REST API эндпоинты (FastAPI, lifespan, CORS)
│   ├── database.py            # SQLite шлюз: ACID-транзакции, потокобезопасные блокировки
│   ├── games/
│   │   ├── provably_fair.py   # CSPRNG, commitment scheme, HMAC-SHA256 генератор
│   │   ├── blackjack.py       # ООП-модель: Card, Hand, Shoe, FSM раунда
│   │   ├── roulette.py        # ООП-модель: RouletteGame, европейские секторы
│   │   └── slots.py           # ООП-модель: SlotGame, барабанные ленты, RTP
│   └── tests/
│       ├── test_games_and_fairness.py         # Юнит-тесты правил и детерминизма
│       └── test_transactions_concurrency.py   # Стресс-тест параллельных списаний (Race Condition)
└── frontend/
    ├── src/
    │   ├── types.ts           # Строгие контракты DTO и сущностей
    │   ├── hooks/useCasino.ts # Управление состоянием клиента и API-вызовами
    │   ├── components/        # Компоненты интерфейса (Lobby, Sidebar, Shell)
    │   └── features/          # Модули игровых залов (Blackjack, Roulette, Slots, History)
    └── vite.config.ts         # Сборка статических ассетов
```

---

## Запуск и разработка

### 1. Подготовка окружения (Python 3.10+)
Установка зависимостей с помощью современного пакетного менеджера `uv`:
```powershell
uv sync
```

### 2. Запуск автоматических тестов
Запуск набора юнит-тестов и стресс-тестов на состояние гонки:
```powershell
$env:PYTHONPATH="backend"
uv run pytest backend/tests/ -v
```

### 3. Запуск десктопного приложения
```powershell
uv run python app.py
```

### 4. Режим веб-разработки (Full-stack)
Терминал 1 (API-сервер):
```powershell
uv run python backend/main.py
```

Терминал 2 (Клиент):
```powershell
cd frontend
npm install
npm run dev
```
Интерфейс будет доступен по адресу `http://localhost:5173`.
