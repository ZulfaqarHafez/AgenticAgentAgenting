# 17. Agent pipeline

An end-to-end algorithm for a weather decision agent, built from the earlier chapters. Each step lists its inputs, computation and outputs, and whether it is deterministic code, a fast typed-decision model (for example Laya), or a language model.

## 17.1 Overview

```
User question
   │
   ▼
[1 Router] ──▶ [2 Parse] ──▶ [3 Warnings check] ──▶ [4 Observe] ──▶ [5 Diagnose]
                                                                       │
   ┌───────────────────────────────────────────────────────────────────┘
   ▼
[6 Gather forecasts] ──▶ [7 Post-process & blend] ──▶ [8 Probabilities] ──▶ [9 Critic]
                                                                              │
   ┌──────────────────────────────────────────────────────────────────────────┘
   ▼
[10 Decide] ──▶ [11 Explain] ──▶ [12 Output check] ──▶ Answer
                                                          │
                              [13 Verify later] ◀─────────┘ (logs forecast; scores it when observations arrive)
```

## 17.2 Steps

### 1. Router (fast typed-decision model)

Typed questions answered in one call:
- `intent`: choice of {go/no-go decision, timing window, current conditions, hazard check, general info, not weather}
- `urgency`: score 0–1 (for example "trees falling, should we evacuate the site?" scores high)
- `weather_sensitive`: yes/no
- `needs_nowcast`: yes/no (horizon under 6 hours)
- `hazards_mentioned`: multi-choice {rain, lightning, wind, heat, haze, flood}

Outputs decide which later steps run (for example skip ensembles for a "what's it like now?" question). Store the router's confidences in their own fields; they are **not** weather probabilities (chapter 09).

### 2. Parse (language model, structured output)

Extract: location (geocode to lat/lon and NEA area), time window (convert to UTC), activity, thresholds ("disruptive rain" → ≥ 5 mm/h? ask or use defaults), and costs if given. Ask a clarifying question if location or time is missing.

Defaults table (per activity, configurable):

| Activity | Event of concern | Default threshold | Default C/L |
| --- | --- | --- | --- |
| Outdoor event | Rain during event | ≥ 2 mm/h | 0.2 |
| Construction concrete pour | Rain within 6 h after pour | ≥ 1 mm | 0.3 |
| Crane lift | Gusts | ≥ 15 m/s | 0.1 |
| Outdoor sport / golf | Lightning within 10 km | any strike | 0.05 |
| Commute | Heavy rain at departure | ≥ 10 mm/h | 0.5 |

### 3. Official warnings check (deterministic)

Query NEA heavy-rain warnings, PUB flood alerts, NEA heat stress and haze advisories for the area. If any are active, they go first in the answer and the recommendation cannot be less cautious than the official advice.

### 4. Observe (deterministic)

- Latest station readings near the location (QC per chapter 05).
- Rainfall in the last 30–60 minutes across the region.
- Lightning in the last 30 minutes within 30 km.
- Radar or nowcast information (NEA 2-hour forecast; radar if available).
- Derived: dewpoint, WBGT (observed), wet-bulb, heat index.

### 5. Diagnose (deterministic rules + optional language model summary)

Compute regime indicators:
- Season and monsoon phase from the date (chapter 14).
- MJO phase and amplitude (RMM).
- Low-level wind regime from model analysis (NE/SW/light).
- Instability and moisture: CAPE, K-index, PW from model profiles (chapter 03).
- Surge indicators (925 hPa northeasterly strength over the southern South China Sea).
- Squall indicators: overnight convection over Sumatra or the Strait on satellite.

Output: a regime label (for example "inter-monsoon, light winds, high afternoon instability") used to select climatology and stratified verification statistics.

### 6. Gather forecasts (deterministic)

For each source (global deterministic, ensembles, regional models, AI models, NEA text forecasts):
- Extract site values (nearest land point) and neighbourhood statistics for rain (chapter 08).
- Align to the user's time window; compute window totals and maxima.
- Record source, run time and retrieval time.

### 7. Post-process and blend (deterministic)

- Bias-correct each source with stratified bias estimates (chapter 08).
- Weight sources with inverse-error weights from the scorecard, falling back to equal weights when samples are small (fewer than ~30 verified cases).

### 8. Probabilities (deterministic)

