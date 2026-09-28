# Следующий цикл разработки: проверяемый релиз ранней альфы

Срез: 2026-09-28, проверенное рабочее дерево `D:\pen1s\projects\flet`. Этот план продолжает [исходный аудит и roadmap](backend-refactor-roadmap.md), а не заменяет его findings. В рабочем дереве есть незакоммиченные backend/frontend изменения и новые пакеты `backend/casino/{application,domain,persistence}`; перед каждым этапом сверять их фактический diff и сохранять соседнюю работу. Статусы ниже подтверждены текущими файлами и командами.

## Цель и проверенный исходный уровень

Цель — довести уже внедрённые расчёты и транзакции до безопасного обновления сохранений и воспроизводимого desktop-релиза на виртуальных фишках. Правила v1 остаются прежними: европейская рулетка 0–36 с возвратом 2×/36×; слоты с текущими тремя лентами и RTP `454/512 = 88,671875%`; blackjack с шестью колодами, S17, peek, 3:2, late surrender, double после split, максимум четырьмя руками и одной картой на разделённого туза. Изменение любого из этих параметров — отдельное продуктово утверждённое правило и новая версия, а не побочный эффект рефакторинга.

Повторно запущено на этом срезе после появления пакетов application/domain/persistence:

| Проверка | Результат |
|---|---|
| `uv run --directory backend --group test python -m unittest discover -s tests -q` | 92 теста, OK на Python 3.12 (2026-09-28), включая property-based blackjack state machines, application/domain error boundary и compatibility facade tests. |
| `uv run --no-project --python 3.10 --with fastapi --with uvicorn --with hypothesis --directory backend python -m unittest discover -s tests -q` | 92 теста, OK на Python 3.10 (2026-09-28). |
| `uv run --directory backend --group quality mypy --python-version 3.10 casino` | OK, 36 исходных файлов. |
| `uv run --directory backend --group quality ruff check casino tests run_api.py` | OK. |
| `uv run --directory backend --group quality ruff format --check casino tests run_api.py` | OK, 48 файлов. |
| `frontend`: `npm run test:unit`, `npm run build`, `npm run lint` | 9/9 тестов и production build — OK; дополнительно close coordinator проверяет порядок shutdown/destroy, повторные запросы и сбой остановки. `npm run lint` проходит без предупреждений. |
| `frontend`: `npm run build:desktop` | PyInstaller sidecar и Vite production assets успешно собраны из чистого источника на Python 3.12; фактический bundle также проверен полной Tauri сборкой ниже. |
| `cargo check --manifest-path src-tauri/Cargo.toml` из `frontend` | Прямой запуск использует GNU Rust из Chocolatey и падает на отсутствующем `dlltool.exe`. Проверка с rustup MSVC `cargo` и явным `RUSTC`, а также cold release build проходят через `scripts/tauri.mjs`; артефакты направлены в отдельный `%TEMP%` target-каталог. |
| `npm run tauri -- build --no-bundle --config '{"build":{"beforeBuildCommand":""}}'` через `scripts/tauri.mjs` | Текущий source и frontend dist собраны в `frontend/build/tauri-msvc/release/noir-casino.exe` без перезаписи существующего ignored sidecar binary. Packaged executable получил native Windows `WM_CLOSE`: окно и sidecar завершились; отдельный `native-close.sqlite3` прошёл `recovery verify`. MSI/NSIS clean build и full gameplay/retry/restore проверены выше на snapshot `d11c0af`. |
| `git diff --check` | Код возврата 0; Git сообщает только предстоящее преобразование LF в CRLF. |

Подтверждённая игровая регрессия в этих проверках не обнаружена. Нижеследующие риски явно разделены на **проверенный дефект**, **долг с видимым в коде механизмом** и **выпускной пробел**, который ещё требует испытания. Не объявлять потерю пользовательских данных или ошибочную выплату уже случившимся фактом без отдельного воспроизведения.

## Текущие статусы и целевая граница модулей

