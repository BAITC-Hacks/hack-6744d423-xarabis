# Интеграция frontend с Akim City Simulator API

Статус документа: актуально для backend `0.6.0`.

Этот документ является рабочим контрактом для frontend. Для подключения основной
симуляции не требуется читать исходный код backend или самостоятельно воспроизводить
формулу Score.

## 1. Что frontend может реализовать сейчас

Текущий API полностью поддерживает основной игровой цикл:

1. загрузить правила, районы, показатели и мероприятия;
2. создать сценарий;
3. выбрать до пяти мероприятий и назначить районы;
4. проверить выбор и бюджет;
5. сохранить выбор;
6. рассчитать итог;
7. показать Score, изменения по районам, критические показатели и эффекты;
8. получить актуальный результат и историю расчётов.

Пока отсутствуют:

- авторизация и пользователи;
- завершение сценария;
- streaming-прокси для постепенного текста AI-консультанта.

Это не мешает собрать основной экран симуляции. API уже поддерживает пагинированный
список, сброс и удаление сценариев.

## 2. Адреса и подключение

Локальный backend:

```text
http://127.0.0.1:8000
```

Префикс API:

```text
/api/v1
```

Полезные адреса:

```text
Swagger UI: http://127.0.0.1:8000/docs
OpenAPI JSON: http://127.0.0.1:8000/openapi.json
Health: http://127.0.0.1:8000/api/v1/health
Readiness: http://127.0.0.1:8000/api/v1/ready
```

`/health` подтверждает работу процесса. `/ready` дополнительно проверяет PostgreSQL и
возвращает `503 {"status":"not_ready"}`, если база временно недоступна. Эти маршруты
предназначены прежде всего для инфраструктуры; игровой UI не должен считать
недоступность AI-сервиса ошибкой readiness основного backend.

### Запросы из браузера

Backend разрешает CORS для адресов из переменной `CORS_ALLOWED_ORIGINS`. По умолчанию
разрешены `http://localhost:5173` и `http://127.0.0.1:5173`. Поэтому локально можно
использовать `http://127.0.0.1:8000/api/v1` напрямую.

Предпочтительный вариант — направлять `/api` через proxy frontend-сервера. Тогда
конфигурация frontend одинакова в development и production. Пример для Vite:

```ts
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
```

После этого frontend использует относительный адрес:

```ts
const API_BASE_URL = "/api/v1";
```

Если frontend запускается с другого origin, этот точный origin необходимо добавить в
`CORS_ALLOWED_ORIGINS` backend через запятую. Wildcard `*` для production не
использовать. В production frontend и `/api` лучше публиковать на одном origin через
reverse proxy. Не зашивайте локальный адрес backend в компоненты.

Все запросы и ответы используют `application/json`. Авторизация в текущей версии не
требуется.

## 3. Обязательные TypeScript-типы

Создайте один файл контрактов, например `src/shared/api/city-simulator.types.ts`.

