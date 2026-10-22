# Data check scripts

Scripts and results behind [chapter 19](../19-real-data-check.md). Run from any folder; pass the working directory as the first argument.

| Script | What it does |
| --- | --- |
| `fetch_rain_month.py OUT START_DATE DAYS` | Downloads every 5-minute rainfall reading for a run of days from data.gov.sg (paged, with retries) |
| `fetch_mss.py OUT STATIONS Y0 Y1 [MONTHS]` | Downloads MSS daily climate CSVs per station and month from weather.gov.sg (slowly, to avoid 403 throttling) |
| `analyse.py WORKDIR` | Data quality, October 2025 rain timing and locality, Changi normals and extremes, September 2026 forecast verification |
| `diurnal.py WORKDIR` | Hour-of-day rain statistics per sampled month |
| `charts.py DATA_CHECK_DIR OUT_HTML` | Draws the README charts (SVG in an HTML page) from `analysis.json` and `diurnal.json`; screenshot each `<figure>` to get the PNGs in `docs/images/` |

`analyse.py` and `diurnal.py` expect this layout under `WORKDIR/data/`: `rain_<mon><year>/` (from `fetch_rain_month.py`), `mss_changi/` and `mss_sep2026/` (from `fetch_mss.py`), and `raw/om/hist_fc.json` (Open-Meteo historical forecasts for Changi, September 2026).

`analysis.json` and `diurnal.json` are the outputs used in chapter 19. Raw downloads are not committed (about 120 MB).
