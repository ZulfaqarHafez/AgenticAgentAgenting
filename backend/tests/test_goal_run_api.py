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

    ledger_response = client.get(f"/runs/{run_id}/ledger")
    assert ledger_response.status_code == 200
    ledger = ledger_response.json()
    assert len(ledger) >= 4
    event_types = [event["event_type"] for event in ledger]
    assert "role_activation" in event_types
    assert "confidence_shift" in event_types
