"""Builds docs/images/charts.html (three SVG charts) from analysis.json and diurnal.json.

Render to PNG with a headless browser, e.g. screenshot each <figure> element at 2x.
Usage: python3 charts.py docs/meteorology/data-check docs/images/charts.html
"""
import json, sys, pathlib, html

src = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2])
A = json.load(open(src / "analysis.json")); D = json.load(open(src / "diurnal.json"))

SURFACE, INK, INK2, GRID, SERIES, SERIES_SOFT = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1", "#2a78d6", "#cde2fb"
FONT = "-apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
esc = html.escape

def bar_path(x, y, w, h, r=4):
    """Bar with rounded top corners, square at the baseline."""
    r = min(r, w / 2, h)
    return (f"M{x:.1f},{y + h:.1f} L{x:.1f},{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} "
            f"L{x + w - r:.1f},{y:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} L{x + w:.1f},{y + h:.1f} Z")

def figure(fid, title, subtitle, svg, source, width):
    return (f'<figure id="{fid}" style="width:{width}px">'
            f'<figcaption><strong>{esc(title)}</strong><span>{esc(subtitle)}</span></figcaption>{svg}'
            f'<p class="src">{esc(source)}</p></figure>')

# ---------- 1. Changi monthly normals ----------
n = A["changi_normals_1991_2020"]; months = n["months"]
W, H, ml, mr, mt, mb = 860, 300, 48, 12, 16, 30
pw, ph = W - ml - mr, H - mt - mb
ymax = 350
y = lambda v: mt + ph * (1 - v / ymax)
step = pw / 12; bw = step - 10
parts = []
for t in range(0, ymax + 1, 50):
    parts.append(f'<line x1="{ml}" x2="{W - mr}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="{GRID}" stroke-width="1"/>')
    parts.append(f'<text x="{ml - 8}" y="{y(t) + 4:.1f}" text-anchor="end" class="tick">{t}</text>')
names = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
vals = [m["mean_total_mm"] for m in months]
hi, lo = vals.index(max(vals)), vals.index(min(vals))
for i, m in enumerate(months):
    x = ml + i * step + 5; v = m["mean_total_mm"]
    parts.append(f'<path d="{bar_path(x, y(v), bw, y(0) - y(v))}" fill="{SERIES}"><title>{names[i]}: {v:.0f} mm, {m["wet_days_ge_1mm"]} rain days</title></path>')
    parts.append(f'<text x="{x + bw / 2:.1f}" y="{H - 10}" text-anchor="middle" class="tick">{names[i]}</text>')
    if i in (hi, lo):
        parts.append(f'<text x="{x + bw / 2:.1f}" y="{y(v) - 6:.1f}" text-anchor="middle" class="lab">{v:.0f} mm</text>')
parts.append(f'<line x1="{ml}" x2="{W - mr}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="{INK2}" stroke-width="1"/>')
svg1 = f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Changi mean monthly rainfall">{"".join(parts)}</svg>'
fig1 = figure("normals", "Changi rainfall by month",
              f"Mean monthly total in mm, 1991–2020 ({n['full_years']} complete years). Annual mean {n['annual_mean_mm']:,.0f} mm, {n['wet_days_ge_1mm_per_year']:.0f} rain days.",
              svg1, "Source: MSS daily climate records, station S24 (Changi).", W)

# ---------- 2. Rain timing by season (small multiples, shared scale) ----------
PW, PH, pml, pmr, pmt, pmb = 410, 200, 40, 10, 10, 26
ymax2 = 0.30
panels = []
for label, d in D.items():
    hours = d["hours"]
    xs = lambda h: pml + (PW - pml - pmr) * h / 23
    ys = lambda v: pmt + (PH - pmt - pmb) * (1 - v / ymax2)
    p = []
    for t in (0, 0.1, 0.2, 0.3):
        p.append(f'<line x1="{pml}" x2="{PW - pmr}" y1="{ys(t):.1f}" y2="{ys(t):.1f}" stroke="{GRID}"/>')
        p.append(f'<text x="{pml - 6}" y="{ys(t) + 4:.1f}" text-anchor="end" class="tick">{int(t * 100)}%</text>')
    for h in (0, 6, 12, 18):
        p.append(f'<text x="{xs(h):.1f}" y="{PH - 8}" text-anchor="middle" class="tick">{h:02d}:00</text>')
    pts = " ".join(f"{xs(h['hour']):.1f},{ys(h['p_point']):.1f}" for h in hours)
    area = f"{xs(0):.1f},{ys(0):.1f} " + pts + f" {xs(23):.1f},{ys(0):.1f}"
    p.append(f'<polygon points="{area}" fill="{SERIES_SOFT}" opacity="0.6"/>')
    p.append(f'<polyline points="{pts}" fill="none" stroke="{SERIES}" stroke-width="2" stroke-linejoin="round"/>')
    pk = max(hours, key=lambda h: h["p_point"])
    p.append(f'<circle cx="{xs(pk["hour"]):.1f}" cy="{ys(pk["p_point"]):.1f}" r="4" fill="{SERIES}" stroke="{SURFACE}" stroke-width="2"/>')
    anchor = "end" if pk["hour"] > 16 else "start"; dx = -8 if anchor == "end" else 8
    p.append(f'<text x="{xs(pk["hour"]) + dx:.1f}" y="{ys(pk["p_point"]) + 4:.1f}" text-anchor="{anchor}" class="lab">peak {pk["hour"]:02d}:00, {pk["p_point"] * 100:.0f}%</text>')
    p.append(f'<line x1="{pml}" x2="{PW - pmr}" y1="{ys(0):.1f}" y2="{ys(0):.1f}" stroke="{INK2}"/>')
    panels.append(f'<div class="panel"><div class="ptitle">{esc(label)}</div><svg width="{PW}" height="{PH}" viewBox="0 0 {PW} {PH}" role="img" aria-label="{esc(label)}">{"".join(p)}</svg></div>')
