"""Downloads every 5-minute rainfall reading for a range of days from data.gov.sg (v2 real-time API, paginated)."""
import json, sys, time, urllib.request, urllib.error, pathlib, datetime as dt

out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
start = dt.date.fromisoformat(sys.argv[2]); days = int(sys.argv[3])
BASE = "https://api-open.data.gov.sg/v2/real-time/api/rainfall"
stats = {"requests": 0, "retries": 0, "status": {}}

def get(url):
    for attempt in range(6):
        stats["requests"] += 1
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "met-kb-data-check"}), timeout=40) as r:
                stats["status"][r.status] = stats["status"].get(r.status, 0) + 1
                return json.load(r)
        except urllib.error.HTTPError as e:
            stats["status"][e.code] = stats["status"].get(e.code, 0) + 1
            stats["retries"] += 1
            time.sleep(min(60, 2 ** attempt * 2))
        except Exception:
            stats["retries"] += 1
            time.sleep(min(60, 2 ** attempt * 2))
    raise RuntimeError("gave up on " + url)

t0 = time.time()
for i in range(days):
    day = (start + dt.timedelta(days=i)).isoformat()
    f = out / f"{day}.json"
    if f.exists():
        continue
    readings, stations, token = [], {}, None
    while True:
        url = f"{BASE}?date={day}" + (f"&paginationToken={token}" if token else "")
        d = get(url)["data"]
        readings += d["readings"]
        for s in d["stations"]:
            stations[s["id"]] = s
        token = d.get("paginationToken")
        time.sleep(0.4)
        if not token:
            break
    f.write_text(json.dumps({"date": day, "stations": list(stations.values()), "readings": readings}))
    print(day, len(readings), "timestamps", len(stations), "stations", flush=True)
print("done", json.dumps(stats), f"{time.time() - t0:.0f}s", flush=True)