```ts
export type UUID = string;
export type ISODateTime = string;

export type Direction =
  | "transport"
  | "ecology"
  | "social"
  | "safety"
  | "services";

export type IndicatorId =
  | "T1"
  | "T2"
  | "E1"
  | "E2"
  | "S1"
  | "S2"
  | "B1"
  | "B2"
  | "C1"
  | "C2";

export type DistrictId =
  | "esil"
  | "almaty"
  | "saryarka"
  | "baikonur"
  | "nura";

export type MeasureScope = "district" | "city";
export type EffectKind = "direct" | "synergy";
export type ScenarioStatus = "draft" | "calculated" | "completed";

export interface CatalogMetadata {
  dataset_version: string;
  formula_version: string;
  budget: number;
  horizon_quarters: number;
  required_decisions: number;
  max_measures_per_direction: number;
  critical_threshold: number;
}

export interface Indicator {
  id: IndicatorId;
  direction: Direction;
  name: string;
  scale_description: string;
  weight: number;
}

export interface District {
  id: DistrictId;
  name: string;
  population_share: number;
  profile: string;
  indicators: Record<IndicatorId, number>;
}

export interface Measure {
  id: string;
  direction: Direction;
  name: string;
  scope: MeasureScope;
  cost: number;
  lag_quarters: number;
  effects: Partial<Record<IndicatorId, number>>;
}

export interface Decision {
  measure_id: string;
  district_id: DistrictId | null;
}

export interface DraftValidation {
  valid: true;
  decision_count: number;
  total_cost: number;
  remaining_budget: number;
  ready_for_calculation: boolean;
}

export interface Scenario {
  id: UUID;
  status: ScenarioStatus;
  version: number;
  budget_limit: number;
  decisions: Decision[];
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface ScenarioPage {
  items: Scenario[];
  total: number;
  limit: number;
  offset: number;
}

export interface CriticalIndicator {
  district_id: DistrictId;
  indicator_id: IndicatorId;
  value: number;
}

export interface AppliedEffect {
  measure_ids: string[];
  district_id: DistrictId;
  indicator_id: IndicatorId;
  delta: number;
  kind: EffectKind;
}

export interface DistrictResult {
  district_id: DistrictId;
  score_before: number;
  score_after: number;
  indicators_before: Record<IndicatorId, number>;
  indicators_after: Record<IndicatorId, number>;
}

export interface SimulationResult {
  dataset_version: string;
  formula_version: string;
  total_cost: number;
  remaining_budget: number;
  score_before: number;
  score_after: number;
  score_delta: number;
  city_average: number;
  weakest_district_score: number;
  districts: DistrictResult[];
  critical_before: CriticalIndicator[];
  critical_after: CriticalIndicator[];
  effects: AppliedEffect[];
}

export interface StoredSimulationResult {
  id: UUID;
  scenario_id: UUID;
  scenario_version: number;
  created_at: ISODateTime;
  simulation: SimulationResult;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown;
    request_id?: string;
  };
}

export interface ValidationIssue {
  code: string;
  message: string;
  context: Record<string, unknown>;
}
```

`Measure.id` сейчас имеет вид `M1`…`M14`, но frontend должен брать список из API, а
не считать, что каталог навсегда ограничен четырнадцатью элементами.

## 4. Справочники и начальная загрузка

При старте приложения выполните четыре независимых запроса параллельно:

```http
GET /api/v1/catalog
GET /api/v1/indicators
GET /api/v1/districts
GET /api/v1/measures
```

Пример:

```ts
const [catalog, indicators, districts, measures] = await Promise.all([
  api.get<CatalogMetadata>("/catalog"),
  api.get<Indicator[]>("/indicators"),
  api.get<District[]>("/districts"),
  api.get<Measure[]>("/measures"),
]);
```

Не храните названия районов, мероприятий, показателей, стоимость, эффекты и веса в
frontend-коде. API является источником истины.

### `GET /catalog`

Пример ответа:

```json
{
  "dataset_version": "1.0",
  "formula_version": "1.0",
  "budget": 100,
  "horizon_quarters": 8,
  "required_decisions": 5,
  "max_measures_per_direction": 2,
  "critical_threshold": 40.0
}
```

Использование полей:

- `budget` — максимальный бюджет;
- `required_decisions` — точное количество решений для расчёта;
- `max_measures_per_direction` — максимум мер одного направления;
- `horizon_quarters` — горизонт, на котором backend применяет эффекты;
- `critical_threshold` — значение ниже него считается критическим;
- версии нужно сохранить вместе с отображаемым результатом для диагностики.

### `GET /indicators`

Возвращает десять показателей. `direction` нужен для группировки, `name` — для UI,
`scale_description` — для подсказки пользователю о смысле шкалы, `weight` — только
для объяснения. Frontend не должен пересчитывать Score.

### `GET /districts`

Возвращает пять районов и исходные показатели. `population_share` — доля населения
от `0` до `1`, а не процент. Для отображения умножайте её на 100.

### `GET /measures`

Для меры со `scope = "district"` пользователь обязан выбрать район. Для меры со
`scope = "city"` селектор района нужно скрыть или заблокировать, а в запросе всегда
отправлять `district_id: null`.

