# 19. Real data check

What the real data sources actually return, how reliable they are, and what the first measurements say. Checked on 22 October 2026 by calling every source directly and analysing samples. The scripts and raw results are in [`data-check/`](data-check/).

**Summary:**
- Live and historical data for Singapore is good and free. **Rain gauges, temperature, humidity, wind, heat stress (WBGT), lightning strikes and NEA forecasts** all have working APIs, with history back to December 2016.
- **MSS daily climate files** give Changi records from 1991, enough for real climate normals.
- **Radar is only available as website images**, kept for about 30 days, with no official API.
- **Open-Meteo** gives 9+ forecast models, 4 ensembles and an archive of past forecasts, but its free quota is shared and ran out during this check.
- The data **contradicted several assumptions** in earlier chapters (section 19.6). That is exactly why this check was needed.

## 19.1 data.gov.sg real-time API (NEA)

Base: `https://api-open.data.gov.sg/v2/real-time/api/<endpoint>`. Response envelope: `{"code": 0, "data": {...}, "errorMsg": ""}`; `code: 17` with `REAL_TIME_API_DATA_NOT_FOUND` when no data exists for the requested time.

| Endpoint | Stations / areas | Cadence | Unit / format | Notes |
| --- | --- | --- | --- | --- |
| `rainfall` | 88 listed (55–60 reporting reliably in a month) | 5 min | mm per 5 min (`TB1 Rainfall 5 Minute Total F`) | Includes `S2xx` rain-only stations |
| `air-temperature` | 18 | 1 min | °C | |
| `relative-humidity` | 18 | 1 min | % | |
| `wind-speed` | 18 | 1 min | **knots** (10-min average) | Convert: × 0.5144 for m/s |
| `wind-direction` | 18 | 1 min | degrees (10-min average) | Direction wind blows *from* |
| `two-hr-forecast` | 47 areas | Every 30 min | Text category per area | 9 categories seen (19.4) |
| `twenty-four-hr-forecast` | 5 regions × 3 periods | ~3× daily | Category codes (e.g. `TL`, `CL`) + T/RH/wind ranges | |
| `four-day-outlook` | Island | Daily | Category + summary text + ranges | |
| `psi` | 5 regions | Hourly | 24-h PSI and pollutant sub-indices | |
| `pm25` | 5 regions | Hourly | µg/m³ | |
| `uv` | Island | Hourly | UV index | |
| `weather?api=wbgt` | **30 stations** | 15 min | WBGT °C **as text**, plus `heatStress` label (Low/Moderate/High) | Not at `/wbgt` (404) |
| `weather?api=lightning` | Strike list | 2-min records | Each strike: lat/lon (text), `type` `C` (cloud-to-cloud) or `G` (cloud-to-ground), ms timestamp | Not at `/lightning` (404) |

### History and paging

- **`date=YYYY-MM-DD`** returns that day; **`date=YYYY-MM-DDTHH:MM:SS`** returns the reading at that time (useful for sampling).
- Results are **paged 25 timestamps per request** (newest first) with a `paginationToken`. One full day of 5-minute rainfall = 288 timestamps = **12 requests**; one day of lightning = 720 records = 29 requests.
- **History starts in early December 2016** (2016-12-08 works; 2016-12-01 and earlier return "not found").
- Station lists change over time (55 rain stations in 2016, 90 in 2026). Always read the station list returned with each response.

### Reliability observed

| Check | Result |
| --- | --- |
| Requests made | 1,470 rainfall requests over 4 months of history, plus probes |
| Failures | 0 errors, 0 retries needed |
| Speed | ~0.4–0.7 s per request; one month of 5-min rainfall ≈ 6.5 minutes at 0.4 s spacing |
| Rate-limit headers | None returned. data.gov.sg says limits apply from end-2025 and a free API key raises them |
| **User-Agent** | **Python's default `Python-urllib` User-Agent is blocked with 403.** Any other User-Agent works. Always set one |
| Missing values | 0 nulls and 0 negative values in 507,267 rainfall values (Oct 2025) |
| Timestamps | Every day had all 288 five-minute timestamps |
| Station completeness | 55 of 60 stations ≥ 95% complete; 2 stations < 50% (in Oct 2025) |

## 19.2 MSS daily climate files (weather.gov.sg)

URL: `https://www.weather.gov.sg/files/dailydata/DAILYDATA_<station>_<YYYYMM>.csv`

