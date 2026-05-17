import json
import urllib.request

BASE = "http://127.0.0.1:8000"

def post(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

goal = post("/goals", {
    "title": "Smoke test goal",
    "success_criteria": ["Create run", "Rotate turns", "Generate report"],
    "constraints": ["Quick validation"],
    "priority": "high"
})

goal_id = goal["goal_id"]
run = post(f"/goals/{goal_id}/runs", {
    "active_roles": ["planner", "research", "verifier"],
    "min_usefulness": 0.35,
    "max_low_value_streak": 2,
    "enable_priority_preemption": True
})
run_id = run["run_id"]

turn1 = post(f"/runs/{run_id}/turns", {
    "role": "planner",
    "contribution": "Planner proposes decomposition",
    "confidence": 0.84,
    "evidence_refs": ["https://example.org/p1"],
    "usefulness_score": 0.80,
    "pass_turn": False,
    "priority_override": False
})

turn2 = post(f"/runs/{run_id}/turns", {
    "role": "research",
    "contribution": "Research adds evidence",
    "confidence": 0.86,
    "evidence_refs": ["https://example.org/r1"],
    "usefulness_score": 0.82,
    "pass_turn": False,
    "priority_override": False
})

turn3 = post(f"/runs/{run_id}/turns", {
    "role": "verifier",
    "contribution": "Verifier validates assumptions",
    "confidence": 0.90,
    "evidence_refs": ["https://example.org/v1"],
    "usefulness_score": 0.88,
    "pass_turn": False,
    "priority_override": False
})

report = get(f"/runs/{run_id}/report")

print(json.dumps({
    "goal_id": goal_id,
    "run_id": run_id,
    "current_role_after_3_turns": turn3["current_role"],
    "turn_count": report["turns"],
    "rounds": report["rounds"],
    "fallback_layer": report["fallback_layer"],
    "role_turn_counts": report["role_turn_counts"]
}, indent=2))
