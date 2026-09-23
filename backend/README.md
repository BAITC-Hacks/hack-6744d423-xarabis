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
```

Зависимости направлены внутрь: `presentation -> application -> domain`.
Домен не импортирует FastAPI, Pydantic или инфраструктурные адаптеры.

## Запуск

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn city_simulator.main:app --reload
```

Swagger UI: <http://127.0.0.1:8000/docs>

Docker:

```bash
docker build -t akim-backend .
docker run --rm -p 8000:8000 akim-backend
```

## API

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/api/v1/health` | Проверка процесса |
| `GET` | `/api/v1/catalog` | Версии и правила симуляции |
| `GET` | `/api/v1/indicators` | Справочник показателей |
| `GET` | `/api/v1/districts` | Исходные районы |
| `GET` | `/api/v1/measures` | Каталог мероприятий |
| `POST` | `/api/v1/scenarios/validate` | Проверка неполного выбора |
| `POST` | `/api/v1/scenarios/simulate` | Финальная проверка и расчёт |

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

## Проверки

```powershell
.\.venv\Scripts\ruff.exe check src tests
.\.venv\Scripts\python.exe -m pytest -q
```

Эталонный сценарий из задания имеет стоимость `95` и Score `56.54`.
