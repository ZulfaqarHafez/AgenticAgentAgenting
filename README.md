# Agentic Agent (Hive Circle)

A goal-driven multi-agent system: specialist agents (Planner, Research, Executor, Critic, Verifier) take turns on a goal in a "traffic circle", and a proof gate decides when the work is good enough to finish. The repo also holds a meteorology knowledge base and real-data analysis for the next direction: an agentic weather decision assistant for Singapore.

![Hive Circle Console with a live mission](docs/images/hive-console.jpg)

## What's in the repo

| Part | What it is | Status |
| --- | --- | --- |
| **Backend** (`backend/`) | Rust API server (axum + tokio): goals, runs, turn scheduler, proof gate, decision ledger, skill recommender | Working; 33 tests |
| **Frontend** (`frontend/`) | Next.js console: mission control, specialist ring, conversation, proof gate, ledger, run history | Working; 17 Playwright tests |
| **Meteorology knowledge base** (`docs/meteorology/`) | 19 chapters, a 206-concept knowledge graph, data-check scripts and results | Reference for the weather agent |
| **Planning docs** (`docs/`) | Architecture plan, competitive analysis, research on similar projects | Background |

> **Note:** specialist turns are currently generated from templates (`prompted_local_engine`); no language model is connected yet. The scheduling, scoring, proof gate and UI are real.

## How it works

```mermaid
flowchart LR
    U[User goal] --> R[Skill recommender<br/>picks specialists]
    R --> C{Circle junction<br/>scheduler}
    C --> P[Planner] --> C
    C --> RS[Research] --> C
    C --> E[Executor] --> C
    C --> CR[Critic] --> C
    C --> V[Verifier] --> C
    C --> G[Proof gate]
    G -->|blocked| C
    G -->|ready| D[Complete run]
    C -.-> L[Decision ledger<br/>and run report]
```

- **Turn rotation:** the baton passes round the active specialists. A specialist can pass, hand off to another role, or be paused after repeated low-value turns.
- **Priority lane:** the Verifier can interrupt the rotation when something looks risky, which moves the run to a stricter fallback layer.
- **Proof gate:** a run can only be completed after enough turns, enough distinct evidence, a Verifier turn and a minimum average confidence. Thresholds depend on the run mode (lite, balanced, power).
- **Decision ledger:** every role activation, confidence change and fallback transition is recorded and replayable.

![Specialist turns in the conversation view](docs/images/hive-console-conversation.jpg)

## Quick start

### Backend

Needs a Rust toolchain ([rustup.rs](https://rustup.rs)).

```bash
cd backend
cargo run --release
```

The API listens on `http://127.0.0.1:8000` (change with `HIVE_HOST` / `HIVE_PORT`). Interactive API docs are at `/docs`, the OpenAPI spec at `/openapi.json`.

Data is kept in memory by default. For persistence, use Postgres with a Redis run cache:

```bash
export HIVE_STORE_BACKEND=postgres_redis
export HIVE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/hive_agent
export HIVE_REDIS_URL=redis://localhost:6379/0
```

All settings are listed in [`backend/README.md`](backend/README.md).

### Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

On Windows PowerShell, set the variable first: `$env:NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"`.

### Checks

| Area | Command |
| --- | --- |
| Backend | `cd backend && cargo test && cargo clippy --all-targets && cargo fmt --check` |
| Frontend | `cd frontend && npm run lint && npm run build` |
| End-to-end | `cd frontend && npx playwright test` (starts the Rust backend and a production build of the UI automatically; the first run compiles the backend) |

## API overview

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health`, `/runtime/status` | Liveness, version, store backend, run counts |
| `POST` / `GET` | `/goals`, `/goals/{id}` | Create and read goals |
| `POST` / `GET` | `/goals/{id}/runs` | Start a run (body optional; roles are recommended if not given) and list a goal's runs |
| `GET` | `/runs`, `/runs/{id}` | Read runs |
| `POST` | `/runs/{id}/auto-turn` | Let the current specialist take a generated turn |
| `POST` | `/runs/{id}/turns` | Submit a turn yourself |
| `GET` | `/runs/{id}/report`, `/ledger`, `/proof-gate` | Usefulness report, decision ledger, proof-gate status |
| `POST` | `/runs/{id}/complete` | Complete a run (409 if the proof gate is blocked) |
| `POST` | `/skills/recommendations` | Rank specialists for a goal |

## Meteorology knowledge base

The next direction is an agentic weather decision assistant: agents gather observations and forecasts, compare and calibrate them, and turn them into recommendations ("move the event indoors?") with honest probabilities, verified against what actually happened.

[`docs/meteorology/`](docs/meteorology/README.md) holds the groundwork:

- **19 chapters:**
  - **How forecasters reason:** the forecasting workflow.
  - **The science:** thermodynamics, convection, tropical dynamics, radar and satellite, weather models.
  - **The statistics:** post-processing, ensembles and probability, nowcasting, verification and decision theory.
  - **The local picture:** Singapore weather and hazards, data sources, and an agent pipeline.
  - **Worked examples:** formulas come with worked examples checked in code.
- **Knowledge graph** (`knowledge-graph.json`): 206 concepts and 283 relationships for agents to query.
- **Real data check** ([chapter 19](docs/meteorology/19-real-data-check.md)): every data source was probed live, and samples were analysed.

| Chapter reader with rendered formulas | Concept graph explorer |
| --- | --- |
| ![Knowledge base chapter view](docs/images/knowledge-base-reader.png) | ![Knowledge graph explorer](docs/images/knowledge-base-graph.png) |

### What the real data shows

**Changi averages 2,149 mm of rain a year**, with a wet November–January and a dry February:

![Changi rainfall by month, 1991–2020](docs/images/changi-monthly-rainfall.png)

**Rain timing changes with the season:** late-afternoon storms in December and April, morning rain in July (the Sumatra squall season), and no afternoon peak at all in October 2025. Baselines have to be measured, not assumed:

![Chance of rain by hour at a gauge, one month per season](docs/images/rain-timing-by-season.png)

**Raw model forecasts need calibration:** every model forecast rain days at Changi far more often than they happened in September 2026:

![Forecast rain days by model vs observed, Changi, September 2026](docs/images/forecast-rain-days-vs-observed.png)

Other findings from the data check:
- **NEA live data (data.gov.sg)** covers rain gauges, temperature, humidity, wind, heat stress (30 WBGT stations), lightning strikes and NEA forecasts, with history from December 2016.
- **Radar** is only available as website images (every 5 minutes, about 30 days kept).
- **Rain is very local:** in October 2025, monthly totals ranged from 37 mm to 249 mm across the island.

The charts are produced by [`docs/meteorology/data-check/charts.py`](docs/meteorology/data-check/charts.py) from the committed analysis results.

## Project layout

```
backend/            Rust API server
  src/              routes, scheduler, specialist engine, skill registry, store, models
  tests/            HTTP API tests and an opt-in Postgres/Redis store test
frontend/           Next.js console
  src/components/   hive-shell.tsx (main UI)
  tests/            Playwright end-to-end tests
docs/
  hive-agent-system-plan.md        architecture plan
  alpha-competitive-analysis.md    competitive analysis
  web-research-similar-projects.md research on similar projects
  meteorology/                     weather knowledge base, knowledge graph, data check
  images/                          screenshots and charts used in this README
```
