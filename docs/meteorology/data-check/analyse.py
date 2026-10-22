"""Data-quality checks, baselines and a mini forecast verification from the downloaded samples."""
import json, csv, glob, math, statistics as st, pathlib, sys, collections, datetime as dt

S = pathlib.Path(sys.argv[1])
R = {}

# ---------- A. 5-minute rainfall, Oct 2025 ----------
days = sorted(glob.glob(str(S / "data/rain_oct2025/*.json")))
station_meta, per_day_ts, nulls, negatives, values = {}, [], 0, 0, 0
hourly = collections.defaultdict(float)          # (station, date, hour) -> mm
present = collections.Counter()                  # station -> number of 5-min readings
max5 = (0, None, None)
for f in days:
    d = json.load(open(f))
    for s in d["stations"]:
        station_meta[s["id"]] = s
    per_day_ts.append(len(d["readings"]))
    for r in d["readings"]:
        t = dt.datetime.fromisoformat(r["timestamp"])
        for x in r["data"]:
            v = x["value"]
            if v is None:
                nulls += 1; continue
            values += 1
            if v < 0:
                negatives += 1; continue
            present[x["stationId"]] += 1
            # 5-min total ending at t belongs to the hour of (t - 1 s)
            tb = t - dt.timedelta(seconds=1)
            hourly[(x["stationId"], tb.date().isoformat(), tb.hour)] += v
            if v > max5[0]:
                max5 = (v, x["stationId"], r["timestamp"])
expected = 288 * len(days)
cover = sorted(present.values())
R["five_min"] = {
    "days": len(days), "stations_seen": len(station_meta), "timestamps_per_day_min": min(per_day_ts), "timestamps_per_day_max": max(per_day_ts),
    "values": values, "nulls": nulls, "negatives": negatives,
    "stations_ge_95pct_complete": sum(1 for c in cover if c >= 0.95 * expected),
    "stations_lt_50pct_complete": sum(1 for c in cover if c < 0.5 * expected),
    "max_5min_mm": max5[0], "max_5min_station": station_meta.get(max5[1], {}).get("name"), "max_5min_time": max5[2],
}

# diurnal cycle: fraction of (station, day) pairs with >= 0.2 mm in each local hour, using stations >= 90% complete
good = {s for s, c in present.items() if c >= 0.9 * expected}
dates = [pathlib.Path(f).stem for f in days]
diurnal = []
for h in range(24):
    wet = heavy = n = 0; amounts = []
    for s in good:
        for d in dates:
            v = hourly.get((s, d, h), 0.0); n += 1
            if v >= 0.2: wet += 1; amounts.append(v)
            if v >= 10: heavy += 1
    diurnal.append({"hour": h, "p_wet_ge_0p2": round(wet / n, 4), "p_ge_10mm": round(heavy / n, 4),
                    "mean_wet_hour_mm": round(st.mean(amounts), 2) if amounts else 0})
R["diurnal_oct2025"] = {"stations_used": len(good), "hours": diurnal}

# point vs island-wide probability, per hour of day: P(rain at a given station) vs P(rain anywhere)
anywhere = []
for h in range(24):
    any_wet = sum(1 for d in dates if any(hourly.get((s, d, h), 0) >= 0.2 for s in good))
    anywhere.append(round(any_wet / len(dates), 3))
R["diurnal_oct2025"]["p_rain_anywhere"] = anywhere

# spatial variability: daily station totals
daily_tot = collections.defaultdict(float)
for (s, d, h), v in hourly.items():
    if s in good: daily_tot[(s, d)] += v
spatial = []
for d in dates:
    tots = [daily_tot.get((s, d), 0.0) for s in good]
    if max(tots) >= 10:
        spatial.append({"date": d, "max": round(max(tots), 1), "median": round(st.median(tots), 1),
                        "dry_stations_pct": round(100 * sum(1 for t in tots if t < 1) / len(tots))})
