from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_cors_preflight_for_goal_creation() -> None:
    response = client.options(
        "/goals",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_preflight_for_alternate_local_dev_port() -> None:
    response = client.options(
        "/goals",
        headers={
          "Origin": "http://127.0.0.1:3010",
          "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:3010"
