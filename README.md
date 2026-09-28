# NOIR Casino Club

Локальное казино на виртуальных фишках. Приложение не принимает реальные деньги, не поддерживает платежи, депозиты или вывод средств.

## Запуск

Нужны Node.js, Rust (MSVC toolchain) и `uv`:

```powershell
uv sync
cd frontend
npm install
npm run tauri:dev
```

Для разработки интерфейса в браузере запустите API и Vite в двух терминалах:

```powershell
# Корень проекта
uv run --directory backend python run_api.py

# frontend/
npm run dev
```

API должен слушать loopback `127.0.0.1`. Для Windows-сборки из корня выполните `uv sync --group build`, затем из `frontend/` соберите установщик. Tauri запускает `npm run build:desktop` перед bundle: команда собирает Python sidecar и frontend assets.

`npm run tauri build` и `npm run tauri:dev` автоматически выбирают rustup toolchain `stable-x86_64-pc-windows-msvc`, загружают MSVC/Windows SDK через `VsDevCmd` и используют отдельный каталог `frontend/build/tauri-msvc` для Cargo. Нужны rustup, Visual Studio C++ x64 tools и Windows SDK. На текущей машине обе цели собираются в MSI и NSIS; установленный runtime требует отдельного smoke.

## Архитектура backend

```text
api.py, api_schemas.py, api_errors.py   FastAPI composition, HTTP и DTO
application/commands.py                Транзакционные игровые/wallet use cases
application/queries.py                 Read-side state projection
application/ports.py                   CasinoRepository protocol
application/service.py                 CasinoService и кэш состояния/revision
domain/                                 Правила, игровые модели, ledger types, verifier
persistence/sqlite.py                   SQLite adapter и атомарная запись агрегата
persistence/migrations.py               Schema migrations v0–v4
persistence/codecs.py                    Сохранения и совместимость форматов
recovery.py, process_lock.py             Offline recovery и process lock
```

`CasinoService` координирует application commands через `CasinoRepository` и типизированные read/write Unit of Work; `PlayerRepository` реализует порт на SQLite, а connection остаётся внутри persistence adapter. Каждая команда работает в одной `BEGIN IMMEDIATE` транзакции и сохраняет профиль, активную раздачу, историю, типизированные ledger movements и idempotency response вместе. `CasinoGame` остаётся контрактом для one-shot слотов и рулетки; blackjack — отдельный stateful aggregate. Верхнеуровневые `casino.session`, `casino.storage`, `casino.blackjack` и соседние модули остаются compatibility exports для внешних callers; production код и основная тестовая suite используют новые пакеты.

Активная раздача blackjack хранит идентификатор, связанный с записями её ставок; при восстановлении сохранённая сумма ставок сверяется с ledger. Старые снимки без такого идентификатора продолжают загружаться, но для них эта дополнительная сверка недоступна. Состав башмака проверяется по всем шести колодам. Новый башмак создаётся на границе раздач, когда осталось меньше 60 карт.

## Ставка и жизненный цикл

Для каждого действия backend начинает `BEGIN IMMEDIATE`, читает актуальную версию профиля, проверяет idempotency key, правила и баланс, вычисляет исход, затем сохраняет баланс, историю, ledger, полный ответ и ключ до commit. Поэтому параллельные backend-сессии не перезаписывают друг другу раунды. Повтор того же ключа и параметров возвращает сохранённый ответ без второго списания; повтор ключа с другими данными отклоняется. Frontend хранит ключ вместе с точным телом незавершённого запроса и повторяет именно его после сетевого сбоя.

Блэкджек списывает начальную ставку при старте и сохраняет руки, карты дилера, оставшийся башмак и фазу хода. После перезапуска активная раздача восстанавливается. Каждое разрешённое действие обновляет состояние транзакционно; `double`, `split` и страховка списывают дополнительные фишки, а завершение записывает выплату и результат. Пополнение доступно только после завершения активной раздачи. При целочисленных фишках ставки должны быть чётными, чтобы выплата 3:2 и возврат половины при сдаче оставались точными.

