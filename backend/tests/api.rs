//! End-to-end tests of the HTTP API against the in-memory store.

use axum::Router;
use axum::body::Body;
use axum::http::{Method, Request, StatusCode};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;

use hive_agent_backend::settings::AppSettings;
use hive_agent_backend::store::Store;
use hive_agent_backend::{app_state, build_router};

fn app() -> Router {
    build_router(app_state(Store::memory(), AppSettings::default()))
}

struct Response {
    status: StatusCode,
    headers: axum::http::HeaderMap,
    text: String,
}

impl Response {
    fn json(&self) -> Value {
        serde_json::from_str(&self.text).unwrap_or_else(|_| panic!("not JSON: {}", self.text))
    }
}

async fn send(app: &Router, request: Request<Body>) -> Response {
    let response = app.clone().oneshot(request).await.unwrap();
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    Response {
        status,
        headers,
        text: String::from_utf8(bytes.to_vec()).unwrap(),
    }
}

async fn get(app: &Router, path: &str) -> Response {
    send(app, Request::get(path).body(Body::empty()).unwrap()).await
}

async fn post(app: &Router, path: &str, body: Option<Value>) -> Response {
    let builder = Request::post(path).header("content-type", "application/json");
    let body = body.map_or_else(Body::empty, |value| Body::from(value.to_string()));
    send(app, builder.body(body).unwrap()).await
}

async fn create_goal(app: &Router, title: &str, constraints: Value) -> String {
    let response = post(
        app,
        "/goals",
        Some(json!({
            "title": title,
            "success_criteria": ["Define architecture", "Define fallback"],
            "constraints": constraints,
            "priority": "high",
        })),
    )
    .await;
    assert_eq!(response.status, StatusCode::CREATED, "{}", response.text);
    response.json()["goal_id"].as_str().unwrap().to_string()
}

#[tokio::test]
async fn health_and_bootstrap() {
    let app = app();
    let health = get(&app, "/health").await;
    assert_eq!(health.status, StatusCode::OK);
    assert_eq!(
        health.json(),
        json!({"status": "ok", "service": "hive-agent-backend"})
    );

    let bootstrap = get(&app, "/bootstrap").await;
    assert_eq!(bootstrap.json()["result"]["stage"], "bootstrapped");
}

#[tokio::test]
async fn runtime_status_reports_contract_and_counts_runs() {
    let app = app();
    let status = get(&app, "/runtime/status").await.json();
    assert_eq!(status["api_version"], "0.3.0");
    assert_eq!(status["contract_version"], "run-start.v2");
    assert_eq!(status["store_backend"], "memory");
    assert_eq!(status["recommended_roles_supported"], true);
    assert_eq!(status["decision_ledger_supported"], true);
    assert!(status["uptime_seconds"].is_number());
    assert!(status["server_started_at"].is_string());
    assert_eq!(status["total_runs"], 0);

    let goal_id = create_goal(&app, "Runtime count goal", json!([])).await;
    post(
        &app,
        &format!("/goals/{goal_id}/runs"),
        Some(json!({"active_roles": ["planner"]})),
    )
    .await;
    let status = get(&app, "/runtime/status").await.json();
    assert_eq!(status["total_runs"], 1);
    assert_eq!(status["active_runs"], 1);
}