`effects` — ожидаемые базовые эффекты каталога. Фактически применённые эффекты после
учёта лага, синергии и ограничения диапазона `0..100` находятся только в результате
расчёта.

## 5. Игровые правила

Backend проверяет следующие правила:

- для финального расчёта нужно выбрать ровно 5 мероприятий;
- в черновике может быть от 0 до 5 мероприятий;
- одно мероприятие нельзя выбирать дважды, даже для разных районов;
- суммарная стоимость не может превышать 100;
- в одном направлении можно выбрать не более `max_measures_per_direction` мероприятий;
- районная мера требует существующий `district_id`;
- городская мера требует `district_id: null`;
- `M1` и `M3` несовместимы в любом сочетании районов;
- `M4` и `M7` нельзя применять в одном районе;
- `M5` и `M13` нельзя применять в одном районе.

Frontend может заранее блокировать очевидные ошибки для удобства, но перед
сохранением и расчётом всегда обязан доверять ответу backend. Нельзя копировать
формулу Score или вычислять итоговые эффекты в браузере.

## 6. Рекомендуемый хранимый сценарий

Это основной flow для приложения.

### Экран списка сценариев

```http
GET /api/v1/scenarios?limit=20&offset=0
```

Ответ `200`:

```json
{
  "items": [],
  "total": 0,
  "limit": 20,
  "offset": 0
}
```

`limit` допустим от 1 до 100, `offset` — от 0. Сценарии отсортированы от недавно
обновлённых к старым. Для следующей страницы отправьте `offset + limit`. Отдельного
поля `has_next` нет: следующая страница существует, пока `offset + items.length <
total`.

### Шаг 1. Создать сценарий

```http
POST /api/v1/scenarios
```

Тело отсутствует.

Ответ `201 Created`:

```json
{
  "id": "9ca3e120-1718-41e5-a458-3f62ad4c2033",
  "status": "draft",
  "version": 1,
  "budget_limit": 100,
  "decisions": [],
  "created_at": "2026-09-23T10:00:00+00:00",
  "updated_at": "2026-09-23T10:00:00+00:00"
}
```

Сохраните `id` в состоянии приложения. Для быстрого возврата можно также хранить его
в `localStorage`, например под ключом `akim.currentScenarioId`, но список сценариев
нужно получать из backend.

### Шаг 2. Восстановить сценарий после обновления страницы

```http
GET /api/v1/scenarios/{scenario_id}
```

Если ответ `200`, замените локальное состояние объектом из ответа. Если `404` с
`scenario_not_found`, удалите старый id из `localStorage` и вернитесь к списку.

Порядок элементов `decisions` не является частью контракта. Связывайте карточки по
`measure_id`, а не по индексу массива.

### Шаг 3. Проверить текущий выбор

```http
POST /api/v1/scenarios/validate
Content-Type: application/json

{
  "decisions": [
    {"measure_id": "M12", "district_id": null}
  ]
}
```

Успех `200`:

```json
{
  "valid": true,
  "decision_count": 1,
  "total_cost": 14,
  "remaining_budget": 86,
  "ready_for_calculation": false
}
```

Этот маршрут принимает неполный выбор. При нарушении правила он возвращает `422`, а
не `{ "valid": false }`.

Вызывать его следует после изменения выбора с debounce примерно `250–400 ms` или
перед сохранением шага. Старый запрос нужно отменять через `AbortController`, чтобы
его ответ не перезаписал более новое состояние.

### Шаг 4. Сохранить весь выбор

