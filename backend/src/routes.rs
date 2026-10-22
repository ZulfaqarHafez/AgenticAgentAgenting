//! HTTP handlers. Paths, status codes and JSON shapes match the original FastAPI service.

use std::sync::Arc;

use axum::Json;
use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::response::Html;
use chrono::{DateTime, Utc};
use serde_json::{Value, json};
use utoipa::OpenApi;

use crate::error::{ApiError, ApiResult};
use crate::models::{
    AutoTurnRequest, DecisionLedgerEntry, Goal, GoalCreateRequest, HealthResponse, ProofGateStatus,
    Run, RunMode, RunReport, RunStartRequest, RunStatus, RuntimeStatusResponse,
    SkillRecommendation, SkillRecommendationRequest, SpecialistRole, TurnInput, round3, utc_now,
};
use crate::settings::AppSettings;
use crate::store::Store;
use crate::validation::{OptionalJson, ValidJson};
use crate::{scheduler, skill_registry, specialist_engine};

pub const SERVICE_NAME: &str = "hive-agent-backend";
pub const API_VERSION: &str = "0.3.0";
pub const CONTRACT_VERSION: &str = "run-start.v2";

pub struct AppState {
    pub store: Store,
    pub settings: AppSettings,
    pub started_at: DateTime<Utc>,
}

pub type SharedState = State<Arc<AppState>>;

#[derive(OpenApi)]
#[openapi(
    info(
        title = "Hive Agent Backend",
        version = "0.3.0",
        description = "Backend API for the Hive Circle multi-agent platform."
    ),
    paths(
        health_check,
        runtime_status,
        bootstrap_status,
        create_goal,
        list_goals,
        get_goal,
        list_goal_runs,
        start_run,
        get_run,
        list_runs,
        auto_turn,
        apply_turn,
        get_run_report,
        get_run_ledger,
        get_run_proof_gate,
        complete_run,
        get_skill_recommendations,
    )
)]
pub struct ApiDoc;

async fn load_goal(state: &AppState, goal_id: &str) -> ApiResult<Goal> {
    state
        .store
        .get_goal(goal_id)
        .await?
        .ok_or_else(|| ApiError::not_found("goal not found"))
}

async fn load_run(state: &AppState, run_id: &str) -> ApiResult<Run> {
    state
        .store
        .get_run(run_id)
        .await?
        .ok_or_else(|| ApiError::not_found("run not found"))
}

/// Applies the lite/power presets on top of the caller's options.
fn resolve_run_mode_request(mut request: RunStartRequest) -> RunStartRequest {
    let no_include_roles = request.include_roles.as_ref().is_none_or(Vec::is_empty);
    match request.run_mode {
        RunMode::Lite => {
            if no_include_roles {
                request.include_roles = Some(vec![
                    SpecialistRole::Planner,
                    SpecialistRole::Research,
                    SpecialistRole::Verifier,
                ]);
            }
            request.auto_role_limit = request.auto_role_limit.min(2);
            request.min_usefulness = request.min_usefulness.min(0.3);
        }
        RunMode::Power => {
            if no_include_roles {
                request.include_roles = Some(SpecialistRole::ALL.to_vec());
            }
            request.auto_role_limit = 5;
            request.min_usefulness = request.min_usefulness.max(0.45);
        }
        RunMode::Balanced => {}
    }
    request
}

#[utoipa::path(get, path = "/health", responses((status = 200, body = HealthResponse)))]
pub async fn health_check() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok".into(),
        service: SERVICE_NAME.into(),
    })
}

#[utoipa::path(get, path = "/runtime/status", responses((status = 200, body = RuntimeStatusResponse)))]
pub async fn runtime_status(State(state): SharedState) -> ApiResult<Json<RuntimeStatusResponse>> {
    let now = utc_now();
    let runs = state.store.list_runs().await?;
    let active_runs = runs
        .iter()
        .filter(|run| run.status == RunStatus::Active)
        .count();
    let uptime_ms = (now - state.started_at).num_milliseconds();
    Ok(Json(RuntimeStatusResponse {
        status: "ok".into(),
        service: SERVICE_NAME.into(),
        api_version: API_VERSION.into(),
        contract_version: CONTRACT_VERSION.into(),
        recommended_roles_supported: true,
        decision_ledger_supported: true,
        store_backend: state.settings.store_backend.as_str().into(),
        server_started_at: state.started_at,
        server_now: now,
        uptime_seconds: round3(uptime_ms as f64 / 1000.0),
        total_runs: runs.len(),
        active_runs,
    }))
}