#[tokio::test]
async fn goal_lifecycle_and_run_report() {
    let app = app();
    let goal_id = create_goal(&app, "Plan adaptable hive", json!(["Latency under 15s"])).await;

    let goal = get(&app, &format!("/goals/{goal_id}")).await.json();
    assert_eq!(goal["status"], "active");
    assert_eq!(goal["priority"], "high");
    assert_eq!(
        get(&app, "/goals").await.json().as_array().unwrap().len(),
        1
    );

    let run = post(
        &app,
        &format!("/goals/{goal_id}/runs"),
        Some(json!({
            "active_roles": ["planner", "research", "verifier"],
            "min_usefulness": 0.35,
            "max_low_value_streak": 2,
            "enable_priority_preemption": true,
        })),
    )
    .await;
    assert_eq!(run.status, StatusCode::CREATED);
    let run = run.json();
    assert_eq!(run["current_role"], "planner");
    assert_eq!(run["activation_strategy"], "manual_active_roles");
    let run_id = run["run_id"].as_str().unwrap();

    let turn_1 = post(
        &app,
        &format!("/runs/{run_id}/turns"),
        Some(json!({
            "role": "planner",
            "contribution": "Initial decomposition",
            "confidence": 0.8,
            "evidence_refs": [],
            "usefulness_score": 0.8,
            "pass_turn": false,
            "priority_override": false,
            "requested_next_role": null,
        })),
    )
    .await;
    assert_eq!(turn_1.status, StatusCode::OK, "{}", turn_1.text);
    assert_eq!(turn_1.json()["current_role"], "research");

    let turn_2 = post(
        &app,
        &format!("/runs/{run_id}/turns"),
        Some(json!({
            "role": "research",
            "contribution": "Found source-backed patterns",
            "confidence": 0.9,
            "evidence_refs": ["https://example.com/a"],
            "usefulness_score": 0.85,
        })),
    )
    .await;
    assert_eq!(turn_2.json()["current_role"], "verifier");

    let report = get(&app, &format!("/runs/{run_id}/report")).await.json();
    assert_eq!(report["turns"], 2);
    assert_eq!(report["role_turn_counts"]["planner"], 1);
    assert_eq!(report["role_turn_counts"]["research"], 1);
    assert_eq!(report["role_turn_counts"]["verifier"], 0);
    assert_eq!(report["fallback_layer"], "layer_1_circle_junction");
    assert_eq!(report["proof_gate_status"]["state"], "blocked");

    let ledger = get(&app, &format!("/runs/{run_id}/ledger")).await.json();
    let event_types: Vec<_> = ledger
        .as_array()
        .unwrap()
        .iter()
        .map(|event| event["event_type"].as_str().unwrap())
        .collect();
    assert_eq!(
        event_types,
        [
            "role_activation",
            "confidence_shift",
            "role_activation",
            "confidence_shift"
        ]
    );
    assert_eq!(ledger[3]["confidence_delta"], 0.1);
}

#[tokio::test]
async fn out_of_turn_role_is_rejected() {
    let app = app();
    let goal_id = create_goal(&app, "Out of turn goal", json!([])).await;
    let run = post(
        &app,
        &format!("/goals/{goal_id}/runs"),
        Some(json!({"active_roles": ["planner", "research"]})),
    )
    .await
    .json();
    let response = post(
        &app,
        &format!("/runs/{}/turns", run["run_id"].as_str().unwrap()),
        Some(json!({"role": "research", "contribution": "Too early", "confidence": 0.5})),
    )
    .await;
    assert_eq!(response.status, StatusCode::CONFLICT);
    assert_eq!(
        response.json()["detail"],
        "expected role 'planner' but got 'research'"
    );
}

#[tokio::test]
async fn start_run_auto_recommended_roles() {
    let app = app();
    let goal_id = create_goal(&app, "Auto role goal", json!(["Verify role selection"])).await;
    let run = post(
        &app,
        &format!("/goals/{goal_id}/runs"),
        Some(json!({
            "include_roles": ["planner", "research", "verifier"],
            "auto_role_limit": 3,
        })),
    )
    .await
    .json();
    assert_eq!(run["activation_strategy"], "recommended_roles");
    assert_eq!(run["active_roles"].as_array().unwrap().len(), 3);
    assert_eq!(
        run["activation_recommendations"].as_array().unwrap().len(),
        3
    );
}

#[tokio::test]
async fn start_run_with_empty_body_uses_recommended_roles() {
    let app = app();
    let goal_id = create_goal(&app, "Body omitted goal", json!([])).await;
    let response = post(&app, &format!("/goals/{goal_id}/runs"), None).await;
    assert_eq!(response.status, StatusCode::CREATED, "{}", response.text);
    let run = response.json();
    assert_eq!(run["activation_strategy"], "recommended_roles");
    assert_eq!(run["run_mode"], "balanced");
    assert_eq!(run["active_roles"].as_array().unwrap().len(), 3);
}