| Этап | Статус на проверенном срезе | Подтверждение / оставшийся риск |
|---|---|---|
| N0 | Готово | Зафиксированы schema v0–v4, legacy/corrupt JSON, blackjack v2–v5, API golden shapes и конфликт неоднозначного старого idempotency key; слоты перебраны по всем 512 позициям и roulette по 37 исходам независимыми ожидаемыми таблицами. |
| N1 | Готово | `persistence/sqlite.py` проверяет, резервирует и транзакционно обновляет v0→v4; тесты внедряют отказ после каждого DDL/metadata шага и проверяют откат на исходную схему. Синтетические старые snapshots восстанавливаются. |
| N2 | Готово для локальной модели сохранения | Backup/restore, повреждённая цель, checkpoint WAL, pinned reader и запрет замены базы, открытой backend, проверены тестами. Восстановленная копия v4 с активной blackjack рукой открыта latest NSIS приложением; рука и башмак восстановились, stand завершил её без расхождения баланса/ledger. |
| N3 | Готово | `PlayerRepository.save` требует key, signature, типизированные `LedgerMovement`, response и активную транзакцию; проверяет сумму движений и ledger chain. SQL failure test подтверждает rollback профиля, ledger, кеша ответа и состояния в памяти. |
| N4 | Готово для правил v1 | Слоты/рулетка исчерпывающе сверяются с независимыми векторами; verifier тестирован на natural, insurance, surrender, double, split и S17. Старые результаты помечаются `legacy-unverified`. |
| N5 | Готово для проверенного desktop flow | Packaged WebView прошёл committed blackjack start → injected HTTP 502 → reload → pending banner → retry того же ключа; запрос был committed один раз и завершил natural blackjack 3:2. Backup/restore с активной рукой также прошёл: после relaunch приложение восстановило руку и рассчитало её через `stand`. Итоговая isolated restored DB: `quick_check=ok`, balance 2525, четыре раунда, семь cached requests, девять ledger rows; prefix chain и сумма ledger совпадают с профилем. Отдельный Vite flow покрывает потерю ответа после backend restart. |
| N6 | Готово для проверенной матрицы | 92 backend tests проходят на Python 3.10/3.12. Deterministic traces и два Hypothesis state machines проверяют blackjack правила, legal actions, restart/restore, баланс и ledger. Независимый verifier сверяет все 512 slot stops, 37 roulette pockets и blackjack settlement fixtures; два subprocess-теста покрывают разные ключи и конкурентный retry одного ключа; SQL/commit/serialization failures проверяют rollback. Architecture fitness tests закрепляют import direction, compatibility фасады сохраняют старые exports. История 10 000 записей (1,88 MB): медиана load 70,32 ms, atomic save 50,62 ms. Установленный close-request lifecycle N7 проверен через зарегистрированный handler; физический native input не проходил ручной проверки. |
| N7 | Готово для проверенного desktop lifecycle | MSVC `cargo check` и MSI/NSIS сборки успешны, включая latest-source clean checkout `d11c0af`; оба installer артефакта подтверждены. Latest NSIS installed smoke подтвердил sidecar startup, auth health через UI, gameplay, lost-response retry, backup/restore активной руки и продолжение после полного перезапуска. `tauri://close-requested` через event bridge остановил sidecar и закрыл установленное окно. Дополнительно packaged executable, собранный из текущего дерева, получил native Windows `WM_CLOSE`: окно завершилось, sidecar вышел, изолированная SQLite прошла `recovery verify`. Физический клик по titlebar не выполнялся; `core:window:destroy` обходит close handler и не считается проверкой этого lifecycle. |
| N8 | Готово для ранней локальной альфы | На read-only копии пользовательской базы проверены v3→v4 migration, backup и restore; `quick_check=ok` на source/backup и common columns ledger/profile/processed_requests/metadata совпадают, schema delta — nullable v4 `ledger.reason`. Latest NSIS установлена в temp-каталог; backup/restore отдельного тестового профиля с активной рукой и UI settlement прошли. Packaged startup/gameplay/retry/recovery/shutdown путь проверен; native `WM_CLOSE` текущей сборки завершил окно и sidecar, save прошёл recovery verify. Перед широким распространением вручную проверить физическую titlebar кнопку на целевой машине. Исходный audit roadmap обновлён результатами. |

