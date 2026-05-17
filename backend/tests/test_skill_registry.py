from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_skill_recommendations_returns_ranked_roles() -> None:
    response = client.post(
        "/skills/recommendations",
        json={
            "goal_title": "Research and benchmark agent frameworks with verification",
            "success_criteria": ["Collect evidence", "Validate claims"],
            "constraints": ["Keep risk low"],
            "limit": 3,
        },
    )
    assert response.status_code == 200
    recs = response.json()
    assert len(recs) == 3
    assert recs[0]["activation_score"] >= recs[1]["activation_score"]
    assert recs[1]["activation_score"] >= recs[2]["activation_score"]


def test_skill_recommendations_honors_include_roles() -> None:
    response = client.post(
        "/skills/recommendations",
        json={
            "goal_title": "Plan delivery milestones",
            "include_roles": ["planner", "verifier"],
            "limit": 2,
        },
    )
    assert response.status_code == 200
    recs = response.json()
    roles = [item["role"] for item in recs]
    assert set(roles).issubset({"planner", "verifier"})