R["spatial_oct2025"] = spatial
# station month totals and wettest/driest
month_tot = {s: sum(daily_tot.get((s, d), 0) for d in dates) for s in good}
ranked = sorted(month_tot.items(), key=lambda kv: kv[1])
R["station_month_totals"] = {"n": len(ranked), "min": [station_meta[ranked[0][0]]["name"], round(ranked[0][1], 1)],
                             "max": [station_meta[ranked[-1][0]]["name"], round(ranked[-1][1], 1)],
                             "median": round(st.median(v for _, v in ranked), 1)}
# hourly max intensity
mx = max(((v, k) for k, v in hourly.items()), default=(0, None))
R["max_hourly_mm"] = {"mm": round(mx[0], 1), "station": station_meta[mx[1][0]]["name"], "date": mx[1][1], "hour": mx[1][2]}

# ---------- B. MSS daily records ----------
def read_mss(files):
    rows = []
    for f in files:
        with open(f, encoding="utf-8-sig", errors="replace") as fh:
            rd = csv.reader(fh); hdr = next(rd)
            for row in rd:
                if len(row) < 8: continue
                def num(x):
                    x = x.strip()
                    try: return float(x)
                    except ValueError: return None
                rows.append({"station": pathlib.Path(f).name.split("_")[0], "name": row[0].strip(), "date": dt.date(int(row[1]), int(row[2]), int(row[3])),
                             "rain": num(row[4]), "r30": num(row[5]), "r60": num(row[6]), "r120": num(row[7]),
                             "tmean": num(row[8]) if len(row) > 8 else None, "tmax": num(row[9]) if len(row) > 9 else None,
                             "tmin": num(row[10]) if len(row) > 10 else None})
    return rows, hdr

changi, hdr = read_mss(sorted(glob.glob(str(S / "data/mss_changi/*.csv"))))
R["mss_header"] = hdr
years = sorted({r["date"].year for r in changi})
R["changi_coverage"] = {"first": str(min(r["date"] for r in changi)), "last": str(max(r["date"] for r in changi)),
                        "days": len(changi), "rain_missing_days": sum(1 for r in changi if r["rain"] is None),
                        "r60_missing_days": sum(1 for r in changi if r["r60"] is None),
                        "tmax_missing_days": sum(1 for r in changi if r["tmax"] is None)}
norm = [r for r in changi if 1991 <= r["date"].year <= 2020 and r["rain"] is not None]
full_years = [y for y in range(1991, 2021) if sum(1 for r in norm if r["date"].year == y) >= 360]
annual = [sum(r["rain"] for r in norm if r["date"].year == y) for y in full_years]
monthly = []
for m in range(1, 13):
    rows = [r for r in norm if r["date"].month == m and r["date"].year in full_years]
    yrs = sorted({r["date"].year for r in rows})
    tot = [sum(r["rain"] for r in rows if r["date"].year == y) for y in yrs]
    tmax = [r["tmax"] for r in changi if r["date"].month == m and 1991 <= r["date"].year <= 2020 and r["tmax"] is not None]
    tmin = [r["tmin"] for r in changi if r["date"].month == m and 1991 <= r["date"].year <= 2020 and r["tmin"] is not None]
    monthly.append({"month": m, "mean_total_mm": round(st.mean(tot), 1), "wet_days_ge_1mm": round(sum(1 for r in rows if r["rain"] >= 1) / len(yrs), 1),
                    "p_wet_day_ge_1mm": round(sum(1 for r in rows if r["rain"] >= 1) / len(rows), 3),
                    "p_day_ge_20mm": round(sum(1 for r in rows if r["rain"] >= 20) / len(rows), 3),
                    "mean_tmax": round(st.mean(tmax), 1) if tmax else None, "mean_tmin": round(st.mean(tmin), 1) if tmin else None})
R["changi_normals_1991_2020"] = {"full_years": len(full_years), "annual_mean_mm": round(st.mean(annual), 0),
                                 "annual_min_mm": round(min(annual)), "annual_max_mm": round(max(annual)),
                                 "wet_days_ge_1mm_per_year": round(sum(1 for r in norm if r["date"].year in full_years and r["rain"] >= 1) / len(full_years), 0),
                                 "months": monthly}
# extremes: annual max 60-min rainfall (all years with r60 data) and Gumbel fit (method of moments)
amax = {}
for r in changi:
    if r["r60"] is not None:
        amax[r["date"].year] = max(amax.get(r["date"].year, 0), r["r60"])
