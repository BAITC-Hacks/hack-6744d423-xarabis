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
- пагинированный список, сброс, удаление и история сценариев;
- optimistic locking через версию сценария;
- структурированные ошибки игровых правил и настраиваемый CORS;
- доверенная интеграция со сторонним AI-консультантом и история чата;
- request ID, JSON-логи, безопасные `500`, security headers и лимиты запросов;
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
python -m uvicorn city_simulator.main:app --reload
```

Подключение к базе задаётся через `DATABASE_URL`. Пример находится в `.env.example`.
Разрешённые origin frontend задаются списком через запятую в
`CORS_ALLOWED_ORIGINS`. Локальный файл `.env` не отслеживается Git.
Адрес отдельного AI-сервиса задаётся через `AI_SERVICE_URL`, таймаут — через
`AI_SERVICE_TIMEOUT_SECONDS`. Основной backend сам формирует доверенный контекст и
не принимает результаты симуляции от браузера.
Уровень логирования задаётся `LOG_LEVEL`, максимальное тело запроса —
`MAX_REQUEST_BODY_BYTES`, лимит AI-вопросов на сценарий —
`AI_CHAT_REQUESTS_PER_MINUTE`.

При `APP_ENV=production` приложение отказывается запускаться с `APP_DEBUG=true`,
SQLite или wildcard `*` в CORS. Production-образ работает от непривилегированного
пользователя и исключает `.env`, тесты, локальные БД и виртуальное окружение из
Docker-контекста. Лимит чата хранится в памяти процесса; при горизонтальном
масштабировании его следует заменить общим rate limiter на уровне gateway или Redis.

### Локальный предпросмотр без PostgreSQL

Для локального запуска можно явно выбрать SQLite и создать таблицы из ORM-моделей.
Из каталога `backend` после установки `.[dev]`:

```powershell
$env:DATABASE_URL = "sqlite+aiosqlite:///./.venv/sandbox-local.db"
.\.venv\Scripts\python.exe -m city_simulator.init_local_db
.\.venv\Scripts\python.exe -m uvicorn city_simulator.main:app --host 127.0.0.1 --port 8000
```

Команда инициализации читает только явно заданную переменную окружения `DATABASE_URL`,
отказывается работать с PostgreSQL и создаёт только отсутствующие таблицы. Повторный
запуск сохраняет существующие данные. Файл предпросмотра находится внутри игнорируемой
`.venv`. Это вспомогательный локальный запуск: он не выполняет и не заменяет миграции
Alembic, предназначенные для PostgreSQL, и не обновляет схему уже существующих таблиц.

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
| `GET` | `/api/v1/scenarios` | Получить страницу сценариев |
| `GET` | `/api/v1/scenarios/{id}` | Получить сценарий |
| `PUT` | `/api/v1/scenarios/{id}/decisions` | Заменить выбор мероприятий |
| `POST` | `/api/v1/scenarios/{id}/reset` | Сбросить выбор мероприятий |
| `DELETE` | `/api/v1/scenarios/{id}` | Удалить сценарий |
| `POST` | `/api/v1/scenarios/{id}/calculate` | Рассчитать и сохранить результат |
| `GET` | `/api/v1/scenarios/{id}/result` | Актуальный результат |
| `GET` | `/api/v1/scenarios/{id}/results` | История расчётов |
| `GET` | `/api/v1/sandbox/catalog` | Правила и улучшения учебного города |
| `POST` | `/api/v1/sandbox/simulate` | Пересчитать историю кварталов учебного города |

### Песочница «Новый Берег»

Отдельный вымышленный город с тремя зонами: транспорт, воздух и школы. API песочницы
не использует базу данных и не изменяет сценарии Астаны. Сервер каждый раз проигрывает
переданную историю с начала, поэтому результат воспроизводим и не зависит от других игроков.

`GET /api/v1/sandbox/catalog` возвращает `city_name`, `starting_budget` (100),
`quarterly_income` (12), `max_turns` (12), `critical_threshold` (40), `target_value` (65),
`improvements`. Каждое улучшение содержит `id`, `name`, `description`, `cost`, `zone_id`, `gain`.

`POST /api/v1/sandbox/simulate` принимает только историю завершённых ходов:

```json
{"turns": [["bus", "school", "park"], ["signals"], ["filter"]]}
```

Пустая история `{"turns": []}` возвращает исходное состояние. В квартале допустимы
0–3 улучшения; пустой ход тоже начисляет доход 12. Сначала проверяется и списывается
стоимость строительства, затем начисляется доход. Каждое улучшение строится один раз.
Неизвестные ID, повторы, превышение бюджета и лимитов дают HTTP 422 с `error.code`
`sandbox_validation_error` (игровое правило) или `invalid_request` (форма запроса).

Ответ содержит `city_name`, `quarter` (1–13), `budget`, `score` (среднее трёх зон,
округлённое до одного десятичного знака), `zones` (`id`, `name`, `value`, `description`),
`built` (ID в порядке строительства), `turns`, `status`, `last_changes`, `last_income`.
В `last_changes` — одна запись `{zone_id, before, after}` на изменённую зону последнего
хода, при пустом ходе список пуст. `last_income` равен 0 при старте и 12 после хода.
Статус `won` означает, что все три зоны достигли 65; `finished` — исчерпаны 12 ходов
без победы, иначе `playing`. Пример выше даёт квартал 4, бюджет 22, Score 74.7 и `won`.

### Песочница районов v2

`GET /api/v1/sandbox/v2/catalog` и `POST /api/v1/sandbox/v2/simulate` — отдельный
контракт с `rules_version: "districts-v2"`. Прежние `/sandbox/catalog` и
`/sandbox/simulate` сохраняют исходные правила и формат.

Город «Новый Берег» вымышленный: названия пяти районов заимствованы у Астаны,
но показатели и описания учебные, не реальные городские данные.

| ID | Район | Транспорт | Воздух | Образование |
| --- | --- | ---: | ---: | ---: |
| `esil` | Есиль | 70 | 72 | 54 |
| `almaty` | Алматы | 28 | 52 | 48 |
| `saryarka` | Сарыарка | 38 | 24 | 58 |
| `baikonur` | Байконур | 76 | 74 | 72 |
| `nura` | Нура | 26 | 42 | 26 |

Каталог содержит `rules_version`, `city_name`, `starting_budget: 200`,
`quarterly_income: 25`, `max_turns: 12`, `critical_threshold: 40`,
`target_value: 65` и `improvements` с полями `id`, `name`, `description`, `cost`,
`zone_id` (целевой показатель), `gain`.

| Улучшение | Цена | Показатель | Прибавка |
| --- | ---: | --- | ---: |
| `bus` — Автобусная линия | 22 | `transport` | 24 |
| `signals` — Умные светофоры | 16 | `transport` | 18 |
| `park` — Городской парк | 18 | `air` | 22 |
| `filter` — Фильтры на заводе | 26 | `air` | 30 |
| `school` — Новая школа | 32 | `education` | 42 |
| `repair` — Ремонт дорог | 30 | `transport` | 30 |

Тело запроса — полная история до 12 ходов, по 0–3 решения на ход:

```json
{"turns": [[{"district_id": "almaty", "improvement_id": "bus"}]]}
```

`{"turns": []}` начинает новую игру. Бюджет общий для всех районов; стоимость
проверяется до начисления дохода 25, включая пустые ходы. Одно улучшение разрешено
в каждом районе по одному разу. Значения ограничены сверху 100. Сервер сам
восстанавливает состояние из истории; клиент не передаёт цены, бюджет или показатели.
Неизвестные ID, повтор пары район/улучшение, нехватка бюджета, лишние поля и
превышение лимитов возвращают HTTP 422 (`sandbox_validation_error` или `invalid_request`).

Ответ содержит `rules_version`, `city_name`, `quarter` (1–13), `budget`, `score`,
`districts`, `turns`, `status`, `last_changes`, `last_income`. Каждый район имеет
`id`, `name`, `description`, `score`, `values: {transport, air, education}` и
`built` — список ID построенных улучшений в порядке строительства.
Рейтинг района — среднее трёх показателей с округлением до одного знака; рейтинг
города — среднее неокруглённых рейтингов районов, также округлённое до одного знака.
Цвет рейтинга: меньше 40 — красный, от 40 до 65 — жёлтый, от 65 — зелёный.

`last_changes` объединяет изменения последнего хода по паре район/показатель:
`{district_id, indicator_id, before, after}`; пустой ход возвращает пустой список.
`last_income` равен 0 в начале и 25 после хода. `won` требует значения не ниже 65
у **каждого из трёх показателей каждого из пяти районов**, независимо от среднего
рейтинга. После 12 ходов без победы статус `finished`, иначе `playing`.
Пример выше возвращает квартал 2, бюджет 203 и транспорт Алматы 52;
остальные районы остаются в исходном состоянии.
| `POST` | `/api/v1/scenarios/{id}/chat/messages` | Отправить вопрос консультанту |
| `GET` | `/api/v1/scenarios/{id}/chat/messages` | Получить историю чата |

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
.\.venv\Scripts\python.exe scripts\smoke.py --base-url http://127.0.0.1:8000
```

Эталонный сценарий из задания имеет стоимость `95` и Score `56.54`.
