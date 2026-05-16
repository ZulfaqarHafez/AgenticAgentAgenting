# Agentic Agent (Hive Circle)

Goal-driven multi-agent MVP with:
- FastAPI backend
- LangGraph turn graph integration
- Circle-junction specialist scheduler
- Claude-like Next.js UI shell
- Usefulness report endpoint

## Project layout
- `docs/`: architecture and web research
- `backend/`: FastAPI + scheduler + tests
- `frontend/`: Next.js UI console

## Run backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
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
