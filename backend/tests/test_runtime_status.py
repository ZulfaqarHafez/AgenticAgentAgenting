from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_runtime_status_fields() -> None:
    response = client.get("/runtime/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "hive-agent-backend"
    assert payload["api_version"] == "0.3.0"
    assert payload["contract_version"] == "run-start.v2"
    assert payload["recommended_roles_supported"] is True
    assert payload["decision_ledger_supported"] is True
    assert isinstance(payload["uptime_seconds"], (float, int))
    assert "store_backend" in payload
    assert "server_started_at" in payload
    assert "server_now" in payload
    assert "total_runs" in payload
    assert "active_runs" in payload


def test_runtime_status_counts_runs() -> None:
    goal = client.post(
        "/goals",
        json={
            "title": "Runtime count goal",
            "success_criteria": ["count run"],
            "constraints": [],
            "priority": "medium",
        },
    ).json()

    client.post(
        f"/goals/{goal['goal_id']}/runs",
        json={
            "active_roles": ["planner", "research", "verifier"],
            "min_usefulness": 0.35,
            "max_low_value_streak": 2,
            "enable_priority_preemption": True,
        },
    )

    runtime = client.get("/runtime/status").json()
    assert runtime["total_runs"] >= 1
    assert runtime["active_runs"] >= 1