```http
PUT /api/v1/scenarios/{scenario_id}/decisions
Content-Type: application/json

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

Это полная замена массива, не patch. Не отправляйте только добавленную карточку.

`expected_version` берётся из последнего ответа `Scenario`. При успехе версия
увеличивается на 1. Ответ целиком заменяет локальный объект сценария:

```json
{
  "id": "9ca3e120-1718-41e5-a458-3f62ad4c2033",
  "status": "draft",
  "version": 2,
  "budget_limit": 100,
  "decisions": [
    {"measure_id": "M5", "district_id": "saryarka"},
    {"measure_id": "M7", "district_id": "nura"},
    {"measure_id": "M8", "district_id": "nura"},
    {"measure_id": "M10", "district_id": "nura"},
    {"measure_id": "M12", "district_id": null}
  ],
  "created_at": "2026-09-23T10:00:00+00:00",
  "updated_at": "2026-09-23T10:02:00+00:00"
}
```

Не запускайте несколько `PUT` параллельно: каждый запрос меняет версию. Сериализуйте
сохранения либо сохраняйте по явному действию пользователя.

Любое изменение решений:

- увеличивает `version`;
- переводит статус в `draft`;
- делает прежний результат неактуальным;
- сохраняет прежний результат только в истории.

### Шаг 5. Рассчитать сохранённый сценарий

Кнопка расчёта активна только когда:

- последний `/validate` завершился с `200`;
- `ready_for_calculation === true`;
- сохранение решений завершено;
- нет незаписанных изменений.

Запрос:

```http
POST /api/v1/scenarios/{scenario_id}/calculate
Content-Type: application/json

{
  "expected_version": 2
}
```

Ответ `200`:

```json
{
  "id": "3ba1ff89-4536-4c47-aac3-28e6f59a37cd",
  "scenario_id": "9ca3e120-1718-41e5-a458-3f62ad4c2033",
  "scenario_version": 2,
  "created_at": "2026-09-23T10:03:00+00:00",
  "simulation": {
    "dataset_version": "1.0",
    "formula_version": "1.0",
    "total_cost": 95,
    "remaining_budget": 5,
    "score_before": 52.56,
    "score_after": 56.54,
    "score_delta": 3.99,
    "city_average": 58.08,
    "weakest_district_score": 52.96,
    "districts": [],
    "critical_before": [
      {"district_id": "nura", "indicator_id": "S1", "value": 38.0},
      {"district_id": "nura", "indicator_id": "S2", "value": 35.0}
    ],
    "critical_after": [],
    "effects": []
  }
}
```

В реальном ответе массив `districts` содержит все 5 районов, а массивы критических
показателей и эффектов содержат фактические элементы. В примере они сокращены только
для читаемости.

Повторный расчёт той же версии идемпотентен: backend возвращает уже сохранённый
результат. После расчёта `GET /scenarios/{scenario_id}` вернёт статус `calculated`.

### Шаг 6. Получить актуальный результат

```http
GET /api/v1/scenarios/{scenario_id}/result
```

Возвращает `StoredSimulationResult` только для текущей версии сценария. После
изменения решений маршрут корректно возвращает `404 result_not_found`, пока новая
версия не рассчитана.

### Шаг 7. Получить историю расчётов

```http
GET /api/v1/scenarios/{scenario_id}/results
```

Ответ — `StoredSimulationResult[]`. Новые версии идут первыми. Пагинации пока нет.
История относится к одному сценарию.

### Шаг 8. Сбросить сценарий

```http
POST /api/v1/scenarios/{scenario_id}/reset
Content-Type: application/json

{
  "expected_version": 2
}
```

Сброс удаляет все выбранные решения, увеличивает версию и возвращает сценарий со
статусом `draft`. Старые результаты сохраняются в истории, но актуальный `/result`
начинает возвращать `404 result_not_found`.

### Шаг 9. Удалить сценарий

```http
DELETE /api/v1/scenarios/{scenario_id}?expected_version=3
```

Успех: `204 No Content`, тело отсутствует. Сценарий, решения и результаты удаляются.
После успеха удалите id из `localStorage` и вернитесь к списку. При устаревшей версии
backend возвращает `409 scenario_version_conflict`; автоматически повторять удаление
с новой версией нельзя.

## 7. Быстрый расчёт без хранения

Для прототипа или экрана предпросмотра можно использовать:

```http
POST /api/v1/scenarios/simulate
Content-Type: application/json

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

Ответ — чистый `SimulationResult`, без обёртки `StoredSimulationResult`. Запрос ничего
не сохраняет в PostgreSQL. Для основного пользовательского пути используйте хранимый
сценарий из предыдущего раздела.

