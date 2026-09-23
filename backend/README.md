# Akim City Simulator Backend

Backend учебного симулятора управления районами Астаны. Приложение проверяет набор
управленческих решений, детерминированно применяет их эффекты и рассчитывает Astana
Quality of Life Score. AI не участвует в вычислениях.

## Возможности текущей версии

- версионированный синтетический датасет из 5 районов и 14 мероприятий;
- fail-fast проверка целостности датасета при старте;
- отдельная валидация неполного сценария и сценария для расчёта;
- контроль бюджета, районов, повторов, направлений и несовместимостей;
- эффекты с учётом лага, городские меры, синергии и ограничение `0..100`;
- расчёт районных оценок, критических показателей и итогового Score;
- подробная трассировка эффектов для внешнего AI-консультанта;
- хранение сценариев, решений и результатов в PostgreSQL;
- история расчётов и optimistic locking через версию сценария;
- OpenAPI и автоматические тесты.

## Архитектура

```text
src/city_simulator/
├── domain/          # сущности, правила и чистый расчёт
├── application/     # сценарии использования
├── infrastructure/  # загрузка и проверка датасета
├── presentation/    # FastAPI и HTTP-схемы
├── resources/       # simulation.v1.json
├── core/            # конфигурация
└── main.py           # сборка приложения
migrations/
└── versions/         # версионированная схема PostgreSQL
```

Зависимости направлены внутрь: `presentation -> application -> domain`.
Домен не импортирует FastAPI, Pydantic или инфраструктурные адаптеры.

## Запуск

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn city_simulator.main:app --reload
```

Подключение к базе задаётся через `DATABASE_URL`. Пример находится в `.env.example`.
Локальный файл `.env` не отслеживается Git.

Запуск backend и PostgreSQL через Docker:

```bash
docker compose up --build
```

Swagger UI: <http://127.0.0.1:8000/docs>

Полный контракт и порядок подключения frontend:
[`docs/frontend-integration.md`](docs/frontend-integration.md).

## API

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/api/v1/health` | Проверка процесса |
| `GET` | `/api/v1/ready` | Проверка подключения к базе |
| `GET` | `/api/v1/catalog` | Версии и правила симуляции |
| `GET` | `/api/v1/indicators` | Справочник показателей |
| `GET` | `/api/v1/districts` | Исходные районы |
| `GET` | `/api/v1/measures` | Каталог мероприятий |
| `POST` | `/api/v1/scenarios/validate` | Проверка неполного выбора |
| `POST` | `/api/v1/scenarios/simulate` | Финальная проверка и расчёт |
| `POST` | `/api/v1/scenarios` | Создать хранимый сценарий |
| `GET` | `/api/v1/scenarios/{id}` | Получить сценарий |
| `PUT` | `/api/v1/scenarios/{id}/decisions` | Заменить выбор мероприятий |
| `POST` | `/api/v1/scenarios/{id}/calculate` | Рассчитать и сохранить результат |
| `GET` | `/api/v1/scenarios/{id}/result` | Актуальный результат |
| `GET` | `/api/v1/scenarios/{id}/results` | История расчётов |

Пример финального расчёта:

```json
{
  "decisions": [
    {"measure_id": "M7", "district_id": "nura"},
    {"measure_id": "M8", "district_id": "nura"},
    {"measure_id": "M10", "district_id": "nura"},
    {"measure_id": "M12", "district_id": null},
    {"measure_id": "M5", "district_id": "saryarka"}
  ]
}
```

Ответ содержит показатели до и после, списки критических значений и `effects`. Каждый
элемент `effects` описывает фактически применённую дельту после лага и clipping. Поле
`kind` отличает прямой эффект от синергии.

### Версии сценария

Сценарий создаётся с `version = 1`. Изменение решений требует `expected_version` и
увеличивает версию. Если клиент отправляет устаревшую версию, API отвечает HTTP `409`
с кодом `scenario_version_conflict`. После изменения решений старый расчёт остаётся в
истории, но перестаёт считаться актуальным.

Пример изменения выбора:

```json
{
  "expected_version": 1,
  "decisions": [
    {"measure_id": "M7", "district_id": "nura"},
    {"measure_id": "M8", "district_id": "nura"},
    {"measure_id": "M10", "district_id": "nura"},
    {"measure_id": "M12", "district_id": null},
    {"measure_id": "M5", "district_id": "saryarka"}
  ]
}
```

## Проверки

```powershell
.\.venv\Scripts\ruff.exe check src tests
.\.venv\Scripts\python.exe -m pytest -q
```

Эталонный сценарий из задания имеет стоимость `95` и Score `56.54`.