Columns: `Station, Year, Month, Day, Daily Rainfall Total (mm), Highest 30 min Rainfall (mm), Highest 60 min Rainfall (mm), Highest 120 min Rainfall (mm), Mean Temperature (°C), Maximum Temperature (°C), Minimum Temperature (°C), Mean Wind Speed (km/h), Max Wind Speed (km/h)` (file starts with a UTF-8 byte-order mark; numbers are space-padded).

| Finding | Detail |
| --- | --- |
| Stations | 39 station IDs had files for Jan 2025 (`S06`–`S123`); rain-only `S2xx` stations have none |
| Depth | Changi (`S24`) from 1991 (and spot checks back to 1980); 12,903 days downloaded |
| Latency | Files appear about a month later (Sep 2026 available on 22 Oct; Oct 2026 not yet) |
| Short-duration rain | Highest 30/60/120-min columns are blank before about 2014 at Changi (8,315 days missing) |
| **Throttling** | Fast sequential downloads get **403 Forbidden**; the same files succeed on retry. 42 of 432 Changi months failed on the first pass, all but 5 recovered on a slower retry |
| **Station names change** | Changi appears as "Changi" in older files and "Changi Met. Station" in newer ones. **Key by station ID, never by name** |
| Gaps | Station-months can be missing (12 of 39 stations had no Sep 2026 file) |

## 19.3 Radar (weather.gov.sg images)

No official radar data API was found. The MSS website serves rain-area overlays as PNG images:

```
https://www.weather.gov.sg/files/rainarea/50km/v2/dpsri_70km_<YYYYMMDDHHMM>0000dBR.dpsri.png
https://www.weather.gov.sg/files/rainarea/240km/dpsri_240km_<YYYYMMDDHHMM>0000dBR.dpsri.png
```

| Property | Finding |
| --- | --- |
| Format | 480 × 480 RGBA PNG, transparent where there is no rain |
| Colours | Fixed palette (25–33 distinct colours seen), so intensity bands can be decoded by colour lookup |
| Cadence | Every 5 minutes (minute multiple of 5; other minutes return 404/403) |
| Retention | About **30 days** (22 Sep available on 22 Oct; 20 Sep and earlier 404) |
| Georeferencing | **Not published.** Image bounds must be worked out (for example by matching coastlines) and should be confirmed with MSS |
| Terms | Not stated for automated use. **Ask MSS for permission or an official feed before relying on this in a product** |

Implication: radar-based nowcasting is possible but rests on undocumented image URLs. Design the nowcast so it degrades gracefully to gauges + lightning + NEA 2-hour forecasts if radar disappears. Keep your own archive if you need more than 30 days of history (for training or verification).

## 19.4 NEA forecast vocabulary

Categories seen in 2-hour forecasts over three sample days (Dec 2024, Apr 2025, Oct 2025), most to least frequent:

`Cloudy`, `Partly Cloudy (Night)`, `Light Rain`, `Showers`, `Thundery Showers`, `Windy`, `Heavy Thundery Showers`, `Partly Cloudy (Day)`, `Moderate Rain`.

The 24-hour forecast and 4-day outlook use short codes (for example `TL` = Thundery Showers, `CL` = Cloudy). The full code list is larger than this sample; map unknown codes to "other" rather than failing.

These are **categorical, not probabilistic**. To use them as a forecast source, convert each category to an empirical rain probability by verifying it against gauges in the same area (chapter 12): for example, "how often did ≥ 0.2 mm fall in the next 2 hours at gauges in Bedok when NEA said `Showers`?"

## 19.5 Open-Meteo

| API | Status | Notes |
| --- | --- | --- |
| Forecast (`api.open-meteo.com/v1/forecast`) | Works | 9 models returned data for Singapore: ECMWF IFS, ECMWF AIFS, GFS, ICON, JMA, UKMO, CMA, GEM, Météo-France |
| Ensemble (`ensemble-api.open-meteo.com`) | Works | ECMWF IFS 51 members, ECMWF AIFS 51, GFS 31, ICON 40 |
| Historical forecasts (`historical-forecast-api.open-meteo.com`) | Works | Archived past forecasts: lets the scorecard backtest without waiting months |
| Previous runs, ERA5 archive | **429: daily limit exceeded** | The free tier's daily quota is shared by everyone behind the same IP; this sandbox's shared IP ran out |

