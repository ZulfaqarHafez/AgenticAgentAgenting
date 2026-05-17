import json
import urllib.request

BASE = "http://127.0.0.1:8000"

# Browser-like CORS preflight
preflight = urllib.request.Request(
    BASE + "/goals",
    method="OPTIONS",
    headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
    },
)
with urllib.request.urlopen(preflight, timeout=20) as resp:
    preflight_status = resp.status
    preflight_allow_origin = resp.headers.get("Access-Control-Allow-Origin")

# Actual browser-origin POST
payload = {
    "title": "UI live request check",
    "success_criteria": ["request accepted"],
    "constraints": ["cors allowed"],
    "priority": "high",
}
post_req = urllib.request.Request(
    BASE + "/goals",
    data=json.dumps(payload).encode("utf-8"),
    method="POST",
    headers={
        "Content-Type": "application/json",
        "Origin": "http://localhost:3000",
    },
)
with urllib.request.urlopen(post_req, timeout=20) as resp:
    post_status = resp.status
    post_allow_origin = resp.headers.get("Access-Control-Allow-Origin")
    body = json.loads(resp.read().decode("utf-8"))

print(json.dumps({
    "preflight_status": preflight_status,
    "preflight_allow_origin": preflight_allow_origin,
    "post_status": post_status,
    "post_allow_origin": post_allow_origin,
    "goal_id": body.get("goal_id"),
}, indent=2))