## 8. Как отображать результат

### Верхний блок

- основной результат: `score_after`;
- изменение: `score_delta`, со знаком;
- исходный результат: `score_before`;
- средневзвешенный районный балл после мер: `city_average`;
- балл самого слабого района после мер: `weakest_district_score`;
- потрачено: `total_cost`;
- осталось: `remaining_budget`.

Не ограничивайте городской Score вручную диапазоном `0..100`: формула включает штраф
за критические показатели. Показатели районов находятся в диапазоне `0..100`.

### Районы

Для каждого элемента `districts` найдите район по `district_id` в справочнике и
покажите:

- `score_before` и `score_after`;
- разницу по Score;
- значения каждого индикатора до и после;
- разницу по каждому индикатору.

Название показателя берите из `/indicators`. Не выводите пользователю только коды
`T1`, `E2` и т. п. без расшифровки.

### Критические значения

`critical_before` и `critical_after` содержат значения строго ниже
`critical_threshold`. Если `critical_after` пуст, показывайте положительное состояние,
а не пустой сломанный блок.

### Эффекты

- `kind = "direct"` — прямой эффект выбранного мероприятия;
- `kind = "synergy"` — дополнительный эффект сочетания мероприятий;
- `measure_ids` может содержать один или несколько id;
- `delta` может быть отрицательным;
- `delta` уже учитывает лаг и ограничение итогового показателя диапазоном `0..100`.

Frontend не должен повторно применять `delta` к `indicators_after`.

## 9. Ошибки и обязательное поведение UI

### Бизнес-ошибка сценария

HTTP `422`:

```json
{
  "error": {
    "code": "scenario_validation_error",
    "message": "Сценарий нарушает игровые правила",
    "details": [
      {
        "code": "decision_count_mismatch",
        "message": "Нужно выбрать ровно 5 мероприятий",
        "context": {"required": 5, "actual": 1}
      }
    ]
  }
}
```

`details` имеет тип `ValidationIssue[]`. Логику UI стройте по `details[].code`, а
пользователю показывайте `details[].message`. Стабильные коды правил:

| Код | Значение |
| --- | --- |
| `decision_count_mismatch` | Для расчёта выбрано не ровно требуемое количество |
| `too_many_decisions` | В черновике слишком много решений |
| `duplicate_measure` | Мероприятие выбрано повторно |
| `unknown_measure` | Мероприятия нет в каталоге |
| `district_required` | Для районной меры не указан существующий район |
| `district_not_allowed` | Для городской меры передан район |
| `budget_exceeded` | Превышен бюджет |
| `direction_limit_exceeded` | Превышен лимит мер одного направления |
| `incompatible_measures` | Выбрано несовместимое сочетание |

### Ошибка структуры запроса

HTTP `422`, код `invalid_request`. Это обычно ошибка frontend-кода: неверный UUID,
лишнее поле, неправильный тип или id мероприятия не соответствует формату. В dev
показывайте и логируйте `details`; пользователю достаточно сообщения о некорректном
запросе.

API запрещает неизвестные поля в request body. Не отправляйте UI-only свойства,
например `measureName`, `selected`, `simulation_result` или `clientId`.

### Сценарий не найден

HTTP `404`, код `scenario_not_found`. `error.details.scenario_id` содержит id. Удалите
сохранённый id, вернитесь к списку и сообщите, что прежний черновик недоступен.

### Актуальный результат отсутствует

HTTP `404`, код `result_not_found`. Это нормальное состояние нового или изменённого
черновика. Показывайте экран выбора или предложение запустить расчёт.

### Конфликт версии

HTTP `409`, код `scenario_version_conflict`.

`error.details` содержит `scenario_id`, отправленную `expected_version` и актуальную
`current_version`.

Алгоритм обработки:

1. остановить текущую операцию;
2. выполнить `GET /scenarios/{scenario_id}`;
3. заменить локальный сценарий свежим объектом;
4. предупредить пользователя, что сценарий изменился;
5. не повторять старый `PUT` автоматически, иначе можно затереть более новые данные.

### Сетевая ошибка или `5xx`