Practical findings:
- **Model disagreement is large.** For the same 3 days at central Singapore, 3-day rain totals ranged from **0.7 mm (ICON) to 24.6 mm (ECMWF AIFS)**.
- **Grid points are not where you asked.** Several models' nearest grid point to central Singapore (1.35° N) was **1.5° N, about 17 km north, over Johor**. Always record and check the returned latitude/longitude; for coastal or small-island sites, consider averaging neighbouring points.
- **Not every model has every variable.** AIFS returned no CAPE or gusts; JMA no CAPE; none returned `lightning_potential` for this point.
- **Production needs a paid key or self-hosting.** Open-Meteo is open source and can be self-hosted; ECMWF open data can also be downloaded directly.

## 19.6 What the data says

### Changi climate normals (station S24, 1991–2020, 26 complete years)

| Month | Mean rain (mm) | Rain days ≥ 1 mm | P(rain day) | P(day ≥ 20 mm) | Mean max / min (°C) |
| --- | --- | --- | --- | --- | --- |
| Jan | 227 | 11.2 | 0.36 | 0.11 | 30.6 / 24.3 |
| Feb | 108 | 6.4 | 0.23 | 0.07 | 31.5 / 24.6 |
| Mar | 152 | 9.6 | 0.31 | 0.09 | 32.2 / 24.9 |
| Apr | 172 | 11.9 | 0.40 | 0.10 | 32.4 / 25.3 |
| May | 164 | 11.3 | 0.36 | 0.09 | 32.3 / 25.7 |
| Jun | 140 | 10.6 | 0.35 | 0.09 | 31.9 / 25.7 |
| Jul | 152 | 10.7 | 0.34 | 0.08 | 31.4 / 25.4 |
| Aug | 151 | 11.5 | 0.37 | 0.08 | 31.4 / 25.3 |
| Sep | 126 | 10.3 | 0.34 | 0.08 | 31.6 / 25.2 |
| Oct | 162 | 12.2 | 0.39 | 0.08 | 31.8 / 25.0 |
| Nov | 257 | 15.3 | 0.51 | 0.14 | 31.2 / 24.6 |
| Dec | 338 | 16.5 | 0.53 | 0.17 | 30.5 / 24.3 |
| **Year** | **2,149** (range 1,119–2,886) | **137** | | | |

(Years with any missing month are excluded. P(rain day) is the chance a given day has ≥ 1 mm.)

- This agrees with MSS's published long-term figure (≈ 2,166 mm for 1981–2017) and confirms Changi, in the east, is drier than the island average; western and central stations are wetter (see below).
- **Wettest day on record in the sample:** 216.2 mm on 30 Jan 2011.
- **Annual maximum 60-minute rainfall** (12 years with data): median 61 mm, highest 82 mm. A Gumbel fit gives return levels of about **60 mm (2-year), 77 mm (10-year) and 92 mm (50-year)** in one hour. These are rough given only 12 years.

### When does it rain? (5-minute gauges, 52–57 stations, one month per season)

Probability that a given gauge records ≥ 0.2 mm in a given hour, peak hour, and when the heavy hours (≥ 10 mm in an hour at a gauge) happen:

| Month (season) | Peak hour (SGT) | Peak P(rain at a gauge) | P(rain anywhere on the island) at peak | Where heavy hours fall |
| --- | --- | --- | --- | --- |
| Dec 2024 (NE monsoon) | 17:00 | 23% | 65% | 55% in 15–18h, 23% in 18–21h |
| Apr 2025 (inter-monsoon) | 18:00 | 27% | 50–67% | 87% between 12:00 and 21:00 |
| Jul 2025 (SW monsoon) | 11:00 | 12% | 32% | 59% between 06:00 and 12:00 |
| Oct 2025 (inter-monsoon) | 10–11:00 | 8% | 55% | Spread out: 21% 03–06h, 24% 21–24h, 17% 09–12h |

What this shows:
1. **Seasonal timing is real and strong.** December and April storms peak in the late afternoon; July rain peaks in the morning, matching Sumatra squall timing.
2. **October 2025 did not follow the "afternoon thunderstorm" pattern** that chapter 14 describes for the inter-monsoon. It had pre-dawn and late-night heavy rain instead. One month is not a climatology, but it shows the pattern varies year to year. **Baselines must be computed from several years per month, not assumed from the season name.**
3. **Point vs island probability differ hugely.** At the April peak a single gauge had a 27% chance of rain in that hour, but there was a 67% chance of rain *somewhere* on the island. A product must say which one it means (chapter 09).

### How local is the rain? (Oct 2025)