#[tokio::test]
async fn run_modes_change_role_depth() {
    let app = app();
    let goal_id = create_goal(&app, "Mode goal", json!([])).await;

    let power = post(
        &app,
        &format!("/goals/{goal_id}/runs"),
        Some(json!({"run_mode": "power"})),
    )
    .await
    .json();
    assert_eq!(power["run_mode"], "power");
    assert_eq!(power["active_roles"].as_array().unwrap().len(), 5);
    assert_eq!(power["min_usefulness"], 0.45);

    let lite = post(
        &app,
        &format!("/goals/{goal_id}/runs"),
        Some(json!({"run_mode": "lite"})),
    )
    .await
    .json();
    assert_eq!(lite["run_mode"], "lite");
    assert_eq!(lite["active_roles"].as_array().unwrap().len(), 2);
    assert_eq!(lite["min_usefulness"], 0.3);

    let history = get(&app, &format!("/goals/{goal_id}/runs")).await.json();
    assert_eq!(history.as_array().unwrap().len(), 2);
    assert!(
        history
            .as_array()
            .unwrap()
            .iter()
            .all(|run| run["goal_id"] == goal_id.as_str())
    );
}

#[tokio::test]
async fn auto_turn_generates_specialist_output() {
    let app = app();
    let goal_id = create_goal(&app, "Auto turn generation", json!(["Keep baton visible"])).await;
    let run = post(
        &app,
        &format!("/goals/{goal_id}/runs"),
        Some(json!({"run_mode": "balanced"})),
    )
    .await
    .json();
    let run_id = run["run_id"].as_str().unwrap();
    let first_role = run["current_role"].as_str().unwrap().to_string();

    let response = post(
        &app,
        &format!("/runs/{run_id}/auto-turn"),
        Some(json!({"user_prompt": "Map the baton and the fallback path."})),
    )
    .await;
    assert_eq!(response.status, StatusCode::OK, "{}", response.text);
    let updated = response.json();
    let latest = &updated["turn_history"][0];
    assert_eq!(latest["role"], first_role.as_str());
    assert_eq!(
        latest["user_prompt"],
        "Map the baton and the fallback path."
    );
    assert_eq!(
        latest["specialist_output"]["provider"],
        "prompted_local_engine"
    );
    assert!(
        !latest["specialist_output"]["prompt_title"]
            .as_str()
            .unwrap()
            .is_empty()
    );
    let contribution = latest["contribution"].as_str().unwrap();
    assert!(
        [
            "Mission frame",
            "Signals",
            "Proof check",
            "Implementation move",
            "Contrarian read"
        ]
        .iter()
        .any(|marker| contribution.contains(marker)),
        "{contribution}"
    );
}

#[tokio::test]
async fn proof_gate_blocks_then_allows_completion() {
    let app = app();
    let goal_id = create_goal(&app, "Proof gate completion", json!(["Need evidence"])).await;
    let run = post(
        &app,
        &format!("/goals/{goal_id}/runs"),
        Some(json!({"run_mode": "balanced"})),
    )
    .await
    .json();
    let run_id = run["run_id"].as_str().unwrap();

    let blocked = post(&app, &format!("/runs/{run_id}/complete"), None).await;
    assert_eq!(blocked.status, StatusCode::CONFLICT);
    assert_eq!(
        blocked.json()["detail"]["message"],
        "proof gate blocked completion"
    );
    assert!(
        !blocked.json()["detail"]["blockers"]
            .as_array()
            .unwrap()
            .is_empty()
    );

    for prompt in [
        "Plan the system.",
        "Research supporting evidence.",
        "Verify release readiness.",
    ] {
        let response = post(
            &app,
            &format!("/runs/{run_id}/auto-turn"),
            Some(json!({"user_prompt": prompt})),
        )
        .await;
        assert_eq!(response.status, StatusCode::OK, "{}", response.text);
    }

    let gate = get(&app, &format!("/runs/{run_id}/proof-gate"))
        .await
        .json();
    assert_eq!(gate["ready_to_complete"], true, "{gate}");
    assert_eq!(gate["verifier_turn_observed"], true);

    let completed = post(&app, &format!("/runs/{run_id}/complete"), None).await;
    assert_eq!(completed.status, StatusCode::OK);
    assert_eq!(completed.json()["status"], "completed");

    let after = post(
        &app,
        &format!("/runs/{run_id}/auto-turn"),
        Some(json!({"user_prompt": "One more?"})),
    )
    .await;
    assert_eq!(after.status, StatusCode::CONFLICT);
    assert_eq!(after.json()["detail"], "run is not active");
}