## Правила и выплаты

Лимиты ставок находятся в `GameRules`, blackjack — в `BlackjackRules`, рулетка — в `RouletteRules`, слоты — в `SlotRules`. Конфигурации проверяются при создании. Изменяйте параметры там, а не в HTTP-обработчиках.

- **Европейская рулетка:** равномерный выбор кармана `0..36`; красные номера заданы в `RED_NUMBERS`, остальные ненулевые — чёрные. Красное/чёрное возвращают `2 × ставка` (ставка включена); зеро возвращает `36 × ставка` (35:1 выигрыш плюс ставка). Существующие варианты UI/API — `red`, `black`, `zero`.
- **Блэкджек:** шесть колод в башмаке; туз считается за 11 и понижается до 1 при переборе; дилер стоит на любом 17, включая soft 17. Дилер получает закрытую карту и проверяет натуральный блэкджек при открытом тузе или карте стоимостью 10. Натуральный блэкджек платит `ставка × 5 / 2` вместе со ставкой, обычная победа — `2 × ставка`, push — `ставка`, проигрыш — 0. Натуральный блэкджек возможен только на первых двух картах исходной руки; 21 после добора или разделения пары оплачивается как обычная победа.
- **Решения игрока:** взять карту, остановиться, удвоить ставку и получить ровно одну карту, разделить пару одинаковой стоимости (10/J/Q/K совместимы) до четырёх рук с отдельной равной ставкой, сдаться на первых двух картах после проверки дилера и получить половину ставки обратно. После разделения первая рука получает карту и играется до конца, затем следующая получает свою карту; после разделения можно удваивать. На каждую руку из разделённых тузов выдаётся ровно одна карта. При открытом тузе дилера доступна страховка до половины исходной ставки, оплачиваемая 2:1 при натуральном блэкджеке дилера. Недоступные по фазе или балансу действия отклоняются сервером.
- **Слоты:** каждый из трёх барабанов имеет явно заданную последовательность символов, повтор символа задаёт его вес. Тройка платит настроенный множитель от 4× до 24× (включая ставку), любая пара возвращает 1×, прочее — 0. Интерфейс показывает таблицу выплат и теоретическое ожидание, рассчитанное по текущей конфигурации барабанов; это ожидание не предсказывает результат отдельной сессии.

Слоты публикуют SHA-256 commitment следующего server seed в `/api/state`, принимают client seed и ожидаемый commitment, затем в результате раскрывают seed и позиции барабанов. Клиент пересчитывает HMAC-SHA-256 позиции и выплату; повторное использование idempotency key не вращает seed второй раз. Рулетка и блэкджек используют `secrets` через `SecureRandom`. Это проверка последовательности локальной игры, а не требование реального денежного казино.