Текущая целевая граница — локальный модульный монолит: `api.py`/`api_schemas.py` принимают HTTP и формируют DTO; `application/service.py` координирует use cases через `CasinoRepository` и read/write Unit of Work protocols; `domain/` содержит правила, модели и доменные ошибки; `application/` содержит сценарии, stale-state и idempotency ошибки; `persistence/sqlite.py` держит connection и хранит профиль, ledger и ключи повторов. `session.py`, `storage.py`, `blackjack.py`, `games.py`, `models.py`, `core.py`, `slot_fairness.py` и `errors.py` остаются compatibility facades. Fitness test удерживает canonical packages от импорта root error facade; удаление фасадов отложено до проверки внешних callers. Подробная структура и ADR — в [архитектурном плане реализации](architecture-implementation-plan.md), решение о transaction boundary — в [ADR-006](docs/architecture/ADR-006-typed-unit-of-work.md).

| Компонент | Ответственность и объектная граница |
|---|---|
| `CasinoService` | Сценарии игры/refill, атомарная последовательность `read → validate → decide → persist`, кэш идемпотентного ответа; не содержит SQL. |
| `PlayerRepository` + `CasinoRepository` Protocol | Адаптер SQLite и минимальный порт для application service; транзакции, миграция, сохранение агрегата и ledger. Не дублировать business rules во writer. |
| `Blackjack`, `BlackjackRound`, `PlayerHand`, `BlackjackRules`, `Card` | Blackjack rules/state machine, композиция раунда из рук/карт и injectable RNG; snapshot должен сохранять версию и состояние башмака. Не вводить наследование для каждого действия. |
| `SlotMachine`, `Roulette`, `CasinoGame`, `GameRules` | Единый каталог/полиморфный контракт простых игр; расчёты выплат и rule snapshot принадлежат domain. Blackjack подключается к каталогу через уже используемый общий контракт, без переезда его особой state machine в generic base class. |
| `GameResult`, rule metadata/verifier | Типизированный результат и его историческая доказуемость; legacy результат остаётся отображаемым и помечается непроверенным. |
| FastAPI routes/DTO | Проверка входного формата, auth локального sidecar и перевод domain/application errors в стабильные HTTP ответы; не рассчитывают баланс или исход. |

Основные ООП средства здесь — инкапсуляция состояния blackjack, композиция `round → hands → cards/rules`, абстракция RNG/repository port и полиморфизм игрового каталога. Наследование использовать лишь там, где существует substitutable контракт; не добавлять base classes ради защиты проекта или SOLID. Это оставляет поведение объяснимым и тестируемым без декоративных паттернов.

## Критический путь и задачи

Каждая задача — отдельный reviewable результат. Порядок `N0 → N1 → N2 → N3 → N4 → N5 → N6 → N7 → N8`; подготовка недостающих fixtures и Windows toolchain может идти параллельно, но выпускные ворота `N8` всегда последние. Уже существующие пункты сначала допроверить, а не переписывать с нуля. Для каждой задачи указаны изменение, основание, затрагиваемые файлы, совместимость и критерий готовности.

### N0 — Зафиксировать базу и протоколы до новых миграций · P0 · без зависимостей

- **Изменение:** дополнить существующие `backend/tests/fixtures/save-v0.sql`…`save-v4.sql`, fixtures legacy/corrupt `player.json`, blackjack snapshots v2–v5 и API contract синтетической ambiguous-ledger историей и golden HTTP ответами. Зафиксировать точные правила v1 и независимые математические векторы. Реальные пользовательские данные в репозиторий не добавлять.
- **Основание:** `backend/casino/persistence/sqlite.py` меняет схему при открытии; `backend/casino/domain/blackjack.py` читает несколько форматов; одних 64 тестов недостаточно, чтобы доказать перенос всех старых сохранений. Это выпускной пробел, не подтверждённое повреждение.
- **Файлы:** `backend/tests/fixtures/`, `backend/tests/test_recovery.py`, `test_blackjack.py`, `test_api_auth.py`, `test_round_verifier.py`, `README.md`.
- **Совместимость:** fixtures сохраняют исходные байты и ожидаемые результаты v1; старые кейсы с неизвестным происхождением ledger помечаются `ambiguous`, а не «исправляются» искусственно.
- **Готово:** команда тестов воспроизводит текущие публичные ответы и все известные входные версии; независимый SQL-запрос даёт `balance = Σledger.delta` для валидных snapshots; повреждённые fixtures отвергаются без записи в исходник.

