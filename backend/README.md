# Hive Agent Backend

Rust API server for the Hive Circle orchestration system, built on axum and tokio.

## Quickstart

```bash
cargo run --release
```

The server listens on `http://127.0.0.1:8000`. Interactive API docs are at `/docs` and the OpenAPI spec is at `/openapi.json`.

## Layout

- `src/routes.rs`: HTTP handlers (same paths and JSON as the original FastAPI service)
- `src/scheduler.rs`: circle-junction turn rotation, low-value pausing, verifier preemption, proof gate
- `src/specialist_engine.rs`: template-based specialist turns for `/runs/{id}/auto-turn`
- `src/skill_registry.rs`: specialist recommendations
- `src/store.rs`: in-memory store, or Postgres + Redis
- `src/models.rs`, `src/validation.rs`: request/response types and 422 validation errors

## Configuration

| Variable | Default |
| --- | --- |
| `HIVE_HOST` | `127.0.0.1` |
| `HIVE_PORT` | `8000` |
| `HIVE_STORE_BACKEND` | `memory` (or `postgres_redis`) |
| `HIVE_DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/hive_agent` |
| `HIVE_REDIS_URL` | `redis://localhost:6379/0` |
| `HIVE_REDIS_RUN_TTL_SECONDS` | `900` |
| `HIVE_CORS_ORIGINS` | localhost / 127.0.0.1 on ports 3000-3005, 3010, 3011 |
| `RUST_LOG` | `info,sqlx=warn` |

Postgres mode creates the same `goals` and `runs` tables the Python backend used, so data it already saved still loads. Old `postgresql+psycopg://` URLs are accepted.

## Tests

```bash
cargo test
cargo clippy --all-targets
cargo fmt --check
```

The Postgres + Redis store test is skipped unless you point it at real servers:

```bash
HIVE_TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/hive_agent_test \
HIVE_TEST_REDIS_URL=redis://localhost:6379/15 \
cargo test --test postgres_store
```
