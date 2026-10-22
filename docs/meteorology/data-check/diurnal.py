"""Hour-of-day rain statistics per sampled month, from 5-minute station data."""
import json, glob, pathlib, sys, collections, datetime as dt

S = pathlib.Path(sys.argv[1])
out = {}
for folder, label in [("rain_dec2024", "Dec 2024 (NE monsoon)"), ("rain_apr2025", "Apr 2025 (inter-monsoon)"),
                      ("rain_jul2025", "Jul 2025 (SW monsoon)"), ("rain_oct2025", "Oct 2025 (inter-monsoon)")]:
    files = sorted(glob.glob(str(S / "data" / folder / "*.json")))
    if not files:
        continue
    hourly = collections.defaultdict(float); present = collections.Counter(); names = {}
    dates = []
    for f in files:
        d = json.load(open(f)); dates.append(d["date"])
        for s in d["stations"]:
            names[s["id"]] = s["name"]
        for r in d["readings"]:
            t = dt.datetime.fromisoformat(r["timestamp"]) - dt.timedelta(seconds=1)
            for x in r["data"]:
                if x["value"] is None or x["value"] < 0:
                    continue
                present[x["stationId"]] += 1
                hourly[(x["stationId"], t.date().isoformat(), t.hour)] += x["value"]
    good = [s for s, c in present.items() if c >= 0.9 * 288 * len(files)]
    hours = []
    for h in range(24):
        n = wet = heavy = 0
        for s in good:
            for d in dates:
                v = hourly.get((s, d, h), 0.0); n += 1
                wet += v >= 0.2; heavy += v >= 10
        anywhere = sum(1 for d in dates if any(hourly.get((s, d, h), 0) >= 0.2 for s in good)) / len(dates)
        hours.append({"hour": h, "p_point": round(wet / n, 4), "p_point_ge10": round(heavy / n, 4), "p_anywhere": round(anywhere, 3)})
    # station-level share of all heavy hours (>=10 mm) by 3-hour block
    blocks = collections.Counter()
    for (s, d, h), v in hourly.items():
        if s in good and v >= 10:
            blocks[f"{h // 3 * 3:02d}-{h // 3 * 3 + 3:02d}"] += 1
    total_heavy = sum(blocks.values())
    peak = max(hours, key=lambda x: x["p_point"])
    out[label] = {"days": len(files), "stations": len(good), "hours": hours,
                  "peak_hour": peak["hour"], "peak_p_point": peak["p_point"],
                  "heavy_hour_share_by_block": {k: round(v / total_heavy, 3) for k, v in sorted(blocks.items())} if total_heavy else {},
                  "heavy_hours_total": total_heavy}
print(json.dumps(out, indent=1))