Сохраните несохранённый выбор локально, покажите кнопку повторной попытки и не
переходите на экран результата. Для `calculate` повтор с той же версией безопасен.

Каждый прикладной HTTP-ответ содержит `X-Request-ID`. Сохраняйте его в техническом
логе и показывайте в раскрываемых деталях ошибки: по этому id backend-разработчик
найдёт запрос в JSON-логах. Заголовки `X-Request-ID` и `Retry-After` доступны браузеру
и при прямом CORS-подключении. Frontend может отправить собственный `X-Request-ID`,
если он содержит не более 64 латинских букв, цифр, точек, `_` или `-`.

Дополнительные инфраструктурные ошибки:

| HTTP | Код | Действие frontend |
| --- | --- | --- |
| `413` | `request_too_large` | Не повторять тот же запрос; проверить лишние данные |
| `429` | `chat_rate_limit_exceeded` | Заблокировать отправку на время из `Retry-After` |
| `500` | `internal_error` | Показать общий сбой и `request_id`, не технические детали |

## 10. Минимальный API-клиент

```ts
const API_BASE_URL = "/api/v1";

export class ApiRequestError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details?: unknown,
    public readonly requestId?: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  const payload: unknown =
    response.status === 204 ? undefined : await response.json();
  if (!response.ok) {
    const body = payload as ApiErrorBody;
    throw new ApiRequestError(
      response.status,
      body.error?.code ?? "unknown_error",
      body.error?.message ?? "Неизвестная ошибка API",
      body.error?.details,
      response.headers.get("X-Request-ID") ?? body.error?.request_id,
    );
  }
  return payload as T;
}

export const cityApi = {
  getCatalog: () => request<CatalogMetadata>("/catalog"),
  getIndicators: () => request<Indicator[]>("/indicators"),
  getDistricts: () => request<District[]>("/districts"),
  getMeasures: () => request<Measure[]>("/measures"),

  createScenario: () =>
    request<Scenario>("/scenarios", { method: "POST" }),

  listScenarios: (limit = 20, offset = 0) =>
    request<ScenarioPage>(`/scenarios?limit=${limit}&offset=${offset}`),

  getScenario: (id: UUID) => request<Scenario>(`/scenarios/${id}`),

  validate: (decisions: Decision[], signal?: AbortSignal) =>
    request<DraftValidation>("/scenarios/validate", {
      method: "POST",
      body: JSON.stringify({ decisions }),
      signal,
    }),

  replaceDecisions: (
    id: UUID,
    expectedVersion: number,
    decisions: Decision[],
  ) =>
    request<Scenario>(`/scenarios/${id}/decisions`, {
      method: "PUT",
      body: JSON.stringify({
        expected_version: expectedVersion,
        decisions,
      }),
    }),

  calculate: (id: UUID, expectedVersion: number) =>
    request<StoredSimulationResult>(`/scenarios/${id}/calculate`, {
      method: "POST",
      body: JSON.stringify({ expected_version: expectedVersion }),
    }),

  getCurrentResult: (id: UUID) =>
    request<StoredSimulationResult>(`/scenarios/${id}/result`),

  getResults: (id: UUID) =>
    request<StoredSimulationResult[]>(`/scenarios/${id}/results`),

  resetScenario: (id: UUID, expectedVersion: number) =>
    request<Scenario>(`/scenarios/${id}/reset`, {
      method: "POST",
      body: JSON.stringify({ expected_version: expectedVersion }),
    }),

  deleteScenario: (id: UUID, expectedVersion: number) =>
    request<void>(
      `/scenarios/${id}?expected_version=${expectedVersion}`,
      { method: "DELETE" },
    ),
};
```

Для production желательно генерировать клиент из `/openapi.json`, но правила работы
с версиями и состояниями из этого документа всё равно остаются обязательными.

## 11. Состояние frontend

Минимально храните:

