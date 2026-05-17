from app.main import app


def test_run_start_contract_supports_recommended_roles() -> None:
    schema = app.openapi()["components"]["schemas"]["RunStartRequest"]
    properties = schema["properties"]

    assert "include_roles" in properties
    assert "auto_role_limit" in properties
    assert "active_roles" in properties
    assert "required" not in schema or "active_roles" not in schema["required"]


def test_run_start_request_body_can_be_omitted() -> None:
    request_body = app.openapi()["paths"]["/goals/{goal_id}/runs"]["post"]["requestBody"]
    assert request_body.get("required") is not True
