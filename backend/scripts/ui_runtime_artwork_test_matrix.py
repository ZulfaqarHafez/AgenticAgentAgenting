import json
import urllib.request
import urllib.error

BACKEND = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:3000"

results = []

def check(name, fn):
    try:
        fn()
        results.append((name, True, "ok"))
    except Exception as exc:
        results.append((name, False, str(exc)))


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, dict(resp.headers), json.loads(resp.read().decode("utf-8"))


def post_json(url, payload, headers=None):
    all_headers = {"Content-Type": "application/json"}
    if headers:
        all_headers.update(headers)
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=all_headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, dict(resp.headers), json.loads(body)

# Shared ids
goal_id = None
run_id = None

def t1_backend_health():
    status, _, body = get_json(BACKEND + "/health")
    assert status == 200
    assert body["status"] == "ok"

def t2_runtime_status_endpoint():
    status, _, body = get_json(BACKEND + "/runtime/status")
    assert status == 200
    assert "uptime_seconds" in body

def t3_runtime_status_fields():
    status, _, body = get_json(BACKEND + "/runtime/status")
    assert status == 200
    assert body["service"] == "hive-agent-backend"
    assert "store_backend" in body


def t4_cors_preflight_goals():
    req = urllib.request.Request(
        BACKEND + "/goals",
        method="OPTIONS",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        assert resp.status == 200
        assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"


def t5_post_goal_with_origin():
    global goal_id
    status, headers, body = post_json(
        BACKEND + "/goals",
        {
            "title": "Matrix goal",
            "success_criteria": ["run matrix"],
            "constraints": ["none"],
            "priority": "high",
        },
        headers={"Origin": "http://localhost:3000"},
    )
    assert status == 201
    allow_origin = headers.get("Access-Control-Allow-Origin") or headers.get(
        "access-control-allow-origin"
    )
    assert allow_origin == "http://localhost:3000"
    goal_id = body["goal_id"]


def t6_start_run():
    global run_id
    status, _, body = post_json(
        BACKEND + f"/goals/{goal_id}/runs",
        {
            "active_roles": ["planner", "research", "verifier"],
            "min_usefulness": 0.35,
            "max_low_value_streak": 2,
            "enable_priority_preemption": True,
        },
    )
    assert status == 201
    run_id = body["run_id"]


def t7_submit_turn():
    status, _, body = post_json(
        BACKEND + f"/runs/{run_id}/turns",
        {
            "role": "planner",
            "contribution": "Matrix contribution",
            "confidence": 0.8,
            "usefulness_score": 0.75,
            "evidence_refs": [],
            "pass_turn": False,
        },
    )
    assert status == 200
    assert body["turn_number"] >= 1


def t8_ledger_events():
    status, _, body = get_json(BACKEND + f"/runs/{run_id}/ledger")
    assert status == 200
    assert len(body) >= 2
    assert any(event["event_type"] == "role_activation" for event in body)


def t9_skill_recommendations_sorted():
    status, _, body = post_json(
        BACKEND + "/skills/recommendations",
        {
            "goal_title": "Research and verify architecture",
            "limit": 4,
        },
    )
    assert status == 200
    assert len(body) == 4
    scores = [item["activation_score"] for item in body]
    assert scores == sorted(scores, reverse=True)


def t10_frontend_runtime_visible():
    req = urllib.request.Request(FRONTEND, method="GET")
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8")
        assert resp.status == 200
        assert "Runtime" in html
        assert "Decision Ledger" in html


def t11_artwork_routes():
    for name in ["hive", "planner", "research", "verifier", "executor", "critic", "user"]:
        req = urllib.request.Request(FRONTEND + f"/agents/{name}.svg", method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            txt = resp.read().decode("utf-8")
            assert resp.status == 200
            assert "<svg" in txt

for test in [
    ("backend_health", t1_backend_health),
    ("runtime_status_endpoint", t2_runtime_status_endpoint),
    ("runtime_status_fields", t3_runtime_status_fields),
    ("cors_preflight_goals", t4_cors_preflight_goals),
    ("post_goal_with_origin", t5_post_goal_with_origin),
    ("start_run", t6_start_run),
    ("submit_turn", t7_submit_turn),
    ("ledger_events", t8_ledger_events),
    ("skill_recommendations_sorted", t9_skill_recommendations_sorted),
    ("frontend_runtime_visible", t10_frontend_runtime_visible),
    ("artwork_routes", t11_artwork_routes),
]:
    check(*test)

passed = sum(1 for _, ok, _ in results if ok)
failed = len(results) - passed
print(json.dumps({
    "passed": passed,
    "failed": failed,
    "results": [
        {"name": name, "ok": ok, "detail": detail} for name, ok, detail in results
    ],
}, indent=2))

if failed:
    raise SystemExit(1)
