# План устранения AI-слопа и технического долга (NOIR Casino)

> Создан по правилам `/plan-writing` на основе результатов глубокого аудита [`777asino-audit.md`](file:///C:/Users/Фенилэтиламин/.gemini/antigravity/brain/5c53365d-8e42-4483-ba8b-f63a9337a8e0/777asino-audit.md).

## Цель
Устранить фиктивные обещания (fake seed / unverified provably-fair), убрать мертвый и шаблонный код (dead API fields, unused money.ts, triple CSS layers), защитить операции с балансом от race conditions и привести проект к честному, устойчивому виду.

---

## Задачи

### Фаза 1. Чистка фиктивного Provably Fair и dead-полей в API
- [ ] **Задача 1.1: Очистить бэкенд от фейкового seed-хэша и dead-полей**
  - Файлы: [`backend/main.py`](file:///c:/Users/Фенилэтиламин/Desktop/777asino-main/backend/main.py), [`backend/database.py`](file:///c:/Users/Фенилэтиламин/Desktop/777asino-main/backend/database.py)
  - Действие: Убрать хардкод `"server_seed_hash": "a1b2c3d4e5f67890"` из `build_casino_state()`. Удалить неиспользуемые поля `idempotency_key`, `client_seed`, `expected_server_seed_hash` из `PlayRequest` / `BlackjackActionRequest` / `RefillRequest`. Убрать фейковый `"verification_status": "verified"` из сохраняемой истории.
  - Проверка: Запустить `python backend/main.py`, проверить эндпоинт `GET /api/state` — в ответе нет фейковых хэшей и пустых полей.

- [ ] **Задача 1.2: Синхронизировать типы и UI фронтенда**
  - Файлы: [`frontend/src/types.ts`](file:///c:/Users/Фенилэтиламин/Desktop/777asino-main/frontend/src/types.ts), [`frontend/src/features/history/HistoryPage.tsx`](file:///c:/Users/Фенилэтиламин/Desktop/777asino-main/frontend/src/features/history/HistoryPage.tsx)
  - Действие: Удалить неиспользуемые интерфейсы (`FairnessProof`, dead-поля в `RoundResult`). В `HistoryPage.tsx` убрать ложную плашку "Результат проверен", заменить счётчик на реальный контекст ("Последние N раундов").
  - Проверка: Запустить `npm run build` в папке `frontend` — сборка TypeScript проходит без ошибок.

---

### Фаза 2. Безопасность и надежность базы данных (Backend)
- [ ] **Задача 2.1: Атомарность баланса и включение WAL-режима**
  - Файлы: [`backend/database.py`](file:///c:/Users/Фенилэтиламин/Desktop/777asino-main/backend/database.py)
  - Действие: В `get_connection()` добавить `conn.execute("PRAGMA journal_mode=WAL")`. Переписать `deduct_balance()` с проверкой `WHERE id = 1 AND balance >= ?` с вызовом исключения при нехватке фишек.
  - Проверка: Вызов `deduct_balance(9999999)` выбрасывает ошибку и не уводит баланс в минус.

- [ ] **Задача 2.2: Устранить избыточный вызов init_db() на каждый GET**
  - Файлы: [`backend/database.py`](file:///c:/Users/Фенилэтиламин/Desktop/777asino-main/backend/database.py), [`backend/main.py`](file:///c:/Users/Фенилэтиламин/Desktop/777asino-main/backend/main.py)
  - Действие: Убрать вызовы `init_db()` внутри `get_player()`, `get_history()`, `load_blackjack_state()`. Оставить инициализацию только при старте сервера через lifespan-контекст FastAPI.
  - Проверка: Запрос `GET /api/state` не выполняет `CREATE TABLE IF NOT EXISTS` повторно.

- [ ] **Задача 2.3: Исправление CORS и консольного окна PyInstaller**
  - Файлы: [`backend/main.py`](file:///c:/Users/Фенилэтиламин/Desktop/777asino-main/backend/main.py), [`Semerka.spec`](file:///c:/Users/Фенилэтиламин/Desktop/777asino-main/Semerka.spec)
  - Действие: Заменить `allow_origins=["*"]` на локальные origin (`http://127.0.0.1:8765`, `http://localhost:5173`). В `Semerka.spec` установить `console=False`.
  - Проверка: Запуск через uvicorn не выдает CORS-предупреждений; spec-файл валиден.

---

### Фаза 3. Очистка фронтенда от мертвого кода и наслоений стилей
- [ ] **Задача 3.1: Удаление неиспользуемых файлов и мертвого состояния**
  - Файлы: [`frontend/src/lib/money.ts`](file:///c:/Users/Фенилэтиламин/Desktop/777asino-main/frontend/src/lib/money.ts), [`frontend/src/hooks/useCasino.ts`](file:///c:/Users/Фенилэтиламин/Desktop/777asino-main/frontend/src/hooks/useCasino.ts), [`frontend/src/components/shell/AppShell.tsx`](file:///c:/Users/Фенилэтиламин/Desktop/777asino-main/frontend/src/components/shell/AppShell.tsx)
  - Действие: Удалить файл `money.ts`. Убрать из `useCasino.ts` и `AppShell.tsx` бутафорский проп `retryAvailable: false`.
  - Проверка: `npm run build` во `frontend` успешен, лишние импорты отсутствуют.

- [ ] **Задача 3.2: Дедупликация и нормализация CSS**
  - Файлы: [`frontend/src/features/shared/game-ui.css`](file:///c:/Users/Фенилэтиламин/Desktop/777asino-main/frontend/src/features/shared/game-ui.css), [`frontend/vite.config.ts`](file:///c:/Users/Фенилэтиламин/Desktop/777asino-main/frontend/vite.config.ts)
  - Действие: Схлопнуть 3 повторных блока правил `.game-action-primary` и `.game-bet-control` в один чистый блок без взаимных перезаписей. В `vite.config.ts` убрать мусорные пути `src-tauri` из `watch.ignored`.
  - Проверка: Визуальная проверка кнопок и полей ввода в интерфейсе — стили не поломаны, в devtools нет 3-кратного зачеркивания свойств.

- [ ] **Задача 3.3: Очистка AI-копирайта и статусов**
  - Файлы: [`frontend/src/components/lobby/LobbyPage.tsx`](file:///c:/Users/Фенилэтиламин/Desktop/777asino-main/frontend/src/components/lobby/LobbyPage.tsx), [`frontend/src/features/shared/BetControl.tsx`](file:///c:/Users/Фенилэтиламин/Desktop/777asino-main/frontend/src/features/shared/BetControl.tsx)
  - Действие: Заменить шаблонный слоган "Три зала. Одна атмосфера." на честный "Виртуальные фишки. Настоящая механика." В `BetControl.tsx` заменить "Запрос выполняется" на лаконичное "Подождите…".
  - Проверка: В лобби и на кнопках отображаются обновленные тексты.

---

### Фаза 4. Гигиена репозитория и окружения
- [ ] **Задача 4.1: Актуализация .gitignore и .env.example**
  - Файлы: `.gitignore`, `.env.example`
  - Действие: Добавить `.venv/`, `*.exe`, `__pycache__/`, `*.sqlite3` в корень `.gitignore`. Создать файл `.env.example` с документированием `VITE_CASINO_API`.
  - Проверка: `git status` не отслеживает локальные артефакты и кэш.

---

### Фаза X: Финальная сквозная верификация (Always Last)
- [ ] **Задача X.1: Сквозное тестирование сценариев**
  - Действие:
    1. Запустить сервер и открыть клиент.
    2. Сыграть раунд в Блэкджек (hit, stand, split/double).
    3. Сыграть раунд в Рулетку (red/black/zero).
    4. Сыграть раунд в Слоты (проверить корректность анимации и баланса).
    5. Проверить страницу Истории: записи честные, без ложных плашек.
    6. Проверить `npm run build` во `frontend` (чистая компиляция TS).
  - Проверка: Все три игры работают штатно, баланс обновляется атомарно, консоль браузера чиста от ошибок.

---

## Критерии готовности (Done When)
1. В API и на фронтенде нет ни одного упоминания статичного "server_seed_hash: a1b2c3d4e5f67890" или фейкового "verified".
2. В коде нет неиспользуемых полей (`money.ts`, `retryAvailable`, dead API properties).
3. Стилизация `.game-action-primary` и общих контролов избавлена от 3-кратных перезаписей.
4. База данных защищена от отрицательного баланса через условие в SQL и работает в WAL-режиме.
5. `npm run build` проходит без предупреждений и ошибок.
