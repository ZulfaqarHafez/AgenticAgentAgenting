# 16. Data sources

Where agents get observations, forecasts and reference data. Endpoints, limits and formats change; **verify** before building on any of them, and respect each provider's terms and rate limits.

## 16.1 Singapore (data.gov.sg / NEA)

NEA publishes real-time weather and environmental data through data.gov.sg. The v2 real-time API family is served from `api-open.data.gov.sg/v2/real-time/api/...`; dataset metadata is under `api-production.data.gov.sg/v2/public/api/...`. A free API key from the data.gov.sg developer portal gives higher rate limits (rate limits enforced from end of 2025).

| Dataset | Content | Cadence | Notes |
| --- | --- | --- | --- |
| Rainfall | Per-station rainfall | 5 min | Dense gauge network; values are 5-min totals |
| Air temperature | Per-station | 1 min | |
| Relative humidity | Per-station | 1 min | |
| Wind speed and direction | Per-station | 1 min | |
| 2-hour weather forecast | Text forecast per area (≈ 47 areas) | Every 30 min | NEA nowcast; categorical ("Thundery Showers", "Cloudy") |
| 24-hour forecast | Regional forecasts (north, south, east, west, central) | Several times daily | |
| 4-day outlook | Daily outlook | Daily | |
| PSI and PM2.5 | Per region, hourly | Hourly | Haze monitoring |
| UV index | Hourly | Hourly | |
| WBGT | Heat stress readings | ~15 min | Real-time API component (endpoint path: **verify**) |
| Lightning | Lightning observations | Near real time | Real-time API component (endpoint path: **verify**) |

Practical notes:
- Station metadata (ID, name, latitude, longitude) comes with each response; store it.
- Timestamps are in SGT (UTC+8) with offset; convert to UTC for storage.
- Missing stations appear and disappear; never assume the station list is fixed.
- The data.gov.sg status page reports outages per component; handle missing data gracefully.

Other Singapore sources:
- **weather.gov.sg (MSS)**: radar imagery, climate station statistics, historical daily data per station (downloadable), climate reports. Check terms before automated use.
- **PUB**: water-level information and flood alerts (Telegram channel, myENV app, SMS subscription).
- **MPA**: tide predictions.

## 16.2 Global forecast data

| Source | What | Access |
| --- | --- | --- |
| **Open-Meteo** | Forecasts from many models (ECMWF IFS and AIFS, GFS, ICON, and others), ensemble API, historical weather (ERA5), marine, air quality | Free JSON API, no key for non-commercial use; commercial plans available |
| **ECMWF open data** | Subset of HRES, ENS and AIFS fields at 0.25° | GRIB2 files, free, CC-BY-4.0 |
| **NOAA GFS / GEFS** | Global deterministic and ensemble | GRIB2 via NOMADS and AWS/Google cloud buckets |
| **DWD ICON** | Global and ensemble | Open data server |
| **Copernicus Climate Data Store** | ERA5 reanalysis, seasonal forecasts | Free account and API |

**Open-Meteo is the fastest start**: one HTTP request returns hourly forecasts from several models for a latitude/longitude, including ensemble members, so an agent can compute probabilities without handling GRIB files.

Example request shape (verify parameters in the docs):

```
https://api.open-meteo.com/v1/forecast?latitude=1.35&longitude=103.82
  &hourly=precipitation,temperature_2m,relative_humidity_2m,wind_gusts_10m,cape
  &models=ecmwf_ifs025,gfs_seamless,icon_seamless&timezone=Asia/Singapore
https://ensemble-api.open-meteo.com/v1/ensemble?latitude=1.35&longitude=103.82
  &hourly=precipitation&models=ecmwf_ifs025
```

## 16.3 Satellite and remote sensing

| Source | What | Access |
| --- | --- | --- |
| **Himawari-9** (JMA) | 16-band imagery, 10-min full disk | NOAA Open Data on AWS (Himawari bucket), JMA/JAXA P-Tree (registration) |
| **GPM IMERG** (NASA) | Satellite precipitation, 0.1°, 30 min | NASA GES DISC (Earthdata login) |
| **GSMaP** (JAXA) | Satellite precipitation, near real time | JAXA |
| **NASA FIRMS** | Fire hotspots (MODIS, VIIRS) | Free API with map key |
| **ASMC** | Regional hotspot and haze maps | Web (MSS-hosted) |

## 16.4 Upper air and indices

| Source | What |
| --- | --- |
| University of Wyoming sounding archive | Radiosonde profiles (including Singapore, WMO 48698 — **verify**) |
| Bureau of Meteorology / NOAA CPC | MJO RMM index, daily |
| NOAA CPC / BoM | ENSO (Niño 3.4, ONI) and IOD indices |

## 16.5 Data engineering notes

- **Formats**: JSON (APIs), GRIB2 (NWP; read with `cfgrib`/`eccodes`), NetCDF (reanalysis, satellite; `xarray`), HDF5 (satellite).
- **Python libraries**: `xarray`, `cfgrib`, `metpy` (thermodynamics, indices, soundings), `pysteps` (nowcasting), `xskillscore`/`scores` (verification), `properscoring` (CRPS).
- **Storage**: store observations and forecasts in a time-series schema keyed by (source, location, variable, init time, valid time). Keep raw responses for reproducibility.
- **Caching and politeness**: respect rate limits; cache forecasts per model run (they don't change until the next run).
- **Provenance**: every number shown to a user should be traceable to source, run and retrieval time.
