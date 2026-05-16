from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "hive-agent-backend"}


def test_bootstrap() -> None:
    client = TestClient(app)
    response = client.get("/bootstrap")
    assert response.status_code == 200
    assert response.json()["result"]["stage"] == "bootstrapped"
