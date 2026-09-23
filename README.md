# Аким на 5 часов

Симулятор решений для районов Астаны: пользователь выбирает меры, Python API проверяет план и рассчитывает показатели и городской Score. Интерфейс показывает изменения по районам и условный интерактивный 3D-макет. Это хакатонный прототип; геометрия и демоданные карты не являются точной моделью города.

## Где что лежит

| Папка | Ответственность |
| --- | --- |
| [`frontend/`](frontend/README.md) | React-интерфейс, песочница Three.js, Unity WebGL, веб-сервер и прокси к API |
| [`backend/`](backend/README.md) | Python API, правила и расчёты симулятора, хранение сценариев |
| [`ai_service/`](ai_service/README.md) | AI-консультант для Астаны и вымышленного города; подключён через потоковый серверный прокси |

Фронтенд не реализует расчёты и не хранит API-ключи. Контракт данных: [`backend/docs/frontend-integration.md`](backend/docs/frontend-integration.md).

## Быстрый запуск всего проекта

Нужны Node.js **22.16+** и Python **3.12**. Откройте отдельные терминалы в корне репозитория. Команды ниже — для macOS/Linux; Windows-варианты есть в [`frontend/README.md`](frontend/README.md) и [`backend/README.md`](backend/README.md).

**1. Python API** (порт `8000`, локальный SQLite вместо PostgreSQL):

```sh
cd backend
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
export DATABASE_URL='sqlite+aiosqlite:///./.venv/akim-local.db'
.venv/bin/python -m city_simulator.init_local_db
.venv/bin/python -m uvicorn city_simulator.main:app --host 127.0.0.1 --port 8000
```

Если установлен только `python3`, проверьте его версию и замените `python3.12` в первой команде. В новом терминале бэкенда задайте `DATABASE_URL` заново. Проверка: <http://127.0.0.1:8000/api/v1/health> и <http://127.0.0.1:8000/docs>.

**2. Фронтенд** (порт `5173`):

```bash
cd frontend
cp .env.example .env
npm ci
npm run dev
```

Открыть [Астану](http://127.0.0.1:5173/#astana) или [песочницу](http://127.0.0.1:5173/#sandbox). Без Python API интерфейс показывает деморежим: произвольные решения не рассчитываются.

**3. AI-консультант (необязательно)** из корня репозитория:

```sh
python3.12 -m venv ai_service/.venv
ai_service/.venv/bin/python -m pip install -r ai_service/requirements-lock.txt
cp ai_service/.env.example ai_service/.env
# Впишите OPENAI_API_KEY и OPENAI_MODEL в ai_service/.env
ai_service/.venv/bin/python -m uvicorn ai_service.app:app --host 127.0.0.1 --port 8001
```

Ключ хранится только в `ai_service/.env`, не в `frontend/.env`, `VITE_*`, JavaScript или Git. Проверка процесса: <http://127.0.0.1:8001/health>; этот адрес не подтверждает доступ к модели. Подробнее — в [`ai_service/README.md`](ai_service/README.md).

Подробные команды сборки и размещения, ограничения Unity WebGL и сценарий проверки — в [`frontend/README.md`](frontend/README.md).

## Показ жюри и проверка сборки

В `/#astana` выберите район, нажмите «Попробовать пример» → «Сохранить план» → «Рассчитать результат». Score, бюджет и изменения районов приходят из Python API. «Показать жюри» открывает историю «Проблема → Решение → Результат». В `/#sandbox` выберите улучшения и нажмите «Следующий квартал» — состояние тоже пересчитывает Python.

```sh
cd frontend
npm test
npm run build
PORT=3003 PYTHON_API_URL=http://127.0.0.1:8000 AI_API_URL=http://127.0.0.1:8001 npm run serve
```

Production-адрес: <http://127.0.0.1:3003/>. Если `/api/v1/*` возвращает `502`, проверьте, что Python API запущен на порту `8000`. Не открывайте `dist/index.html` через `file://`: WebGL и API требуют HTTP. Для публичного размещения нужны настройки защиты API и секретов; этот запуск предназначен для локального демо.

## Город-песочница

Во вкладке **Песочница** доступен вымышленный Новый Берег: пять районов с названиями из кейса Астаны, цветными рейтингами, шестью улучшениями, очередями машин и сменой дня и ночи. География условная. Каждый район развивается отдельно, бюджет общий. Python рассчитывает состояние, а AI объясняет выбранный район и текущий план. Карта Астаны основана на OpenStreetMap (© OpenStreetMap contributors, ODbL), но содержит только пять районов из задания: Сарайшык не включён; здания, высоты и движение машин схематические. Подробности — в [frontend/README.md](frontend/README.md).