### N1 — Сделать обновление SQLite предварительно проверяемым и обратимым · P0 · после N0

- **Изменение:** закончить и независимо проверить реализованные `quick_check`, SQLite backup, транзакционные шаги `v0→v1→v2→v3→v4` и publication `user_version`; добавить fault injection после каждого DDL/metadata шага. Существующую v4 схему не менять без причины.
- **Основание:** `backend/casino/persistence/sqlite.py` уже содержит backup и upgrades; текущие tests подтверждают upgrade fixtures и один rollback case, но не отказ на каждой точке миграции. Остаток — тестовый/recovery gate, а не заявление о текущей частичной миграции.
- **Файлы:** `backend/casino/persistence/sqlite.py`, facade `backend/casino/storage.py`, `backend/casino/recovery.py`, `backend/tests/test_recovery.py`, `README.md`.
- **Совместимость:** сохранённый v4 не переписывать без причины; новые структуры вводить только после успешного preflight. База более новой версии по-прежнему отвергается. Downgrade не выполнять; rollback — через проверенный backup после остановки backend.
- **Готово:** для каждой версии fixture upgrade даёт ту же руку/башмак/историю/баланс/ledger; инъекция отказа после каждого DDL/metadata шага оставляет исходную базу читаемой старым кодом либо проверенную восстанавливаемую копию; `user_version` никогда не опережает фактическую схему.

### N2 — Проверить и обезопасить ручное восстановление · P0 · после N0 и N1

- **Изменение:** сделать требование «backend остановлен» исполнимым предусловием для `restore --replace` или ввести межпроцессную эксклюзивную блокировку на весь lifecycle. Перед заменой проверять источник и резервную копию назначения; обрабатывать WAL/SHM без потери подтверждённых транзакций; при конфликте имени backup не перезаписывать его. Реализовано: перед заменой destination WAL checkpoint'ится и база переводится в DELETE journal mode, orphan sidecar при отсутствующем destination вызывает отказ. Осталось добавить сценарий dry-run на **копии** пользовательского сохранения, если оно доступно.
- **Основание:** текущие `backend/casino/recovery.py` и `process_lock.py` уже блокируют restore на время работы backend. Оставшийся риск — неполная проверка взаимодействия блокировки с WAL/SHM и smoke приложения, не отсутствие lock.
- **Файлы:** `backend/casino/process_lock.py`, `backend/run_api.py`, `backend/casino/recovery.py`, `backend/casino/persistence/sqlite.py`, `backend/tests/test_recovery.py`, `README.md`.
- **Совместимость:** CLI `backup/verify/restore` и флаг `--replace` оставить; конфликт живого backend должен давать явную ошибку до замены. Не переносить и не стирать оригинал при неудаче.
- **Готово:** тест с живым writer отказывает безопасно; restore с закрытым backend, активным WAL и повреждённым назначением сохраняет подтверждённый баланс и backup; повторный restore в ту же секунду не затирает первую копию; `verify` не меняет проверяемый файл.

### N3 — Закрыть обход игрового ledger через общий writer · P0 · после N1

