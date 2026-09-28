# ADR-006: Типизированная transaction boundary

## Статус

Accepted

## Контекст

`CasinoRepository` открывает одну транзакцию на команду, потому что игровой переход должен атомарно менять профиль, руку, ledger, seed и cached response. До этого application получал connection как `Any` и передавал его в методы repository с параметром `db`. Это скрывало от mypy конкретную зависимость application от SQLite и позволяло случайно вызывать adapter API вне transaction boundary.

## Рассмотренные варианты

| Вариант | Выгода | Цена |
|---|---|---|
| Передавать SQLite connection через application port | Минимум adapter кода; легко использовать любые SQL операции. | Application знает низкоуровневый handle; transaction scope сложно выразить типами. |
| Типизированный transaction-scoped Unit of Work | Application видит только разрешённые операции в границах одной транзакции; adapter владеет connection. | SQLite adapter содержит небольшой forwarding слой; новые операции нужно добавить в UoW protocol. |
| Убрать repository и выполнять SQL рядом с use cases | Меньше интерфейсов для одного хранилища. | Правила игры и транзакционная запись снова зависят от SQLite и теряют тестируемую границу. |

## Решение

`CasinoRepository.read_transaction()` возвращает `CasinoReadUnitOfWork`; `write_transaction()` возвращает его расширение `CasinoUnitOfWork`, которое добавляет операции записи. Application использует эти протоколы для загрузки и проверки снимка, idempotency lookup, seed и atomic save. SQLite adapter хранит connection внутри `SQLiteUnitOfWork`; сырые соединения остаются внутри `persistence.sqlite`.

## Последствия

- Сигнатуры application-порта не содержат `sqlite3.Connection` или `Any` для transaction handle.
- Транзакция по-прежнему охватывает весь сценарий и коммитится только context manager-ом репозитория.
- Существующие публичные методы `PlayerRepository` сохраняются для recovery и совместимых callers, но application use cases их не вызывают.
- Read-only use cases не видят методов записи. Для нового adapter нужно реализовать те же protocols; контракт проверяется mypy и полным backend набором.

## Пересмотреть, если

Появится второй adapter или сценарий, которому нужны capabilities за пределами текущего UoW. Сначала расширить protocol минимальной операцией; не выдавать низкоуровневый connection через порт.