```ts
interface SimulatorState {
  catalog: CatalogMetadata | null;
  indicators: Indicator[];
  districts: District[];
  measures: Measure[];
  scenario: Scenario | null;
  draftDecisions: Decision[];
  validation: DraftValidation | null;
  currentResult: StoredSimulationResult | null;
  hasUnsavedChanges: boolean;
  isValidating: boolean;
  isSaving: boolean;
  isCalculating: boolean;
}
```

Правила состояния:

- серверный `Scenario` — подтверждённое сохранённое состояние;
- `draftDecisions` — редактируемая копия;
- `currentResult` нужно сразу очистить при локальном изменении выбора;
- новую `version` брать только из ответа backend;
- во время сохранения или расчёта блокировать повторное нажатие;
- не считать `localStorage` источником истины, кроме хранения id сценария и временного
  восстановления несохранённого выбора.

## 12. AI-консультант: граница интеграции

AI-консультант является отдельным сервисом с `POST /chat`, но frontend не должен
вызывать его напрямую. Согласно контракту консультанта:

- основной backend формирует доверенный контекст;
- основной backend хранит историю диалога;
- основной backend сохраняет структурированный ответ;
- ключ AI-провайдера и межсервисное взаимодействие не попадают в браузер;
- frontend только отправляет сообщение основному backend и отображает ответ.

Основной backend предоставляет обычный запрос с целым проверенным ответом и историю
сообщений. Streaming появится отдельно; текущий маршрут не передаёт частичный текст.

Рекомендуемый интерфейс UI:

```ts
export interface ConsultantBlock {
  title: string;
  explanation: string;
}

export interface ConsultantResponse {
  answer: string;
  strengths: ConsultantBlock[];
  risks: ConsultantBlock[];
  consequences: ConsultantBlock[];
  recommendations: ConsultantBlock[];
  follow_up_question: string | null;
}

export interface ConsultantClient {
  sendMessage(message: string): Promise<ConsultantResponse>;
  listMessages(): Promise<ChatMessage[]>;
}

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: UUID;
  scenario_id: UUID;
  sequence: number;
  role: ChatRole;
  content: string;
  report: ConsultantResponse | null;
  created_at: ISODateTime;
}
```

Отправка сообщения:

```http
POST /api/v1/scenarios/{scenario_id}/chat/messages
Content-Type: application/json

{"message":"Какие риски у моего плана?"}
```

Успех `200` возвращает `ConsultantResponse` без дополнительной обёртки. Frontend не
передаёт историю, выбранные мероприятия, бюджет или результат расчёта. Backend берёт
их из PostgreSQL, передаёт стороннему сервису и сохраняет пару сообщений только после
получения валидного полного ответа.

История:

```http
GET /api/v1/scenarios/{scenario_id}/chat/messages
```

Ответ — `ChatMessage[]` в хронологическом порядке. У пользовательского сообщения
`report` равен `null`; у сообщения ассистента `report` содержит полный
структурированный ответ, а `content` — его текстовое представление для следующего
запроса к AI.

Готовый адаптер вместо mock:

```ts
export function createConsultantClient(scenarioId: UUID): ConsultantClient {
  return {
    sendMessage: (message: string) =>
      request<ConsultantResponse>(
        `/scenarios/${encodeURIComponent(scenarioId)}/chat/messages`,
        {
          method: "POST",
          body: JSON.stringify({ message }),
        },
      ),
    listMessages: () =>
      request<ChatMessage[]>(
        `/scenarios/${encodeURIComponent(scenarioId)}/chat/messages`,
      ),
  };
}
```

Отображение ответа:

- `answer` показывать всегда;
- пустые `strengths`, `risks`, `consequences` и `recommendations` не рендерить;
- `follow_up_question` не показывать, если он `null`;
- весь текст считать обычным текстом, не HTML;
- предусмотреть ожидание до 45 секунд, ошибку и ручной retry;
- не придумывать успешный ответ при сбое AI.

Возможные коды ошибок: `ai_not_configured`, `ai_unavailable`, `ai_timeout`,
`invalid_ai_response`, `ai_refusal`, `ai_contract_mismatch`. При ошибке сообщение не
считается успешно сохранённым. Retry выполняется только по явному действию
пользователя.

