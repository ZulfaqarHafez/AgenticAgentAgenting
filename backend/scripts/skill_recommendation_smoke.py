import json
import urllib.request

BASE = "http://127.0.0.1:8000"

payload = {
  "goal_title": "Research and verify multi-agent architecture",
  "success_criteria": ["collect evidence", "validate safety"],
  "constraints": ["low latency"],
  "limit": 5
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
  BASE + "/skills/recommendations",
  data=data,
  headers={"Content-Type": "application/json"},
  method="POST"
)
with urllib.request.urlopen(req, timeout=20) as resp:
  recommendations = json.loads(resp.read().decode("utf-8"))
print(json.dumps(recommendations, indent=2))
