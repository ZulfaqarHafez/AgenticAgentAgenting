# Agentic Agent (Hive Circle)

Goal-driven multi-agent MVP with:
- Rust backend (axum + tokio)
- Circle-junction specialist scheduler
- Claude-like Next.js UI shell
- Usefulness report endpoint

## Project layout
- `docs/`: architecture and web research
- `backend/`: Rust API server + scheduler + tests
- `frontend/`: Next.js UI console

## Run backend
Needs a Rust toolchain (https://rustup.rs).
```powershell
cd backend
# Optional persistence mode:
# $env:HIVE_STORE_BACKEND="postgres_redis"
# $env:HIVE_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/hive_agent"
# $env:HIVE_REDIS_URL="redis://localhost:6379/0"
cargo run --release
```
The API listens on `http://127.0.0.1:8000` (change with `HIVE_HOST` / `HIVE_PORT`). API docs are at `/docs`.

## Run frontend
```powershell
cd frontend
npm install
$env:NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
npm run dev
```

## Verify
- Backend checks: `cd backend; cargo test; cargo clippy --all-targets; cargo fmt --check`
- Frontend checks: `cd frontend; npm run lint; npm run build`
