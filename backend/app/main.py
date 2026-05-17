from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException

from app.api_models import HealthResponse
from app.models import (
    DecisionLedgerEntry,
    Goal,
    GoalCreateRequest,
    Run,
    RunReport,
    SkillRecommendation,
    SkillRecommendationRequest,
    RunStartRequest,
    RunStatus,
    TurnInput,
)
from app.orchestration.langgraph_graph import build_bootstrap_graph
from app.orchestration.ring_graph import build_turn_graph
from app.orchestration.scheduler import CircleJunctionScheduler
from app.orchestration.skill_registry import recommend_skills
from app.settings import load_settings
from app.store import build_store

@asynccontextmanager
async def lifespan(_: FastAPI):
    _store.initialize()
    try:
        yield
    finally:
        _store.close()


app = FastAPI(
    title="Hive Agent Backend",
    version="0.2.0",
    description="Backend API for the Hive Circle multi-agent platform.",
    lifespan=lifespan,
)

_settings = load_settings()
_store = build_store(_settings)
_scheduler = CircleJunctionScheduler()
_bootstrap_graph = build_bootstrap_graph()
_turn_graph = build_turn_graph(_scheduler)


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="hive-agent-backend")


@app.get("/bootstrap")
def bootstrap_status():
    result = _bootstrap_graph.invoke({"message": "ready", "stage": "init"})
    return {"result": result}


@app.post("/goals", response_model=Goal, status_code=201)
def create_goal(request: GoalCreateRequest) -> Goal:
    goal = Goal(**request.model_dump())
    return _store.create_goal(goal)


@app.get("/goals", response_model=list[Goal])
def list_goals() -> list[Goal]:
    return _store.list_goals()


@app.get("/goals/{goal_id}", response_model=Goal)
def get_goal(goal_id: str) -> Goal:
    goal = _store.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="goal not found")
    return goal


@app.post("/goals/{goal_id}/runs", response_model=Run, status_code=201)
def start_run(goal_id: str, request: RunStartRequest) -> Run:
    goal = _store.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="goal not found")
    run = _scheduler.initialize_run(goal_id=goal_id, request=request)
    return _store.create_run(run)


@app.get("/runs/{run_id}", response_model=Run)
def get_run(run_id: str) -> Run:
    run = _store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@app.post("/runs/{run_id}/turns", response_model=Run)
def apply_turn(run_id: str, turn: TurnInput) -> Run:
    run = _store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    updated = _turn_graph.invoke({"run": run, "turn": turn})["run"]
    return _store.update_run(updated)


@app.get("/runs/{run_id}/report", response_model=RunReport)
def get_run_report(run_id: str) -> RunReport:
    run = _store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return _scheduler.build_report(run)


@app.get("/runs/{run_id}/ledger", response_model=list[DecisionLedgerEntry])
def get_run_ledger(run_id: str) -> list[DecisionLedgerEntry]:
    run = _store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return _scheduler.build_decision_ledger(run)


@app.post("/runs/{run_id}/complete", response_model=Run)
def complete_run(run_id: str) -> Run:
    run = _store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    run.status = RunStatus.COMPLETED
    return _store.update_run(run)


@app.post("/skills/recommendations", response_model=list[SkillRecommendation])
def get_skill_recommendations(
    request: SkillRecommendationRequest,
) -> list[SkillRecommendation]:
    return recommend_skills(request)