- Event probability from ensemble members and neighbourhoods: $p = $ fraction of members (and neighbourhood points) with the event in the window.
- Combine sources in log-odds space with scorecard weights.
- Apply the latest calibration mapping (isotonic or logistic) for this regime and lead time.
- For 0–3 h horizons, blend with the nowcast using the lead-time weight $\alpha(t)$ (chapter 10).
- Clip to [0.02, 0.98] unless the event is already happening or verified impossible.
- Provide a climatological reference probability for context.

### 9. Critic (deterministic checks + language model review)

Checks:
- **Disagreement**: spread of source probabilities; flag if max − min > 0.4.
- **Observation conflict**: forecasts say dry but radar shows rain approaching (or vice versa) → nowcast dominates.
- **Regime mismatch**: a source known to perform poorly in this regime gets down-weighted.
- **Sanity**: probabilities and amounts consistent (P(≥ 10 mm) ≤ P(≥ 1 mm)); timing windows valid.
- **Plausible worst case**: the 90th percentile scenario and its impact.

Output: confidence level (high/medium/low) with reasons.

### 10. Decide (deterministic)

- Threshold $C/L$ from the user or defaults.
- Recommend protect if $p > C/L$; if $|p - C/L| < 0.1$ and there is time, recommend checking again at a stated time (chapter 13).
- For multi-action problems, minimise expected expense across scenarios.
- Never recommend less caution than official advice.

### 11. Explain (language model)

Fill the template in chapter 13 from the structured forecast object. The language model may choose words but **must not introduce numbers** that are not in the object.

### 12. Output check (fast typed-decision model + deterministic)

Yes/no checks on the drafted message:
- Does every number in the text match a field in the forecast object? (deterministic string/number match)
- Does the text contradict the recommendation? (typed yes/no)
- Does it mention active official warnings? (deterministic)
- Does it imply more precision than given (exact minute times, exact streets)? (typed yes/no)

If any check fails, regenerate or fall back to a plain template.

### 13. Verify later (deterministic, scheduled)

- Log the forecast object, recommendation and inputs.
- When observations for the window arrive, score per chapter 12, update bias estimates, weights and calibration.
- Track recommendation outcomes: protected unnecessarily (false alarm cost), missed events (loss), correct calls, so you can report the economic value.

## 17.3 Data model (core objects)

```json
{
  "forecast_object": {
    "location": {"name": "Marina Bay", "lat": 1.283, "lon": 103.860, "nea_area": "City"},
    "window_utc": ["2026-10-24T07:00Z", "2026-10-24T10:00Z"],
    "event": {"variable": "rain_rate", "threshold": 2.0, "unit": "mm/h"},
    "p_event": 0.27,
    "p_climatology": 0.31,
    "p_by_source": {"ecmwf_ens": 0.22, "gefs": 0.35, "singv": 0.30},
    "weights": {"ecmwf_ens": 0.5, "gefs": 0.2, "singv": 0.3},
    "quantiles_mm": {"p50": 0.0, "p90": 6.5},
    "regime": "inter-monsoon, light winds, high afternoon CAPE",
    "confidence": "medium",
    "confidence_reasons": ["sources disagree on timing", "no storms on radar yet"],
    "official_warnings": [],
    "router_confidence": {"intent": 0.94},
    "provenance": [{"source": "ecmwf_ens", "run": "2026-10-24T00:00Z", "retrieved": "2026-10-24T05:12Z"}]
  },
  "decision": {"cost_loss": 0.2, "action": "protect", "check_again_at": "2026-10-24T05:30Z"}
}
```

## 17.4 Mapping to the Hive roles

| Hive role | Weather pipeline steps |
| --- | --- |
| Research | 4 Observe, 6 Gather forecasts |
| Planner | 2 Parse, 5 Diagnose |
| Executor | 7 Post-process, 8 Probabilities, 10 Decide (all deterministic code) |
| Critic | 9 Critic |
| Verifier | 3 Warnings check, 12 Output check, 13 Verify later; the proof gate requires these to pass |
| Router (new) | 1 Router (fast typed-decision model) |
| Writer (new) | 11 Explain |

The existing proof gate becomes: an answer can only be released if official warnings were checked, every number traces to data, and the output checks pass.

## 17.5 Guardrails summary

1. Official warnings first and never contradicted.
2. Numbers only from data and deterministic computation.
3. Weather probability and model confidence kept separate.
4. Probabilities calibrated and clipped; no 0% or 100% without observation.
5. Localised answers with time windows, not false precision.
6. Every forecast logged and verified; the scorecard is visible to users.
7. Clear fallback when data is missing: say what is unknown rather than guessing.