Правила блэкджека выбраны по [главе 633a кодекса Пенсильвании](https://www.pacodeandbulletin.gov/secure/pacode/data/058/chapter633a/chap633atoc.html) и [описанию классического стола комиссии Невады](https://www.gaming.nv.gov/siteassets/content/divisions/technology/rules-of-play/gameace-live-blackjack.pdf). Параметры стола явно показаны в интерфейсе; дополнительные варианты из источников, например Seven Card Charlie, в игру не добавлены.

## Хранилище и перенос профиля

SQLite-файл по умолчанию: `~/.noir-casino/casino.sqlite3`. При первом создании базы профиль `~/.noir-casino/player.json`, включая активное состояние блэкджека, импортируется в транзакции. Исходный JSON не удаляется. Если файл повреждён или активная раздача не проходит проверку, запуск завершается с ошибкой вместо тихого сброса прогресса. Можно задать `NOIR_CASINO_SAVE_PATH` на путь SQLite; для совместимости заданный путь с суффиксом `.json` означает соседний `.sqlite3` и этот JSON источник миграции.

Таблица `ledger` содержит opening balance и движения виртуальных фишек с балансом после каждой записи; `processed_requests` хранит использованные ключи, подпись операции и ответ. При запуске проверяется непрерывность ledger и равенство итогового баланса профилю. Несовпадение блокирует запись, не исправляя баланс автоматически. Полная история раундов сохраняется для статистики, API показывает последние 12 записей. SQLite атомарно сериализует операции нескольких локальных соединений и процессов.

Создать backup и проверить его можно командами `uv run --directory backend python -m casino.recovery backup <backup.sqlite3> --source <casino.sqlite3>` и `uv run --directory backend python -m casino.recovery verify <backup.sqlite3>`. Для восстановления backend должен быть остановлен; CLI также проверяет межпроцессную блокировку перед заменой файла. Восстановление в новый путь: `uv run --directory backend python -m casino.recovery restore <backup.sqlite3> <casino.sqlite3>`. Для существующего назначения нужен `--replace`; перед заменой команда сохраняет отдельную копию, в том числе если совпала UTC-секунда с предыдущей операцией. Старый `player.json` сохраняется рядом с SQLite как `player.pre-migration-<UTC timestamp>.json` до импорта.

## HTTP API

Маршруты и формы ответов state/history сохранены. Для POST, меняющих состояние, обязателен `idempotency_key`:

```http
GET  /api/health
GET  /api/state
POST /api/games/roulette/play
Content-Type: application/json
{"bet": 20, "choice": "zero", "idempotency_key": "uuid"}

POST /api/blackjack/start
{"bet": 20, "idempotency_key": "uuid"}

POST /api/blackjack/action
{"action": "stand", "idempotency_key": "uuid"}

POST /api/refill
{"idempotency_key": "uuid"}
```

Ошибки имеют поля `code` и `detail`: неверная игровая команда — 400 (`invalid_request`), неверный sidecar token — 401 (`unauthorized`), конфликт idempotency или устаревший slot commitment — 409 (`idempotency_conflict` или `stale_game_state`), ошибка формы запроса — 422 (`invalid_request`). Неизвестные поля запроса запрещены. DTO проверяют форму ответов сервера; существующие URL и поля успешного состояния сохранены. Повторный запрос с тем же ключом и телом вернёт ранее сохранённый ответ. API предназначен только для loopback-доступа.

Для `/api/blackjack/action` допустимы `hit`, `stand`, `double`, `split`, `surrender`, `insurance` и `decline_insurance`. Ответ `/api/state` содержит фазу раздачи, список `hands`, индекс активной руки и `available_actions`; интерфейс включает кнопки по этому списку. Запрос слотов может включать `client_seed` и `expected_server_seed_hash`; устаревший commitment отклоняется до ставки, чтобы два процесса не выдали непроверяемый результат.

## Структура кода

- **Инкапсуляция:** `Blackjack` владеет состоянием колоды/руки и проверяет действия только в активном состоянии.
- **Абстракция:** `CasinoGame.play()` и `RandomSource` задают минимальные контракты.
- **Полиморфизм:** каталог публикует сведения о слотах и рулетке через общий контракт `CasinoGame`; blackjack сохраняет собственную state machine.
- **Композиция:** игра получает RNG и конфигурацию правил; `CasinoService` получает repository port; `create_app()` принимает application service.
- **Разделение ответственности:** транспорт, orchestration, правила домена и SQL находятся в отдельных модулях.

## Проверки

Backend-команды из корня: `uv run --directory backend --group test python -m unittest discover -s tests -q`, `uv run --directory backend --group quality ruff check casino tests run_api.py`, `uv run --directory backend --group quality ruff format --check casino tests run_api.py`, `uv run --directory backend --group quality mypy --python-version 3.10 casino`. Группа `test` содержит Hypothesis для генерации игровых трасс. Frontend-команды из `frontend/`: `npm run test:unit`, `npm run lint`, `npm run build`, `npm run build:desktop`. `npm run tauri build` собирает Windows installer; установленный runtime и sidecar lifecycle нужно smoke-проверить отдельно.
