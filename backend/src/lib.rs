//! Hive Circle backend: a goal-driven multi-agent scheduler served over HTTP.

pub mod error;
pub mod models;
pub mod routes;
pub mod scheduler;
pub mod settings;
pub mod skill_registry;
pub mod specialist_engine;
pub mod store;
pub mod validation;

use std::sync::Arc;

use axum::Router;
use axum::http::HeaderValue;
use axum::routing::{get, post};
use tower_http::cors::{AllowHeaders, AllowMethods, AllowOrigin, CorsLayer};
use tower_http::trace::TraceLayer;

use crate::models::utc_now;
use crate::routes::AppState;
use crate::settings::AppSettings;
use crate::store::Store;

pub fn app_state(store: Store, settings: AppSettings) -> Arc<AppState> {
    Arc::new(AppState {
        store,
        settings,
        started_at: utc_now(),
    })
}

pub fn build_router(state: Arc<AppState>) -> Router {
    let origins: Vec<HeaderValue> = state
        .settings
        .cors_origins
        .iter()
        .filter_map(|origin| HeaderValue::from_str(origin).ok())
        .collect();
    // Credentials are allowed, so methods and headers mirror the request instead of using `*`.
    let cors = CorsLayer::new()
        .allow_origin(AllowOrigin::list(origins))
        .allow_methods(AllowMethods::mirror_request())
        .allow_headers(AllowHeaders::mirror_request())
        .allow_credentials(true);

    Router::new()
        .route("/health", get(routes::health_check))
        .route("/runtime/status", get(routes::runtime_status))
        .route("/bootstrap", get(routes::bootstrap_status))
        .route("/goals", get(routes::list_goals).post(routes::create_goal))
        .route("/goals/{goal_id}", get(routes::get_goal))
        .route(
            "/goals/{goal_id}/runs",
            get(routes::list_goal_runs).post(routes::start_run),
        )
        .route("/runs", get(routes::list_runs))
        .route("/runs/{run_id}", get(routes::get_run))
        .route("/runs/{run_id}/auto-turn", post(routes::auto_turn))
        .route("/runs/{run_id}/turns", post(routes::apply_turn))
        .route("/runs/{run_id}/report", get(routes::get_run_report))
        .route("/runs/{run_id}/ledger", get(routes::get_run_ledger))
        .route("/runs/{run_id}/proof-gate", get(routes::get_run_proof_gate))
        .route("/runs/{run_id}/complete", post(routes::complete_run))
        .route(
            "/skills/recommendations",
            post(routes::get_skill_recommendations),
        )
        .route("/openapi.json", get(routes::openapi_json))
        .route("/docs", get(routes::docs_page))
        .layer(cors)
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}