- **Изменение:** довести уже обязательные `request_key`, `signature`, movements, cached response и транзакцию до явного типа операции; запретить произвольную строку `entry_type` и определить именованную корректировку для тестового bootstrap. Реализовано через `LedgerEntryType`, `LedgerMovement` и обязательный reason для `profile_adjustment`.
- **Основание:** `backend/casino/persistence/sqlite.py::save` принимает только типизированные movements, проверяет дельту относительно баланса и активную транзакцию; остаётся доказать rollback при ошибке на каждом шаге записи.
- **Файлы:** `backend/casino/persistence/sqlite.py`, `backend/casino/application/ports.py`, `backend/casino/application/service.py`, тесты `backend/tests/`.
- **Совместимость:** старые уже записанные `profile_adjustment` не удалять и не переименовывать; читатель остаётся совместимым. Изменение внутреннего writer не должно менять URL и JSON HTTP.
- **Готово:** невозможно изменить persisted balance через публичный repository writer без явного типизированного основания; для каждой игровой операции проверено `new_balance = old_balance + Σmovements`, один response на один ключ и полный rollback при отказе записи.

### N4 — Привязать результаты к версии правил и проверяемому исходу · P1 · после N1 и N3

- **Изменение:** сохранить уже добавленные `rule_version`/fingerprint/snapshot/outcome, строгую офлайн-проверку slot proof и `legacy-unverified`; дополнить fixtures round-trip и независимым oracle для всех 512 slot и 37 roulette исходов, а также blackjack settlement. Новые версии правил добавлять только с отдельным решением; RTP UI оставить округлённым представлением точного результата.
- **Основание:** каноническая реализация теперь в `backend/casino/domain/{models,games,blackjack,rule_metadata,round_verifier}.py`; root modules — compatibility facades. `backend/tests/test_round_verifier.py` содержит проверку отдельных примеров, а не полного пространства исходов. Это долг полноты доказательства, не установленная ошибка v1 выплат.
- **Файлы:** `backend/casino/domain/`, `backend/casino/api_schemas.py`, `backend/tests/test_round_verifier.py`, `backend/tests/test_games.py`, `frontend/src/types.ts`, `frontend/src/features/slots/slotFairness.mjs`, `frontend/tests/slotFairness.test.mjs`.
- **Совместимость:** новые поля только добавочные и `response_model_exclude_unset` не должен исчезнуть; reader принимает старую историю без version/proof. Не «доверять» старому `details` как исходному pocket и не пересчитывать старые выплаты по новым правилам.
- **Готово:** round-trip новой и старой истории, вектор проверки proof до и после смены конфигурации лент, 512 исходов слотов и 37 исходов рулетки по независимому oracle; frontend и backend дают одинаковый вердикт для повреждённого proof.

### N5 — Завершить сквозной контракт повторов после неопределённого ответа · P1 · после N3 и N4

- **Изменение:** покрыть HTTP + `pendingMutations` + UI: committed POST с потерянным ответом, reload приложения, повтор прежнего тела/ключа; конфликт другого payload с тем же ключом; pending барьер для параллельных действий. В source UI и packaged Tauri WebView эти сценарии проверены с HTTP 502, внедрённым после commit: banner пережил reload, retry получил кэшированный ответ и не добавил stake повторно. В packaged UI повтор разрешил natural blackjack 3:2. Сохранённый pending формат и ошибки `400/401/409/422` покрыты unit/API tests; slot proof проверяется после изменения commitment/configuration.
- **Основание:** `frontend/src/lib/casino.api.ts` сохраняет pending body/key, `HistoryPage.tsx` показывает verification status; API test проверяет lost response/service restart/retry/409, а packaged WebView подтвердил commit-before-502, reload/retry и один ledger settlement. Активная рука из восстановленного backup была рассчитана после запуска приложения.
- **Файлы:** `backend/casino/api.py`, `api_schemas.py`, `frontend/src/lib/casino.api.ts`, `pendingMutations.mjs`, `frontend/src/hooks/useCasino.ts`, `frontend/src/features/slots/SlotsPage.tsx`, `frontend/tests/`, `backend/tests/test_api_auth.py`.
- **Совместимость:** оставить существующие URL, поля успеха и `detail`; новый `code` добавлять без breaking change. Pending записи прежнего формата читать или безопасно помечать для ручного восстановления; не выполнять новый POST с новым ключом при неизвестном исходе старого.
- **Готово:** API и packaged UI lost-response/reload/retry не дублируют settlement; 400/401/409/422 имеют ожидаемое поведение pending store; slots не показывают «verified» при изменённом commitment, stops, symbols или payout.

