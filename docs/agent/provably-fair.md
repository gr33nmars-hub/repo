# Проверяемые исходы

## Реализация

Все новые раунды slots, roulette и blackjack используют общий server seed из SQLite metadata. Backend публикует `server_seed_hash = SHA256(server_seed)` в `/api/state`. Старое поле `slots_server_seed_hash` оставлено как совместимый alias; старые сохранения переносят его значение в универсальный ключ без смены уже объявленного commitment.

Команды принимают `client_seed` и необязательный `expected_server_seed_hash`. Desktop клиент передаёт оба значения. Если commitment успел смениться между чтением и записью, команда возвращает stale state до списания фишек. Каждый request остаётся защищён существующим idempotency key. Для каждого раунда nonce равен `0`, потому что seed заменяется после завершения раунда. При активной blackjack раздаче другие игры и пополнение заблокированы, поэтому seed не раскрывается раньше времени.

Backend раскрывает использованный seed в `fairness` завершённой записи истории и генерирует следующий seed в той же write-транзакции, что и результат, ledger и idempotency response. Незавершённая blackjack раздача хранит proof, порядок добора и trace адресатов карт в snapshot. При восстановлении backend проверяет commitment, воспроизводит shoe и сверяет каждую карту с точным адресатом (`dealer` или конкретная рука). Старые snapshots без trace остаются совместимыми, но их завершённые proof-записи помечаются `legacy-unverified`. Writer сохраняет snapshot версии 5; reader принимает версии 2–5, а неизвестные версии отклоняет. После перезапуска колода и доказательство продолжают ту же раздачу.

| Игра | Детерминированное отображение |
|---|---|
| Slots | HMAC-SHA-256 с `client_seed:nonce:reel_index:counter`; rejection sampling выбирает стоп без modulo bias. |
| Roulette | HMAC-SHA-256 с `client_seed:nonce:roulette:counter:0`; rejection sampling отображает число на карман `0–36`. |
| Blackjack | Fisher–Yates по полному башмаку; каждый шаг выбирает индекс через HMAC-SHA-256 и rejection sampling. История содержит порядок добора и адресата каждой карты, которые сравниваются с восстановленной колодой. |

В истории `verified` означает, что backend verifier пересчитал commitment, детерминированный исход и выплату. Для старых roulette/blackjack записей без proof verifier всё ещё проверяет сохранённые правила, исход и выплату: корректные записи показываются как `legacy-unverified`, а повреждённые — как `invalid`. Старые сохранённые записи не пересчитываются задним числом. UI столов и истории не отображает commitment, раскрытый seed, client seed или результат браузерной проверки. Выплату blackjack и статус проверки вычисляет backend.

## Пределы

Это локальное доказательство согласованности. Оно подтверждает, что раскрытый seed соответствует ранее опубликованному hash и что записанный исход получается из описанного алгоритма. Оно не доказывает честность программы, отсутствие подмены бинарного файла или независимость генератора. Владелец машины имеет доступ к локальным файлам сохранения и runtime.

## Проверяемые точки кода

- `backend/casino/domain/provably_fair.py` — HMAC stream, rejection sampling и shuffle.
- `backend/casino/domain/round_verifier.py` — независимая серверная проверка сохранённого исхода.
- `backend/casino/application/commands.py` — commitment check, seed rotation и транзакционная запись proof.
- `frontend/src/features/shared/fairness.mjs` — браузерная проверка отображаемого раунда.