После изменения решений backend автоматически передаёт
`simulation_result: null`, пока новая версия не рассчитана. Frontend не должен
вручную собирать или изменять этот доверенный контекст.

## 13. Порядок реализации frontend

Рекомендуемая последовательность без ожидания дальнейших решений:

1. Настроить proxy `/api` на backend.
2. Создать TypeScript-типы и общий API-клиент.
3. Реализовать параллельную загрузку четырёх справочников.
4. Сделать пагинированный список, создание, открытие и удаление сценариев.
5. Сделать восстановление последнего сценария по id из `localStorage` как shortcut.
6. Реализовать каталог мероприятий и выбор района только для районных мер.
7. Реализовать валидацию выбора, бюджет и отображение структурированных ошибок.
8. Реализовать полную замену решений с `expected_version`.
9. Реализовать сброс сценария с подтверждением пользователя.
10. Реализовать расчёт и экран результата.
11. Реализовать сравнение районов и показателей до/после.
12. Реализовать историю результатов.
13. Подключить `ConsultantClient` к маршруту сценария и убрать mock-badge.
14. Загружать сохранённую историю чата при открытии сценария.

## 14. Критерии готовности frontend-интеграции

Интеграция основной симуляции готова, если выполняются все проверки:

- приложение загружается без захардкоженного каталога;
- список сценариев поддерживает пагинацию;
- после refresh восстанавливается текущий сценарий;
- городская мера отправляется с `district_id: null`;
- районная мера не сохраняется без района;
- невозможно случайно отправить более пяти решений;
- ошибки правил обрабатываются по `error.details[].code`, а пользователю показывается
  `error.details[].message`;
- стоимость и остаток подтверждаются backend;
- сохранения не отправляются параллельно;
- `409` приводит к перезагрузке сценария, а не к бесконечному retry;
- кнопка расчёта недоступна до валидных пяти решений;
- после изменения рассчитанного сценария старый результат исчезает с основного
  экрана, но остаётся в истории;
- результат использует названия из справочников, а не голые id;
- отрицательные эффекты отображаются корректно;
- пустые списки критических значений и AI-блоков отображаются как нормальное
  состояние;
- frontend не пересчитывает Score;
- frontend не обращается к AI-сервису напрямую;
- удаление и сброс требуют подтверждения и актуальной версии сценария;
- чат отправляет только `message`, а контекст формирует backend;
- история чата восстанавливается после обновления страницы.

## 15. Карта API

| Метод | Маршрут | Использование frontend |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Проверка процесса |
| `GET` | `/api/v1/ready` | Проверка backend и БД |
| `GET` | `/api/v1/catalog` | Правила и версии |
| `GET` | `/api/v1/indicators` | Справочник показателей |
| `GET` | `/api/v1/districts` | Районы и исходные данные |
| `GET` | `/api/v1/measures` | Каталог мероприятий |
| `POST` | `/api/v1/scenarios/validate` | Проверка неполного выбора |
| `POST` | `/api/v1/scenarios/simulate` | Расчёт без сохранения |
| `POST` | `/api/v1/scenarios` | Создание сценария |
| `GET` | `/api/v1/scenarios?limit=20&offset=0` | Список сценариев |
| `GET` | `/api/v1/scenarios/{scenario_id}` | Восстановление сценария |
| `PUT` | `/api/v1/scenarios/{scenario_id}/decisions` | Полная замена выбора |
| `POST` | `/api/v1/scenarios/{scenario_id}/reset` | Сброс решений |
| `DELETE` | `/api/v1/scenarios/{scenario_id}?expected_version=N` | Удаление сценария |
| `POST` | `/api/v1/scenarios/{scenario_id}/calculate` | Расчёт и сохранение |
| `GET` | `/api/v1/scenarios/{scenario_id}/result` | Актуальный результат |
| `GET` | `/api/v1/scenarios/{scenario_id}/results` | История результатов |
| `POST` | `/api/v1/scenarios/{scenario_id}/chat/messages` | Отправить сообщение консультанту |
| `GET` | `/api/v1/scenarios/{scenario_id}/chat/messages` | История сообщений консультанта |