### N6 — Усилить доменную проверку реальных инвариантов · P1 · после N3–N5

- **Изменение:** дополнить нынешние deterministic тесты model/property-based трассами blackjack (insurance, natural, soft 17, split/resplit aces, отказ draw и save), конкурентными процессами SQLite и fault injection на SQL/commit/serialization. Независимый oracle не должен вызывать ту же функцию payout, что реализация. Измерить время загрузки/записи на большой истории, но оптимизировать JSON/ledger scan только при установленной проблеме.
- **Основание:** `backend/tests/test_blackjack.py` защищает ряд трасс, а `backend/tests/test_recovery.py` проверяет базовую миграцию и lock. Остались не подтверждёнными свойства редких blackjack сочетаний, двухпроцессные денежные операции, сбои при разных SQL записях и стоимость ledger scan. Это пробел покрытия/возможная производительность, без заявления о текущем дефекте.
- **Файлы:** `backend/tests/test_blackjack.py`, `test_games.py`, `test_recovery.py`, новые `test_storage.py`/`test_contract.py` при необходимости; production-файлы только по обнаруженной ошибке.
- **Совместимость:** тесты не должны переписывать v1 payout; если oracle нашёл расхождение, сначала минимальный воспроизводимый кейс и оценка влияния на старые результаты, затем точечное исправление с новой версией правил при смене поведения.
- **Готово:** матрица ниже зелёная на Python 3.10 и 3.12, включая generated stateful traces и reload; два процесса с разными и одинаковыми ключами не теряют состояние; SQL, commit и serialization failures оставляют согласованные профиль, ledger и cached response. Полный packaged WebView flow остаётся отдельным выпускным gate.

### N7 — Привести desktop build и lifecycle к проверяемому состоянию · P1 · после N2 и N5

- **Изменение:** использовать rustup MSVC toolchain и Visual Studio C++ environment. `scripts/tauri.mjs` подключает rustup MSVC Rust, `VsDevCmd` и отдельный target; MSI/NSIS latest-source собраны из чистого Git checkout `d11c0af` после `npm ci` и fresh PyInstaller/Vite build. NSIS installed smoke проверил startup, sidecar/token, blackjack, lost-response/reload/retry, backup/restore активной руки и full app relaunch внутри WebView. `create_app` откладывает SQLite до первого запроса под process lock; frontend ждёт ожидаемый nonce и отменяет незавершённый startup. `tauri://close-requested` проверен через event bridge, а собранный из текущего дерева executable прошёл native `WM_CLOSE`: close handler остановил sidecar и закрыл окно. Физический клик по titlebar мышью не выполнялся.
- **Основание:** packaged app gameplay, recovery и close-request callback подтверждены на latest build; тестовый WebView debugger использовал отдельный user-data folder и save path. Текущая no-console PyInstaller sidecar сборка прошла piped stdio backup/restore smoke. Дополнительно native `WM_CLOSE` на текущем packaged executable закрыл окно и остановил sidecar; изолированная база прошла `recovery verify`. Ручной физический клик по titlebar не выполнялся.
- **Файлы:** `backend/run_api.py`, `frontend/package.json`, `frontend/src-tauri/Cargo.toml`, `tauri.conf.json`, `frontend/src/lib/casino.api.ts`, `README.md`, release script/CI при введении.
- **Совместимость:** не менять стандартный loopback URL/порт без одновременного обновления CSP и WebView-контракта; bundled save path не должен расходиться с dev path незаметно. Не создавать installer из рабочей директории с неучтёнными артефактами.
- **Готово:** `ruff`, `cargo check`, `npm run build:desktop` и Tauri bundle проходят на Windows; latest NSIS установленный app подтверждает startup, sidecar auth, gameplay, lost-response/retry, backup/restore активной руки, состояние после полного relaunch и штатный close-request handler с остановкой sidecar. Текущий packaged executable прошёл native `WM_CLOSE`, sidecar завершился, save прошёл recovery verify. Физический клик по titlebar оставить ручной проверкой на целевой машине перед распространением.