am = [v for y, v in sorted(amax.items()) if y <= 2025]
if len(am) >= 10:
    mu_hat = st.mean(am); s_hat = st.stdev(am)
    beta = s_hat * math.sqrt(6) / math.pi; mu = mu_hat - 0.5772 * beta
    rl = {T: round(mu - beta * math.log(-math.log(1 - 1 / T)), 1) for T in (2, 10, 50)}
    R["changi_annual_max_60min"] = {"years": len(am), "min": min(am), "median": st.median(am), "max": max(am), "gumbel_return_levels_mm": rl}
dmax = max((r for r in changi if r["rain"] is not None), key=lambda r: r["rain"])
R["changi_wettest_day"] = {"date": str(dmax["date"]), "mm": dmax["rain"]}

# ---------- C. September 2026: island spread + forecast verification at Changi ----------
sep, _ = read_mss(sorted(glob.glob(str(S / "data/mss_sep2026/*.csv"))))
by_day = collections.defaultdict(list)
for r in sep:
    if r["rain"] is not None: by_day[r["date"]].append(r["rain"])
R["sep2026_stations"] = len({r["station"] for r in sep})
obs = {r["date"].isoformat(): r["rain"] for r in sep if r["station"] == "S24" and r["rain"] is not None}
fc = json.load(open(S / "data/raw/om/hist_fc.json"))["daily"]
models = sorted({k.replace("precipitation_sum_", "") for k in fc if k.startswith("precipitation_sum_")})
clim_p = monthly[8]["p_wet_day_ge_1mm"]  # September climatological wet-day probability
ver = {}
dates_fc = fc["time"]
for m in models:
    pairs = [(fc["precipitation_sum_" + m][i], obs[d]) for i, d in enumerate(dates_fc) if d in obs and fc["precipitation_sum_" + m][i] is not None]
    if not pairs: continue
    a = sum(1 for f, o in pairs if f >= 1 and o >= 1); b = sum(1 for f, o in pairs if f >= 1 and o < 1)
    c = sum(1 for f, o in pairs if f < 1 and o >= 1); d_ = sum(1 for f, o in pairs if f < 1 and o < 1)
    ver[m] = {"n": len(pairs), "ME_mm": round(st.mean(f - o for f, o in pairs), 2), "MAE_mm": round(st.mean(abs(f - o) for f, o in pairs), 2),
              "hits": a, "false_alarms": b, "misses": c, "correct_neg": d_,
              "POD": round(a / (a + c), 2) if a + c else None, "FAR": round(b / (a + b), 2) if a + b else None,
              "freq_bias": round((a + b) / (a + c), 2) if a + c else None}
o_sorted = [obs[d] for d in dates_fc if d in obs]
ver["_climatology_MAE_mm"] = round(st.mean(abs(st.mean(o_sorted) - o) for o in o_sorted), 2)
ver["_persistence_MAE_mm"] = round(st.mean(abs(o_sorted[i - 1] - o_sorted[i]) for i in range(1, len(o_sorted))), 2)
ver["_obs_wet_days"] = sum(1 for o in o_sorted if o >= 1)
ver["_obs_total_mm"] = round(sum(o_sorted), 1)
ver["_clim_wet_day_prob_sep"] = clim_p
# Brier score of an equal-weight "ensemble of models" probability vs climatology probability
bs_ens, bs_clim = [], []
for i, d in enumerate(dates_fc):
    if d not in obs: continue
    vals = [fc["precipitation_sum_" + m][i] for m in models if fc["precipitation_sum_" + m][i] is not None]
    p = sum(1 for v in vals if v >= 1) / len(vals); o = 1 if obs[d] >= 1 else 0
    bs_ens.append((p - o) ** 2); bs_clim.append((clim_p - o) ** 2)
ver["_multimodel_brier"] = round(st.mean(bs_ens), 3); ver["_climatology_brier"] = round(st.mean(bs_clim), 3)
ver["_multimodel_BSS"] = round(1 - st.mean(bs_ens) / st.mean(bs_clim), 3)
R["verification_sep2026_changi"] = ver

print(json.dumps(R, indent=1, default=str))