#[tokio::test]
async fn priority_preemption_records_fallback_transition() {
    let app = app();
    let goal_id = create_goal(&app, "Preemption goal", json!([])).await;
    let run = post(
        &app,
        &format!("/goals/{goal_id}/runs"),
        Some(json!({"active_roles": ["planner", "research", "verifier"]})),
    )
    .await
    .json();
    let run_id = run["run_id"].as_str().unwrap();

    let updated = post(
        &app,
        &format!("/runs/{run_id}/turns"),
        Some(json!({
            "role": "verifier",
            "contribution": "Urgent contradiction found",
            "confidence": 0.95,
            "usefulness_score": 0.9,
            "priority_override": true,
        })),
    )
    .await
    .json();
    assert_eq!(updated["turn_history"][0]["outcome"], "priority_preempted");

    let ledger = get(&app, &format!("/runs/{run_id}/ledger")).await.json();
    let fallback = ledger
        .as_array()
        .unwrap()
        .iter()
        .find(|event| event["event_type"] == "fallback_transition")
        .expect("fallback event");
    assert_eq!(fallback["fallback_from"], "layer_1_circle_junction");
    assert_eq!(fallback["fallback_to"], "layer_2_verifier_guard");
}

#[tokio::test]
async fn skill_recommendations_are_ranked_and_filtered() {
    let app = app();
    let recs = post(
        &app,
        "/skills/recommendations",
        Some(json!({
            "goal_title": "Research and benchmark agent frameworks with verification",
            "success_criteria": ["Collect evidence", "Validate claims"],
            "constraints": ["Keep risk low"],
            "limit": 3,
        })),
    )
    .await
    .json();
    let scores: Vec<f64> = recs
        .as_array()
        .unwrap()
        .iter()
        .map(|rec| rec["activation_score"].as_f64().unwrap())
        .collect();
    assert_eq!(scores.len(), 3);
    assert!(scores.windows(2).all(|pair| pair[0] >= pair[1]));

    let filtered = post(
        &app,
        "/skills/recommendations",
        Some(json!({"goal_title": "Plan delivery milestones", "include_roles": ["planner", "verifier"], "limit": 2})),
    )
    .await
    .json();
    for rec in filtered.as_array().unwrap() {
        assert!(rec["role"] == "planner" || rec["role"] == "verifier");
    }
}