svg2 = f'<div class="grid">{"".join(panels)}</div>'
fig2 = figure("timing", "When it rains in Singapore depends on the season",
              "Chance that a given rain gauge records at least 0.2 mm in each hour (SGT). One month per season, 52–57 gauges. Same scale in every panel.",
              svg2, "Source: NEA 5-minute rainfall via data.gov.sg. One month is a sample, not a climatology.", 860)

# ---------- 3. Forecast rain days vs observed ----------
v = A["verification_sep2026_changi"]
label_names = {"ecmwf_aifs025_single": "ECMWF AIFS", "ecmwf_ifs025": "ECMWF IFS", "gfs_seamless": "GFS",
               "icon_seamless": "ICON", "jma_seamless": "JMA", "ukmo_seamless": "UK Met Office"}
rows = sorted(((label_names[k], m["hits"] + m["false_alarms"]) for k, m in v.items() if not k.startswith("_")), key=lambda r: -r[1])
obs = v["_obs_wet_days"]; clim = A["changi_normals_1991_2020"]["months"][8]["wet_days_ge_1mm"]
W3, rowh, ml3, mr3, mt3 = 860, 34, 120, 70, 30
H3 = mt3 + rowh * len(rows) + 30
xmax = 30
x3 = lambda val: ml3 + (W3 - ml3 - mr3) * val / xmax
p = []; labels = []
for t in range(0, xmax + 1, 5):
    p.append(f'<line x1="{x3(t):.1f}" x2="{x3(t):.1f}" y1="{mt3 - 8}" y2="{H3 - 24}" stroke="{GRID}"/>')
    p.append(f'<text x="{x3(t):.1f}" y="{H3 - 8}" text-anchor="middle" class="tick">{t}</text>')
for i, (name, val) in enumerate(rows):
    yy = mt3 + i * rowh + 6; bh = rowh - 12
    p.append(f'<text x="{ml3 - 10}" y="{yy + bh / 2 + 4:.1f}" text-anchor="end" class="cat">{esc(name)}</text>')
    w = x3(val) - x3(0)
    p.append(f'<path d="M{x3(0):.1f},{yy:.1f} L{x3(0) + w - 4:.1f},{yy:.1f} Q{x3(0) + w:.1f},{yy:.1f} {x3(0) + w:.1f},{yy + 4:.1f} L{x3(0) + w:.1f},{yy + bh - 4:.1f} Q{x3(0) + w:.1f},{yy + bh:.1f} {x3(0) + w - 4:.1f},{yy + bh:.1f} L{x3(0):.1f},{yy + bh:.1f} Z" fill="{SERIES}"/>')
    txt = f"{val} days"; tw = len(txt) * 7.4 + 6
    labels.append(f'<rect x="{x3(val) + 3:.1f}" y="{yy + bh / 2 - 9:.1f}" width="{tw:.1f}" height="18" fill="{SURFACE}"/>')
    labels.append(f'<text x="{x3(val) + 6:.1f}" y="{yy + bh / 2 + 4:.1f}" class="lab">{txt}</text>')
for val, txt, dash in ((obs, f"Observed: {obs} days", ""), (clim, f"Normal: {clim:.0f} days", "4 3")):
    p.append(f'<line x1="{x3(val):.1f}" x2="{x3(val):.1f}" y1="{mt3 - 8}" y2="{H3 - 24}" stroke="{INK}" stroke-width="1.5" stroke-dasharray="{dash}"/>')
    p.append(f'<text x="{x3(val) + 4:.1f}" y="{mt3 - 12}" class="ref">{txt}</text>')
p.append(f'<line x1="{x3(0):.1f}" x2="{x3(0):.1f}" y1="{mt3 - 8}" y2="{H3 - 24}" stroke="{INK2}"/>')
p += labels
svg3 = f'<svg width="{W3}" height="{H3}" viewBox="0 0 {W3} {H3}" role="img" aria-label="Forecast rain days by model">{"".join(p)}</svg>'
fig3 = figure("verification", "Models forecast rain far more often than it fell",
              "Days with at least 1 mm forecast for Changi in September 2026, by model, against what was observed (5 days) and the long-term normal.",
              svg3, "Sources: Open-Meteo archived forecasts; MSS daily record. 30 days at one station: a demonstration, not a model ranking.", W3)

css = f"""
body {{ margin: 0; background: {SURFACE}; font-family: {FONT}; color: {INK}; padding: 24px; display: grid; gap: 40px; }}
figure {{ margin: 0; background: {SURFACE}; padding: 20px 20px 12px; }}
figcaption {{ display: grid; gap: 4px; margin-bottom: 14px; }}
figcaption strong {{ font-size: 18px; }}
figcaption span {{ font-size: 13px; color: {INK2}; max-width: 760px; line-height: 1.4; }}
.src {{ font-size: 11px; color: {INK2}; margin: 8px 0 0; }}
.tick {{ font-size: 11px; fill: {INK2}; font-variant-numeric: tabular-nums; }}
.lab {{ font-size: 12px; fill: {INK}; font-weight: 600; font-variant-numeric: tabular-nums; }}
.cat {{ font-size: 13px; fill: {INK}; }}
.ref {{ font-size: 12px; fill: {INK}; }}
.grid {{ display: grid; grid-template-columns: repeat(2, {PW}px); gap: 18px 20px; }}
.ptitle {{ font-size: 13px; font-weight: 600; margin: 0 0 4px 40px; }}
"""
out.write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{fig1}{fig2}{fig3}</body></html>", encoding="utf-8")
print("wrote", out)
