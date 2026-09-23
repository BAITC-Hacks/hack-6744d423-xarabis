# Python API

FastAPI-сервис симулятора: проверяет сценарии и рассчитывает показатели. AI-консультант работает отдельно в `ai_service/`. Контракт фронтенда — [docs/frontend-integration.md](docs/frontend-integration.md).

## Локальный запуск без PostgreSQL

Из папки `backend` (Python 3.11+, рекомендуется 3.12):

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
export DATABASE_URL='sqlite+aiosqlite:///./.venv/akim-local.db'
.venv/bin/python -m city_simulator.init_local_db
.venv/bin/python -m uvicorn city_simulator.main:app --host 127.0.0.1 --port 8000
```

SQLite — только локальный предпросмотр. Инициализация создаёт недостающие таблицы и сохраняет существующие данные. В новом терминале снова задайте `DATABASE_URL`. Проверка: <http://127.0.0.1:8000/api/v1/health> и <http://127.0.0.1:8000/docs>.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -e '.[dev]'
$env:DATABASE_URL = 'sqlite+aiosqlite:///./.venv/akim-local.db'
./.venv/Scripts/python.exe -m city_simulator.init_local_db
./.venv/Scripts/python.exe -m uvicorn city_simulator.main:app --host 127.0.0.1 --port 8000
```

Для PostgreSQL используйте настройки из `.env.example`, `compose.yml` и Alembic-миграции (`alembic upgrade head`). PostgreSQL-миграции с JSONB не предназначены для SQLite. AI-сервис подключается через `AI_SERVICE_URL`; ключ провайдера хранится только там. Тесты: `.venv/bin/python -m pytest` или `./.venv/Scripts/python.exe -m pytest` на Windows.