#[tokio::test]
async fn missing_resources_return_404() {
    let app = app();
    for path in [
        "/goals/G-missing",
        "/goals/G-missing/runs",
        "/runs/R-missing",
        "/runs/R-missing/report",
    ] {
        let response = get(&app, path).await;
        assert_eq!(response.status, StatusCode::NOT_FOUND, "{path}");
        assert!(
            response.json()["detail"]
                .as_str()
                .unwrap()
                .ends_with("not found")
        );
    }
    let response = post(&app, "/goals/G-missing/runs", None).await;
    assert_eq!(response.status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn invalid_bodies_return_422_with_field_locations() {
    let app = app();

    let short_title = post(
        &app,
        "/goals",
        Some(json!({"title": "ab", "success_criteria": ["x"]})),
    )
    .await;
    assert_eq!(short_title.status, StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        short_title.json()["detail"][0]["loc"],
        json!(["body", "title"])
    );

    let no_criteria = post(
        &app,
        "/goals",
        Some(json!({"title": "Valid title", "success_criteria": []})),
    )
    .await;
    assert_eq!(no_criteria.status, StatusCode::UNPROCESSABLE_ENTITY);

    let bad_priority = post(
        &app,
        "/goals",
        Some(json!({"title": "Valid title", "success_criteria": ["x"], "priority": "urgent"})),
    )
    .await;
    assert_eq!(bad_priority.status, StatusCode::UNPROCESSABLE_ENTITY);

    let not_json = send(
        &app,
        Request::post("/goals")
            .header("content-type", "application/json")
            .body(Body::from("{"))
            .unwrap(),
    )
    .await;
    assert_eq!(not_json.status, StatusCode::UNPROCESSABLE_ENTITY);

    let goal_id = create_goal(&app, "Validation goal", json!([])).await;
    let bad_limit = post(
        &app,
        &format!("/goals/{goal_id}/runs"),
        Some(json!({"auto_role_limit": 9})),
    )
    .await;
    assert_eq!(bad_limit.status, StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        bad_limit.json()["detail"][0]["loc"],
        json!(["body", "auto_role_limit"])
    );

    let run = post(&app, &format!("/goals/{goal_id}/runs"), None)
        .await
        .json();
    let run_id = run["run_id"].as_str().unwrap();
    let pass_with_text = post(
        &app,
        &format!("/runs/{run_id}/turns"),
        Some(json!({"role": run["current_role"], "pass_turn": true, "contribution": "hi"})),
    )
    .await;
    assert_eq!(pass_with_text.status, StatusCode::UNPROCESSABLE_ENTITY);

    let empty_contribution = post(
        &app,
        &format!("/runs/{run_id}/turns"),
        Some(json!({"role": run["current_role"], "contribution": "   "})),
    )
    .await;
    assert_eq!(empty_contribution.status, StatusCode::UNPROCESSABLE_ENTITY);

    let short_prompt = post(
        &app,
        &format!("/runs/{run_id}/auto-turn"),
        Some(json!({"user_prompt": "hi"})),
    )
    .await;
    assert_eq!(short_prompt.status, StatusCode::UNPROCESSABLE_ENTITY);
}

#[tokio::test]
async fn cors_preflight_allows_local_dev_origins() {
    let app = app();
    for origin in ["http://localhost:3000", "http://127.0.0.1:3010"] {
        let response = send(
            &app,
            Request::builder()
                .method(Method::OPTIONS)
                .uri("/goals")
                .header("origin", origin)
                .header("access-control-request-method", "POST")
                .header("access-control-request-headers", "content-type")
                .body(Body::empty())
                .unwrap(),
        )
        .await;
        assert_eq!(response.status, StatusCode::OK);
        assert_eq!(response.headers["access-control-allow-origin"], origin);
        assert_eq!(response.headers["access-control-allow-credentials"], "true");
    }

    let simple = send(
        &app,
        Request::post("/goals")
            .header("origin", "http://localhost:3000")
            .header("content-type", "application/json")
            .body(Body::from(
                json!({"title": "CORS goal", "success_criteria": ["x"]}).to_string(),
            ))
            .unwrap(),
    )
    .await;
    assert_eq!(simple.status, StatusCode::CREATED);
    assert_eq!(
        simple.headers["access-control-allow-origin"],
        "http://localhost:3000"
    );

    let foreign = send(
        &app,
        Request::get("/health")
            .header("origin", "https://evil.example")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert!(foreign.headers.get("access-control-allow-origin").is_none());
}

#[tokio::test]
async fn openapi_contract_keeps_run_start_body_optional() {
    let app = app();
    let spec = get(&app, "/openapi.json").await.json();
    let schema = &spec["components"]["schemas"]["RunStartRequest"];
    for field in ["include_roles", "auto_role_limit", "active_roles"] {
        assert!(schema["properties"].get(field).is_some(), "missing {field}");
    }
    let required = schema["required"].as_array().cloned().unwrap_or_default();
    assert!(!required.contains(&json!("active_roles")));

    let body = &spec["paths"]["/goals/{goal_id}/runs"]["post"]["requestBody"];
    assert_ne!(body["required"], true, "{body}");

    let docs = get(&app, "/docs").await;
    assert_eq!(docs.status, StatusCode::OK);
    assert!(docs.text.contains("swagger-ui"));
}

#[test]
fn frontend_agent_artwork_exists() {
    let agents = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../frontend/public/agents");
    for name in [
        "hive", "user", "planner", "research", "verifier", "executor", "critic",
    ] {
        let path = agents.join(format!("{name}.svg"));
        let content = std::fs::read_to_string(&path)
            .unwrap_or_else(|_| panic!("missing artwork asset: {}", path.display()));
        assert!(
            content.contains("<svg") && content.contains("</svg>"),
            "{name}.svg"
        );
    }
}
