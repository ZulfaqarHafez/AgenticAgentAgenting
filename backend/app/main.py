from contextlib import asynccontextmanager
from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api_models import HealthResponse, RuntimeStatusResponse
from app.models import (
    AutoTurnRequest,
    DecisionLedgerEntry,
    Goal,
    GoalCreateRequest,
    ProofGateStatus,
    Run,
    RunMode,
    RunReport,
    SkillRecommendation,
    SkillRecommendationRequest,
    SpecialistRole,
    RunStartRequest,
    RunStatus,
    TurnInput,
    utc_now,
)
from app.orchestration.langgraph_graph import build_bootstrap_graph
from app.orchestration.ring_graph import build_turn_graph
from app.orchestration.scheduler import CircleJunctionScheduler
from app.orchestration.specialist_engine import SpecialistEngine
from app.orchestration.skill_registry import recommend_skills
from app.settings import load_settings
from app.store import build_store

_settings = load_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    _store.initialize()
    try:
        yield
    finally:
        _store.close()


app = FastAPI(
    title="Hive Agent Backend",
    version="0.3.0",
    description="Backend API for the Hive Circle multi-agent platform.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_store = build_store(_settings)
_scheduler = CircleJunctionScheduler()
_specialist_engine = SpecialistEngine()
_bootstrap_graph = build_bootstrap_graph()
_turn_graph = build_turn_graph(_scheduler)
_server_started_at = utc_now()


def _resolve_run_mode_request(request: RunStartRequest) -> RunStartRequest:
    include_roles = request.include_roles
    auto_role_limit = request.auto_role_limit
    min_usefulness = request.min_usefulness

    if request.run_mode == RunMode.LITE:
        include_roles = include_roles or [
            SpecialistRole.PLANNER,
            SpecialistRole.RESEARCH,
            SpecialistRole.VERIFIER,
        ]
        auto_role_limit = min(auto_role_limit, 2)
        min_usefulness = min(min_usefulness, 0.3)
    elif request.run_mode == RunMode.POWER:
        include_roles = include_roles or list(SpecialistRole)
        auto_role_limit = 5
        min_usefulness = max(min_usefulness, 0.45)

    return request.model_copy(
        update={
            "include_roles": include_roles,
            "auto_role_limit": auto_role_limit,
            "min_usefulness": min_usefulness,
        }
    )


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="hive-agent-backend")


@app.get("/runtime/status", response_model=RuntimeStatusResponse)
def runtime_status() -> RuntimeStatusResponse:
    now = utc_now()
    runs = _store.list_runs()
    active_runs = sum(1 for run in runs if run.status == RunStatus.ACTIVE)
    return RuntimeStatusResponse(
        status="ok",
        service="hive-agent-backend",
        api_version=app.version,
        contract_version="run-start.v2",
        recommended_roles_supported=True,
        decision_ledger_supported=True,
        store_backend=_settings.store_backend.value,
        server_started_at=_server_started_at,
        server_now=now,
        uptime_seconds=round((now - _server_started_at).total_seconds(), 3),
        total_runs=len(runs),
        active_runs=active_runs,
    )


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


@app.get("/goals/{goal_id}/runs", response_model=list[Run])
def list_goal_runs(goal_id: str) -> list[Run]:
    goal = _store.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="goal not found")
    return [run for run in _store.list_runs() if run.goal_id == goal_id]


@app.post("/goals/{goal_id}/runs", response_model=Run, status_code=201)
def start_run(
    goal_id: str, request: RunStartRequest = Body(default_factory=RunStartRequest)
) -> Run:
    goal = _store.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="goal not found")
    request = _resolve_run_mode_request(request)
    activation_strategy = "manual_active_roles"
    activation_recommendations: list[SkillRecommendation] = []
    resolved_roles = request.active_roles

    if not resolved_roles:
        recommended = recommend_skills(
            SkillRecommendationRequest(
                goal_title=goal.title,
                success_criteria=goal.success_criteria,
                constraints=goal.constraints,
                include_roles=request.include_roles,
                limit=request.auto_role_limit,
            )
        )
        resolved_roles = [rec.role for rec in recommended]
        activation_recommendations = recommended
        activation_strategy = "recommended_roles"

    resolved_request = request.model_copy(update={"active_roles": resolved_roles})
    run = _scheduler.initialize_run(goal_id=goal_id, request=resolved_request)
    run.activation_strategy = activation_strategy
    run.activation_recommendations = activation_recommendations
    run.run_mode = request.run_mode
    return _store.create_run(run)


@app.get("/runs/{run_id}", response_model=Run)
def get_run(run_id: str) -> Run:
    run = _store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@app.get("/runs", response_model=list[Run])
def list_runs() -> list[Run]:
    return _store.list_runs()


@app.post("/runs/{run_id}/auto-turn", response_model=Run)
async def auto_turn(run_id: str, request: AutoTurnRequest) -> Run:
    run = _store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    goal = _store.get_goal(run.goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="goal not found")
    generated_turn = await _specialist_engine.build_turn(goal, run, request)
    updated = _turn_graph.invoke({"run": run, "turn": generated_turn})["run"]
    return _store.update_run(updated)


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


@app.get("/runs/{run_id}/proof-gate", response_model=ProofGateStatus)
def get_run_proof_gate(run_id: str) -> ProofGateStatus:
    run = _store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run.proof_gate_status


@app.post("/runs/{run_id}/complete", response_model=Run)
def complete_run(run_id: str) -> Run:
    run = _store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    if not run.proof_gate_status.ready_to_complete:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "proof gate blocked completion",
                "blockers": run.proof_gate_status.blockers,
            },
        )
    run.status = RunStatus.COMPLETED
    return _store.update_run(run)


@app.post("/skills/recommendations", response_model=list[SkillRecommendation])
def get_skill_recommendations(
    request: SkillRecommendationRequest,
) -> list[SkillRecommendation]:
    return recommend_skills(request)
