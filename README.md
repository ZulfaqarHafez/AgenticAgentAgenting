# Agentic Agent (Agent Dojo)

A **gym / certification dojo for AI agents**: submit a candidate agent, it runs repeated rounds of
adversarial interviews, gets graded by a judge panel, is served targeted learning material on
failure, and is re-tested on held-out variants until it certifies — or fails with an evidence-backed
report. See **`docs/agent-dojo-plan.md`** for the evidence-backed system plan.

Built on a goal-driven multi-agent MVP that is being repurposed into the dojo (see plan §10):
- FastAPI backend
- LangGraph turn graph integration
- Circle-junction specialist scheduler (→ examiner panel + interview loop)
- Claude-like Next.js UI shell (→ interview room + scorecard)
- Usefulness report endpoint (→ candidate scorecard)

## Project layout
- `docs/`: system plans (`agent-dojo-plan.md` is current direction) and web research
- `backend/`: FastAPI + scheduler + tests
- `frontend/`: Next.js UI console

## Run backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
# Optional persistence mode:
# $env:HIVE_STORE_BACKEND="postgres_redis"
# $env:HIVE_DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/hive_agent"
# $env:HIVE_REDIS_URL="redis://localhost:6379/0"
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

## Run frontend
```powershell
cd frontend
npm install
$env:NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
npm run dev
```

## Verify
- Backend tests: `cd backend; .\.venv\Scripts\python -m pytest`
- Frontend checks: `cd frontend; npm run lint; npm run build`
