# Документация NOIR Casino Club

Эта страница — карта документов для разработчиков и AI-агентов. Поведение сверяйте с кодом; документы описывают назначение, принятые решения и договорённости.

## Текущий контекст

- [Контекст проекта для агента](agent/project-context.md) — продуктовые границы, схема компонентов, потоки данных, контракты, команды разработки и карта тестов.
- [Проверяемые исходы](agent/provably-fair.md) — commit/reveal алгоритм, его реализация для игр и пределы локальной проверки.
- [Соответствие ООП-требованиям](agent/oop-compliance.md) — объектная модель, custom mapping и отчёт сессии.
- [Инструкции агенту в корне](../AGENTS.md) — короткие обязательные правила при работе с репозиторием.
- [llms.txt](../llms.txt) — компактный индекс ключевых материалов и точек входа в код.
- [README проекта](../README.md) — запуск, игровые правила, хранилище, HTTP API и команды проверок.
- [Frontend README](../frontend/README.md) — запуск UI, Tauri build и frontend границы.
- [PRODUCT.md](../PRODUCT.md) — цель, пользователи, возможности и ограничения продукта.
- [DESIGN.md](../DESIGN.md) — дизайн-токены, layout, доступность и визуальные правила.

## Архитектурные решения

ADR фиксируют принятые решения и причины. При конфликте сначала проверьте, соответствует ли реализации текущее решение; не считайте ADR описанием каждого текущего файла.

- [ADR-001: локальный модульный монолит](architecture/ADR-001-local-modular-monolith.md)
- [ADR-002: граница application и persistence](architecture/ADR-002-application-and-persistence-boundary.md)
- [ADR-003: ledger как проверяемая история баланса](architecture/ADR-003-ledger-as-auditable-balance.md)
- [ADR-004: версия правил и проверка результата](architecture/ADR-004-versioned-game-rules.md)
- [ADR-005: desktop lifecycle и API transport](architecture/ADR-005-frontend-platform-and-api.md)
- [ADR-006: типизированный transaction boundary](architecture/ADR-006-typed-unit-of-work.md)

## Где менять документацию

| Изменение | Документы для проверки |
|---|---|
| Новые игровые правила, выплаты или seed proof | `README.md`, `PRODUCT.md` при изменении возможностей, ADR-004; реализация в `backend/casino/domain/` |
| HTTP route, DTO, auth или error contract | `README.md`, `frontend/README.md`, ADR-005; схемы в `backend/casino/api_schemas.py` и `frontend/src/types.ts` |
| Сохранение, миграция, ledger или recovery | `README.md`, ADR-002/003/006; реализация в `backend/casino/persistence/` |
| UI маршрут, доступность или визуальный язык | `PRODUCT.md`, `DESIGN.md`, `frontend/README.md`; реализация в `frontend/src/` |
| Tauri lifecycle, сборка или установка | `README.md`, `frontend/README.md`, ADR-001/005; конфигурация в `frontend/src-tauri/` и `frontend/scripts/` |
| Слои, ключевые invariants или команды агента | `AGENTS.md`, `docs/agent/project-context.md`, `llms.txt` |
