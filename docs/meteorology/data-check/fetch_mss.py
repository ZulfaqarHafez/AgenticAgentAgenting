"""Downloads MSS daily climate CSVs (one per station per month) from weather.gov.sg."""
import sys, time, urllib.request, urllib.error, pathlib

out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
stations = sys.argv[2].split(",")
y0, y1 = int(sys.argv[3]), int(sys.argv[4])
months = [int(m) for m in sys.argv[5].split(",")] if len(sys.argv) > 5 else list(range(1, 13))
got = missing = 0
for s in stations:
    for y in range(y0, y1 + 1):
        for m in months:
            f = out / f"{s}_{y}{m:02d}.csv"
            if f.exists():
                got += 1
                continue
            url = f"https://www.weather.gov.sg/files/dailydata/DAILYDATA_{s}_{y}{m:02d}.csv"
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "met-kb-data-check"}), timeout=30) as r:
                    body = r.read()
                if b"Station" in body[:40]:
                    f.write_bytes(body); got += 1
                else:
                    missing += 1
            except urllib.error.HTTPError:
                missing += 1
            time.sleep(0.25)
print(f"downloaded/available {got}, missing {missing}")
