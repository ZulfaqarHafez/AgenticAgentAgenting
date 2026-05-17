# Hive Agent Backend

FastAPI service for the Hive Circle orchestration system.

## Quickstart

```bash
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

## Persistence Modes

By default, backend runs with in-memory storage:
- `HIVE_STORE_BACKEND=memory`

To enable Postgres + Redis persistence:
- `HIVE_STORE_BACKEND=postgres_redis`
- `HIVE_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/hive_agent`
- `HIVE_REDIS_URL=redis://localhost:6379/0`
- `HIVE_REDIS_RUN_TTL_SECONDS=900`
