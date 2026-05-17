from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_goal_lifecycle_and_run_report() -> None:
    goal_payload = {
        "title": "Plan adaptable hive",
        "success_criteria": ["Define architecture", "Define fallback"],
        "constraints": ["Latency under 15s"],
        "priority": "high",
    }
    goal_response = client.post("/goals", json=goal_payload)
    assert goal_response.status_code == 201
    goal = goal_response.json()
    goal_id = goal["goal_id"]

    run_response = client.post(
        f"/goals/{goal_id}/runs",
        json={
            "active_roles": ["planner", "research", "verifier"],
            "min_usefulness": 0.35,
            "max_low_value_streak": 2,
            "enable_priority_preemption": True,
        },
    )
    assert run_response.status_code == 201
    run = run_response.json()
    run_id = run["run_id"]
    assert run["current_role"] == "planner"

    turn_1 = client.post(
        f"/runs/{run_id}/turns",
        json={
            "role": "planner",
            "contribution": "Initial decomposition",
            "confidence": 0.8,
            "evidence_refs": [],
            "usefulness_score": 0.8,
            "pass_turn": False,
            "priority_override": False,
        },
    )
    assert turn_1.status_code == 200
    assert turn_1.json()["current_role"] == "research"

    turn_2 = client.post(
        f"/runs/{run_id}/turns",
        json={
            "role": "research",
            "contribution": "Found source-backed patterns",
            "confidence": 0.9,
            "evidence_refs": ["https://example.com/a"],
            "usefulness_score": 0.85,
            "pass_turn": False,
            "priority_override": False,
        },
    )
    assert turn_2.status_code == 200
    assert turn_2.json()["current_role"] == "verifier"

    report_response = client.get(f"/runs/{run_id}/report")
    assert report_response.status_code == 200
    report = report_response.json()
    assert report["turns"] == 2
    assert report["role_turn_counts"]["planner"] == 1
    assert report["role_turn_counts"]["research"] == 1
    assert report["fallback_layer"] == "layer_1_circle_junction"
    assert report["proof_gate_status"]["state"] == "blocked"

    ledger_response = client.get(f"/runs/{run_id}/ledger")
    assert ledger_response.status_code == 200
    ledger = ledger_response.json()
    assert len(ledger) >= 4
    event_types = [event["event_type"] for event in ledger]
    assert "role_activation" in event_types
    assert "confidence_shift" in event_types


def test_start_run_auto_recommended_roles() -> None:
    goal_response = client.post(
        "/goals",
        json={
            "title": "Auto role goal",
            "success_criteria": ["Use recommendations"],
            "constraints": ["Verify role selection"],
            "priority": "high",
        },
    )
    assert goal_response.status_code == 201
    goal_id = goal_response.json()["goal_id"]

    run_response = client.post(
        f"/goals/{goal_id}/runs",
        json={
            "include_roles": ["planner", "research", "verifier"],
            "auto_role_limit": 3,
            "min_usefulness": 0.35,
            "max_low_value_streak": 2,
            "enable_priority_preemption": True,
        },
    )
    assert run_response.status_code == 201
    run = run_response.json()
    assert run["activation_strategy"] == "recommended_roles"
    assert len(run["active_roles"]) == 3
    assert len(run["activation_recommendations"]) == 3


def test_start_run_with_empty_body_uses_recommended_roles() -> None:
    goal_response = client.post(
        "/goals",
        json={
            "title": "Body omitted goal",
            "success_criteria": ["Allow body omission"],
            "constraints": ["Use default role recommendation"],
            "priority": "medium",
        },
    )
    assert goal_response.status_code == 201
    goal_id = goal_response.json()["goal_id"]

    run_response = client.post(f"/goals/{goal_id}/runs")
    assert run_response.status_code == 201
    run = run_response.json()
    assert run["activation_strategy"] == "recommended_roles"
    assert len(run["active_roles"]) >= 1


def test_start_run_power_mode_expands_role_depth() -> None:
    goal_response = client.post(
        "/goals",
        json={
            "title": "Power mode goal",
            "success_criteria": ["Activate broader specialist depth"],
            "constraints": [],
            "priority": "high",
        },
    )
    assert goal_response.status_code == 201
    goal_id = goal_response.json()["goal_id"]

    run_response = client.post(
        f"/goals/{goal_id}/runs",
        json={
            "run_mode": "power",
        },
    )
    assert run_response.status_code == 201
    run = run_response.json()
    assert run["run_mode"] == "power"
    assert len(run["active_roles"]) == 5