#[utoipa::path(get, path = "/bootstrap", responses((status = 200, body = Object)))]
pub async fn bootstrap_status() -> Json<Value> {
    Json(json!({ "result": { "message": "ready", "stage": "bootstrapped" } }))
}

#[utoipa::path(
    post,
    path = "/goals",
    request_body = GoalCreateRequest,
    responses((status = 201, body = Goal), (status = 422, description = "Validation error"))
)]
pub async fn create_goal(
    State(state): SharedState,
    ValidJson(request): ValidJson<GoalCreateRequest>,
) -> ApiResult<(StatusCode, Json<Goal>)> {
    let goal = state.store.create_goal(Goal::from(request)).await?;
    Ok((StatusCode::CREATED, Json(goal)))
}

#[utoipa::path(get, path = "/goals", responses((status = 200, body = Vec<Goal>)))]
pub async fn list_goals(State(state): SharedState) -> ApiResult<Json<Vec<Goal>>> {
    Ok(Json(state.store.list_goals().await?))
}

#[utoipa::path(
    get,
    path = "/goals/{goal_id}",
    params(("goal_id" = String, Path)),
    responses((status = 200, body = Goal), (status = 404, description = "Goal not found"))
)]
pub async fn get_goal(
    State(state): SharedState,
    Path(goal_id): Path<String>,
) -> ApiResult<Json<Goal>> {
    Ok(Json(load_goal(&state, &goal_id).await?))
}

#[utoipa::path(
    get,
    path = "/goals/{goal_id}/runs",
    params(("goal_id" = String, Path)),
    responses((status = 200, body = Vec<Run>), (status = 404, description = "Goal not found"))
)]
pub async fn list_goal_runs(
    State(state): SharedState,
    Path(goal_id): Path<String>,
) -> ApiResult<Json<Vec<Run>>> {
    load_goal(&state, &goal_id).await?;
    let runs = state.store.list_runs().await?;
    Ok(Json(
        runs.into_iter()
            .filter(|run| run.goal_id == goal_id)
            .collect(),
    ))
}

/// Starts a run. With no `active_roles`, roles are picked by the skill recommender.
#[utoipa::path(
    post,
    path = "/goals/{goal_id}/runs",
    params(("goal_id" = String, Path)),
    request_body(content = Option<RunStartRequest>, description = "Optional; omit for defaults"),
    responses(
        (status = 201, body = Run),
        (status = 404, description = "Goal not found"),
        (status = 422, description = "Validation error")
    )
)]
pub async fn start_run(
    State(state): SharedState,
    Path(goal_id): Path<String>,
    OptionalJson(request): OptionalJson<RunStartRequest>,
) -> ApiResult<(StatusCode, Json<Run>)> {
    let goal = load_goal(&state, &goal_id).await?;
    let mut request = resolve_run_mode_request(request);

    let mut activation_strategy = "manual_active_roles";
    let mut activation_recommendations = Vec::new();
    if request.active_roles.as_ref().is_none_or(Vec::is_empty) {
        let recommended = skill_registry::recommend_skills(&SkillRecommendationRequest {
            goal_title: goal.title.clone(),
            success_criteria: goal.success_criteria.clone(),
            constraints: goal.constraints.clone(),
            include_roles: request.include_roles.clone(),
            limit: request.auto_role_limit,
        });
        request.active_roles = Some(recommended.iter().map(|rec| rec.role).collect());
        activation_recommendations = recommended;
        activation_strategy = "recommended_roles";
    }

    let mut run = scheduler::initialize_run(&goal_id, &request)?;
    run.activation_strategy = activation_strategy.to_string();
    run.activation_recommendations = activation_recommendations;
    let run = state.store.create_run(run).await?;
    Ok((StatusCode::CREATED, Json(run)))
}

#[utoipa::path(
    get,
    path = "/runs/{run_id}",
    params(("run_id" = String, Path)),
    responses((status = 200, body = Run), (status = 404, description = "Run not found"))
)]
pub async fn get_run(
    State(state): SharedState,
    Path(run_id): Path<String>,
) -> ApiResult<Json<Run>> {
    Ok(Json(load_run(&state, &run_id).await?))
}

#[utoipa::path(get, path = "/runs", responses((status = 200, body = Vec<Run>)))]
pub async fn list_runs(State(state): SharedState) -> ApiResult<Json<Vec<Run>>> {
    Ok(Json(state.store.list_runs().await?))
}

