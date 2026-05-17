import json
import urllib.request

BASE = "http://127.0.0.1:8000"

def post(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

goal = post("/goals", {
    "title": "Decision ledger smoke",
    "success_criteria": ["activation reasons", "fallback transitions"],
    "constraints": ["runtime test"],
    "priority": "high"
})
run = post(f"/goals/{goal['goal_id']}/runs", {
    "active_roles": ["planner", "research", "verifier"],
    "min_usefulness": 0.35,
    "max_low_value_streak": 2,
    "enable_priority_preemption": True
})

# Trigger verifier priority preemption while planner is current.
post(f"/runs/{run['run_id']}/turns", {
    "role": "verifier",
    "contribution": "Critical contradiction detected",
    "confidence": 0.97,
    "usefulness_score": 0.92,
    "evidence_refs": ["https://example.org/critical"],
    "pass_turn": False,
    "priority_override": True
})

ledger = get(f"/runs/{run['run_id']}/ledger")
transitions = [e for e in ledger if e["event_type"] == "fallback_transition"]
activations = [e for e in ledger if e["event_type"] == "role_activation"]

print(json.dumps({
    "run_id": run["run_id"],
    "ledger_events": len(ledger),
    "activation_sample": activations[0]["reason"] if activations else None,
    "fallback_transition_count": len(transitions),
    "fallback_transition_to": transitions[0]["fallback_to"] if transitions else None
}, indent=2))
