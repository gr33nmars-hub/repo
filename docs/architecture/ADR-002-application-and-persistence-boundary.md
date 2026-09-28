# ADR-002: Application service владеет транзакцией

## Статус

Accepted

## Контекст

Одно изменение игры может обновить баланс, историю, blackjack snapshot, slot seed, ledger и сохраненный ответ для повтора запроса. Разнести эти записи между независимыми операциями небезопасно. Правила игр должны оставаться проверяемыми без FastAPI и SQLite.

## Рассмотренные варианты

| Вариант | Выгода | Цена |
|---|---|---|
| Application service + persistence port | Оркестрация держит полный сценарий в одной транзакции; адаптер можно заменить или подменить на тестовый. | Интерфейс должен не допускать обхода транзакции денежными writers. |
| SQL в доменных объектах | Меньше кода orchestration. | Игровые правила получают зависимость от SQLite и сложнее тестируются изолированно. |
| Отдельные CRUD операции | Простые методы чтения и записи. | Не выражает атомарную связь результата, движений и cached response. |

## Решение

`CasinoService` выполняет команды через `CasinoRepository` protocol и transaction-scoped `CasinoUnitOfWork`. `PlayerRepository` в `persistence.sqlite` открывает одну write transaction и адаптирует SQLite connection к UoW; `migrations` и `codecs` отдельно отвечают за схему и формат снимков. Domain не импортирует SQLite, FastAPI или frontend. Детали контракта UoW фиксирует [ADR-006](ADR-006-typed-unit-of-work.md).

## Последствия

- Профиль, рука, история, movements и idempotency response коммитятся или откатываются вместе.
- SQLite остается конкретным адаптером, который composition root передает сервису.
- Совместимые старые import paths сохраняются на время переноса callers.
- Application use cases не получают SQLite connection и обращаются к операциям только через типизированный UoW.
- Adapter реализует небольшой forwarding слой; прямые методы `PlayerRepository` остаются для recovery и совместимости существующих callers.

## Пересмотреть, если

Появится второй persistence adapter с требованиями, которые не выражаются текущим UoW, либо новый сценарий потребует нескольких согласованных транзакций.
