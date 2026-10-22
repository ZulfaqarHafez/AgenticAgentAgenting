# Meteorology Knowledge Base

A working reference for building weather agents: how forecasters reason, the physics and statistics behind it, the formulas an agent needs to compute, and the regional knowledge for Singapore and Southeast Asia.

It has two parts:

- **Chapters** (this folder): human-readable explanations with formulas and worked examples.
- **Knowledge graph** (`knowledge-graph.json`): the same concepts as typed nodes and relationships, for agents to query (for example "which instruments measure rainfall?" or "which metrics verify a probability forecast?").

## Chapters

| # | Chapter | What it covers |
| --- | --- | --- |
| 01 | [Forecasting workflow](01-forecasting-workflow.md) | The forecaster's reasoning loop, lead-time regimes, and how each step maps to an agent |
| 02 | [Thermodynamics and moisture](02-thermodynamics-moisture.md) | Gas law, humidity variables, potential temperature, lapse rates, heat stress, with worked calculations |
| 03 | [Stability and convection](03-stability-convection.md) | Parcel theory, CAPE/CIN, stability indices, precipitable water, thunderstorm ingredients |
| 04 | [Dynamics and tropical circulation](04-dynamics-tropical-circulation.md) | Coriolis, geostrophy (and why it fails near the equator), convergence, monsoons, MJO, ENSO, IOD |
| 05 | [Observations and quality control](05-observations-qc.md) | Stations, sondes, QC algorithms, representativeness |
| 06 | [Radar, satellite and lightning](06-radar-satellite-lightning.md) | Reflectivity, Z–R relations, satellite channels, cloud-top temperature, lightning |
| 07 | [Numerical and AI weather models](07-nwp-ai-models.md) | How NWP works, resolution, parameterisation, global vs convection-permitting, AI models |
| 08 | [Post-processing and blending](08-post-processing-blending.md) | Interpolation, bias correction, MOS, multi-model blending |
| 09 | [Ensembles and probability](09-ensembles-probability.md) | Ensemble statistics, probability from members, calibration, neighbourhood methods |
| 10 | [Nowcasting](10-nowcasting.md) | Radar extrapolation, optical flow, convective initiation, blending with NWP |
| 11 | [Climatology and extremes](11-climatology-extremes.md) | Baselines, anomalies, diurnal cycle, return periods, extreme value basics |
| 12 | [Verification](12-verification.md) | Contingency scores, Brier, CRPS, reliability, ROC, spatial verification, sample size |
| 13 | [Decisions and communication](13-decisions-communication.md) | Cost–loss, economic value, thresholds, uncertainty language |
| 14 | [Singapore and regional meteorology](14-singapore-regional.md) | Seasons, Sumatra squalls, monsoon surges, diurnal convection, climate facts |
| 15 | [Hazards and health](15-hazards-health.md) | Lightning, flash floods, haze/PSI, heat stress/WBGT, squall winds |
| 16 | [Data sources](16-data-sources.md) | Singapore and global data feeds, formats, update cadence |
| 17 | [Agent pipeline](17-agent-pipeline.md) | End-to-end algorithm for a weather decision agent, roles, guardrails |
| 18 | [Constants, units and glossary](18-constants-glossary.md) | Physical constants, unit conversions, glossary |
| 19 | [Real data check](19-real-data-check.md) | What the real Singapore and global data sources return, their quirks, measured baselines and a first forecast verification |

## Conventions

- Units are SI unless stated: temperature in K for physics formulas (°C where noted), pressure in hPa, mixing ratio in kg/kg (g/kg where noted), rain rate in mm/h.
- Formulas use LaTeX (`$...$`, `$$...$$`), which GitHub renders.
- **Worked examples** use one running case where possible: a Singapore afternoon with $T = 32\,°\text{C}$, $RH = 70\%$, $p = 1008\,\text{hPa}$.
- Items marked **(verify)** are operational details (thresholds, URLs, schedules) that change over time. Check the official source before relying on them in a product.

## How agents should use this

1. Numbers come from data and the formulas here, never from a language model's memory.
2. Distinguish **weather probability** (from ensembles, statistics and verification) from **model confidence** (how sure a classifier is about its own answer). They are different quantities.
3. Official warnings (NEA, PUB, MSS) override anything the agents produce.