def test_start_run_lite_mode_limits_auto_role_depth() -> None:
    goal_response = client.post(
        "/goals",
        json={
            "title": "Lite mode goal",
            "success_criteria": ["Stay lightweight"],
            "constraints": [],
            "priority": "medium",
        },
    )
    assert goal_response.status_code == 201
    goal_id = goal_response.json()["goal_id"]

    run_response = client.post(
        f"/goals/{goal_id}/runs",
        json={
            "run_mode": "lite",
        },
    )
    assert run_response.status_code == 201
    run = run_response.json()
    assert run["run_mode"] == "lite"
    assert len(run["active_roles"]) == 2


def test_auto_turn_generates_specialist_output_and_persists_history() -> None:
    goal_response = client.post(
        "/goals",
        json={
            "title": "Auto turn generation",
            "success_criteria": ["Generate differentiated specialist output"],
            "constraints": ["Keep baton visible"],
            "priority": "high",
        },
    )
    assert goal_response.status_code == 201
    goal_id = goal_response.json()["goal_id"]

    run_response = client.post(
        f"/goals/{goal_id}/runs",
        json={"run_mode": "balanced"},
    )
    assert run_response.status_code == 201
    run_id = run_response.json()["run_id"]

    auto_turn_response = client.post(
        f"/runs/{run_id}/auto-turn",
        json={"user_prompt": "Map the baton and the fallback path."},
    )
    assert auto_turn_response.status_code == 200
    updated_run = auto_turn_response.json()
    latest_turn = updated_run["turn_history"][-1]
    assert latest_turn["user_prompt"] == "Map the baton and the fallback path."
    assert latest_turn["specialist_output"]["provider"] == "prompted_local_engine"
    assert latest_turn["specialist_output"]["prompt_title"]
    assert any(
        marker in latest_turn["contribution"]
        for marker in [
            "Mission frame",
            "Signals",
            "Proof check",
            "Implementation move",
            "Contrarian read",
        ]
    )


def test_proof_gate_blocks_then_allows_completion() -> None:
    goal_response = client.post(
        "/goals",
        json={
            "title": "Proof gate completion",
            "success_criteria": ["Require verifier before completion"],
            "constraints": ["Need evidence"],
            "priority": "high",
        },
    )
    assert goal_response.status_code == 201
    goal_id = goal_response.json()["goal_id"]

    run_response = client.post(
        f"/goals/{goal_id}/runs",
        json={"run_mode": "balanced"},
    )
    assert run_response.status_code == 201
    run_id = run_response.json()["run_id"]

    blocked_completion = client.post(f"/runs/{run_id}/complete")
    assert blocked_completion.status_code == 409
    assert "proof gate blocked completion" in blocked_completion.text

    for prompt in [
        "Plan the system.",
        "Research supporting evidence.",
        "Verify release readiness.",
    ]:
        auto_turn_response = client.post(
            f"/runs/{run_id}/auto-turn",
            json={"user_prompt": prompt},
        )
        assert auto_turn_response.status_code == 200

    proof_gate_response = client.get(f"/runs/{run_id}/proof-gate")
    assert proof_gate_response.status_code == 200
    proof_gate = proof_gate_response.json()
    assert proof_gate["ready_to_complete"] is True
    assert proof_gate["verifier_turn_observed"] is True

    completed_response = client.post(f"/runs/{run_id}/complete")
    assert completed_response.status_code == 200
    assert completed_response.json()["status"] == "completed"


def test_goal_run_history_lists_persisted_runs() -> None:
    goal_response = client.post(
        "/goals",
        json={
            "title": "Run history goal",
            "success_criteria": ["Persist two runs"],
            "constraints": [],
            "priority": "medium",
        },
    )
    assert goal_response.status_code == 201
    goal_id = goal_response.json()["goal_id"]

    first_run = client.post(f"/goals/{goal_id}/runs", json={"run_mode": "lite"})
    second_run = client.post(f"/goals/{goal_id}/runs", json={"run_mode": "balanced"})
    assert first_run.status_code == 201
    assert second_run.status_code == 201

    history_response = client.get(f"/goals/{goal_id}/runs")
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) >= 2
    assert all(item["goal_id"] == goal_id for item in history)