/// Lets the current specialist take a generated turn.
#[utoipa::path(
    post,
    path = "/runs/{run_id}/auto-turn",
    params(("run_id" = String, Path)),
    request_body = AutoTurnRequest,
    responses(
        (status = 200, body = Run),
        (status = 404, description = "Run or goal not found"),
        (status = 409, description = "Run is not active"),
        (status = 422, description = "Validation error")
    )
)]
pub async fn auto_turn(
    State(state): SharedState,
    Path(run_id): Path<String>,
    ValidJson(request): ValidJson<AutoTurnRequest>,
) -> ApiResult<Json<Run>> {
    let mut run = load_run(&state, &run_id).await?;
    let goal = load_goal(&state, &run.goal_id).await?;
    let turn = specialist_engine::build_turn(&goal, &run, &request);
    scheduler::apply_turn(&mut run, turn)?;
    Ok(Json(state.store.update_run(run).await?))
}

/// Records a turn written by the caller.
#[utoipa::path(
    post,
    path = "/runs/{run_id}/turns",
    params(("run_id" = String, Path)),
    request_body = TurnInput,
    responses(
        (status = 200, body = Run),
        (status = 404, description = "Run not found"),
        (status = 409, description = "Wrong role or run not active"),
        (status = 422, description = "Validation error")
    )
)]
pub async fn apply_turn(
    State(state): SharedState,
    Path(run_id): Path<String>,
    ValidJson(turn): ValidJson<TurnInput>,
) -> ApiResult<Json<Run>> {
    let mut run = load_run(&state, &run_id).await?;
    scheduler::apply_turn(&mut run, turn)?;
    Ok(Json(state.store.update_run(run).await?))
}

#[utoipa::path(
    get,
    path = "/runs/{run_id}/report",
    params(("run_id" = String, Path)),
    responses((status = 200, body = RunReport), (status = 404, description = "Run not found"))
)]
pub async fn get_run_report(
    State(state): SharedState,
    Path(run_id): Path<String>,
) -> ApiResult<Json<RunReport>> {
    Ok(Json(scheduler::build_report(
        &load_run(&state, &run_id).await?,
    )))
}

#[utoipa::path(
    get,
    path = "/runs/{run_id}/ledger",
    params(("run_id" = String, Path)),
    responses(
        (status = 200, body = Vec<DecisionLedgerEntry>),
        (status = 404, description = "Run not found")
    )
)]
pub async fn get_run_ledger(
    State(state): SharedState,
    Path(run_id): Path<String>,
) -> ApiResult<Json<Vec<DecisionLedgerEntry>>> {
    Ok(Json(scheduler::build_decision_ledger(
        &load_run(&state, &run_id).await?,
    )))
}

#[utoipa::path(
    get,
    path = "/runs/{run_id}/proof-gate",
    params(("run_id" = String, Path)),
    responses((status = 200, body = ProofGateStatus), (status = 404, description = "Run not found"))
)]
pub async fn get_run_proof_gate(
    State(state): SharedState,
    Path(run_id): Path<String>,
) -> ApiResult<Json<ProofGateStatus>> {
    Ok(Json(load_run(&state, &run_id).await?.proof_gate_status))
}

/// Marks a run completed, if the proof gate allows it.
#[utoipa::path(
    post,
    path = "/runs/{run_id}/complete",
    params(("run_id" = String, Path)),
    responses(
        (status = 200, body = Run),
        (status = 404, description = "Run not found"),
        (status = 409, description = "Proof gate blocked completion")
    )
)]
pub async fn complete_run(
    State(state): SharedState,
    Path(run_id): Path<String>,
) -> ApiResult<Json<Run>> {
    let mut run = load_run(&state, &run_id).await?;
    if !run.proof_gate_status.ready_to_complete {
        return Err(ApiError::conflict(json!({
            "message": "proof gate blocked completion",
            "blockers": run.proof_gate_status.blockers,
        })));
    }
    run.status = RunStatus::Completed;
    Ok(Json(state.store.update_run(run).await?))
}

#[utoipa::path(
    post,
    path = "/skills/recommendations",
    request_body = SkillRecommendationRequest,
    responses(
        (status = 200, body = Vec<SkillRecommendation>),
        (status = 422, description = "Validation error")
    )
)]
pub async fn get_skill_recommendations(
    ValidJson(request): ValidJson<SkillRecommendationRequest>,
) -> Json<Vec<SkillRecommendation>> {
    Json(skill_registry::recommend_skills(&request))
}

pub async fn openapi_json() -> Json<utoipa::openapi::OpenApi> {
    Json(ApiDoc::openapi())
}

/// Swagger UI loaded from a CDN, like FastAPI's `/docs`.
pub async fn docs_page() -> Html<&'static str> {
    Html(
        r##"<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Hive Agent Backend - Swagger UI</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
  <script>SwaggerUIBundle({ url: "/openapi.json", dom_id: "#swagger-ui" });</script>
</body>
</html>"##,
    )
}