### N8 — Финальная верификация и решение о ранней альфе · P0 release gate · после N0–N7

- **Изменение:** завершить release review: повторить dry-run backup/migrate/verify/restore на копии доступного сохранения; зафиксировать latest installer и smoke; обновить README и исходный audit roadmap; перечислить остаточные `legacy-unverified` данные и ручную проверку native titlebar перед распространением.
- **Основание:** read-only сравнение пользовательской базы с автоматическим pre-migration backup подтвердило `quick_check=ok` и равенство общих колонок; тестовый installed backup/restore с активной рукой, gameplay/retry и close-request shutdown прошли. Физическая titlebar кнопка требует ручного smoke на машине выпуска.
- **Файлы:** `backend/tests/*`, `frontend/tests/*`, `README.md`, `backend-refactor-roadmap.md`, этот файл.
- **Совместимость:** выпуск только с восстановимым backup; при неудаче миграции исходные данные остаются доступны предыдущей версии. Реальные пользовательские сохранения не входят в Git/CI.
- **Готово:** все команды раздела ниже имеют сохранённый результат; нет открытого P0/P1 дефекта, касающегося баланса, payouts, восстановления или неопределённого POST; product rules v1 и ограничения виртуальных фишек явно описаны.

## Матрица обязательных проверок

| Инвариант | Тест/сценарий и ожидаемый результат |
|---|---|
| Баланс/ledger | После каждой операции `balance >= 0`, `balance = Σdelta`, каждый `balance_after` равен префиксной сумме; нет денежной записи без основания. Проверить два процесса, retry и fault injection. |
| Атомарность результата | `profile + blackjack hand/shoe + history + ledger + processed_requests + slot seed` меняются вместе либо не меняются совсем; reload даёт тот же state. |
| Идемпотентность | Одинаковые key+payload возвращают прежний ответ без новой ставки/выплаты; иной payload даёт 409 без изменения; lost HTTP response после рестарта клиента не дублирует settlement. |
| Blackjack v1 | Детерминированные векторы natural 3:2, push, S17, insurance 2:1, surrender 1/2, double/split/resplit/aces и граница башмака; денежная сумма совпадает с settlement каждой руки. |
| Слоты/рулетка | Exhaustive 512/37 outcomes, точный RTP 454/512 и 36/37, целые выплаты, proof/исторический rule version перепроверяются отдельно от реализации. |
| Миграция/restore | v0–v4 SQLite, старый JSON, blackjack v2–v5, WAL и повреждения: старые данные сохраняются; ошибки останавливают импорт; offline restore возвращает исходную раздачу и баланс. |
| API/desktop | Стабильные success DTO, явные 400/401/409/422, Tauri WebView подключается к собственному sidecar, после закрытия/перезапуска state и pending operation согласованы. |

## Команды выпускного набора и границы решения

Из корня: `uv run --directory backend --group test python -m unittest discover -s tests -q`; затем аналогичная команда с `--no-project --python 3.10 --with fastapi --with uvicorn --with hypothesis`; `uv run --directory backend --group quality mypy --python-version 3.10 casino`; `uv run --directory backend --group quality ruff check casino tests run_api.py`; `uv run --directory backend --group quality ruff format --check casino tests run_api.py`. Из `frontend`: `npm run test:unit`, `npm run lint`, `npm run build`, `npm run build:desktop`, `cargo check --manifest-path src-tauri/Cargo.toml`, Tauri bundle и ручной smoke установленной сборки. Проверки реальной пользовательской базы — только на согласованной копии.

Пока не требуется выбирать новые правила игры: v1 уже описан кодом и исходным аудитом. Если позже меняются RTP, paytable, H17/S17, split/surrender или API-breaking контракт, остановить соответствующий этап до продуктового решения и завести новую rule/API version. Требования реального денежного казино в этот план не включены: приложение использует локальные виртуальные фишки.