- Month totals across 55 stations ranged from **37 mm (Changi East Close) to 249 mm (Clementi Park)**, a 6.7× difference in one month on a 50 km-wide island.
- On 3 Oct 2025, one gauge recorded **68.8 mm in an hour** (Clementi Park, 08:00–09:00) and 92.8 mm in the day, while the island median was 5 mm and 29% of stations stayed dry.
- On 12 Oct 2025, the wettest station had 89 mm while **62% of stations had under 1 mm**.
- The highest 5-minute total was 12.8 mm (≈ 150 mm/h rate).

Conclusion: forecasts and verification must be **per area or per gauge**. "Will it rain in Singapore today?" is the wrong question for nearly every user.

### Lightning on a stormy morning (3 Oct 2025, ~3 h sampled)

- **13,383 strikes** detected in about three hours of sampled windows: **95% cloud-to-cloud, 5% cloud-to-ground** (662).
- 2,074 strikes within 15 km of central Singapore; coverage extends west over the Strait toward Sumatra, so approaching storms are visible before they arrive.
- Data volume is high on storm days; aggregate to counts per grid cell per 5 minutes for storage and alerting.

### How good are model forecasts at a point? (Changi, Sep 2026, 30 days)

Daily rain from Open-Meteo's archived forecasts versus the Changi gauge. September 2026 was unusually dry in rain days (5 days ≥ 1 mm, versus 10.3 normally) but still had 145 mm in total.

| Model | Mean error (mm/day) | MAE (mm/day) | Hits | False alarms | Misses | Frequency bias |
| --- | --- | --- | --- | --- | --- | --- |
| ECMWF AIFS | +0.2 | 5.7 | 4 | 16 | 1 | 4.0 |
| ECMWF IFS | +0.8 | 6.3 | 5 | 16 | 0 | 4.2 |
| GFS | −1.1 | 5.8 | 5 | 19 | 0 | 4.8 |
| ICON | −3.0 | 5.3 | 5 | 7 | 0 | 2.4 |
| JMA | +0.7 | 7.7 | 5 | 17 | 0 | 4.4 |
| UKMO | −2.6 | 4.9 | 4 | 5 | 1 | 1.8 |
| Climatology (monthly mean every day) | | 7.9 | | | | |
| Persistence (yesterday) | | 8.3 | | | | |

- Every model **forecast rain days far too often** (frequency bias 1.8–4.8): the "drizzle problem" from chapter 07, measured.
- Raw model amounts beat climatology and persistence on MAE (4.9–7.7 vs 7.9–8.3 mm).
- A naive multi-model probability (fraction of the six models with ≥ 1 mm) scored **worse than climatology**: Brier 0.33 vs 0.17 (skill −93%).
- **Caveat:** 30 days at one station is far too small to rank models; this is a demonstration of the pipeline, not a verdict. It does show why raw model rain must be **bias-corrected and calibrated** before being shown as a probability (chapter 08).

## 19.7 Corrections to earlier chapters

| Earlier statement | What the data shows | Updated in |
| --- | --- | --- |
| NEA has nine WBGT stations | The API returns **30** WBGT stations | 02, 15 |
| Annual rainfall "≈ 2,166 mm, verify 1991–2020" | Changi 1991–2020 mean **2,149 mm** (26 complete years); other stations are wetter | 14 |
| Inter-monsoon storms are afternoon (14:00–19:00) | True for Apr 2025; **Oct 2025 peaked pre-dawn and late night** | 14 |
| WBGT and lightning endpoints (verify) | `weather?api=wbgt`, `weather?api=lightning` | 16 |
| Radar availability unknown | Images only, 5-min, ~30-day retention, no georeference or stated terms | 16 |

## 19.8 Recommendations for the build

1. **Ingest from data.gov.sg** with a custom User-Agent, paging, retries and backoff; store raw responses and parse in a separate step. Get a free API key.
2. **Build baselines from at least 5 years** of 5-minute gauge history (2017 onwards is available), per station, month and hour. Budget about 6–7 minutes of downloading per station-network-month at polite speed, so 5 years ≈ 7 hours; run it once and keep the archive.
3. **Use MSS daily files** for long-term normals and extremes (Changi from 1991), downloaded slowly with retries.
4. **Treat radar as optional** until MSS confirms terms; start archiving images now if you plan to use them.
5. **Use Open-Meteo for prototyping** (forecasts, ensembles, archived forecasts), with a paid key or self-hosted instance for anything beyond that.
6. **Verify NEA's categorical forecasts** against gauges to turn them into probabilities; they are likely the strongest local short-range signal available.
7. **Calibrate before showing probabilities.** The September test shows raw multi-model rain probabilities are badly overconfident at a point.
8. **Forecast per area**, and always state whether a probability is for a point or for anywhere in an area.
