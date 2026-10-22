# 01. Forecasting workflow

How a professional forecaster reasons, and how that maps onto agents.

## 1.1 The forecast loop

Operational forecasting is a loop, run every shift and every model cycle:

```
 ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌───────────┐   ┌──────────┐   ┌─────────────┐   ┌──────────┐
 │ Observe  │──▶│ Diagnose │──▶│ Consult  │──▶│ Reconcile │──▶│ Forecast │──▶│ Communicate │──▶│  Verify  │
 └──────────┘   └──────────┘   │  models  │   └───────────┘   │ (probab.)│   └─────────────┘   └────┬─────┘
       ▲                       └──────────┘                   └──────────┘                        │
       └──────────────────────────────── learn biases, update trust ──────────────────────────────┘
```

1. **Observe.** Establish the current state: surface stations, radar, satellite, lightning, upper-air soundings. Note anything the models did not expect.
2. **Diagnose.** Explain the current weather physically: which system is responsible (monsoon flow, squall line, sea breeze, surge), how unstable the atmosphere is, where moisture and lift come from. A forecaster who cannot explain *now* should not trust their forecast of *later*.
3. **Consult models.** Look at global deterministic runs, ensembles, convection-permitting regional models, AI models, and statistical guidance.
4. **Reconcile.** Compare models with each other and with observations. Ask: which model initialised closest to reality today? Which has known biases in this regime? Do the ensembles agree?
5. **Forecast with probability.** Express what is likely and how confident you are. Include the plausible high-impact alternative scenario.
6. **Communicate for the decision.** Translate into what matters for the user: timing, location, intensity, impact, and action thresholds.
7. **Verify.** After the event, compare forecast with observation, update knowledge of model biases and your own.

## 1.2 Lead-time regimes

Different tools dominate at different lead times. Agents must pick the right tool for the horizon asked about.

| Horizon | Name | Best tools | Predictable detail |
| --- | --- | --- | --- |
| 0–2 h | Nowcast | Radar/satellite extrapolation, lightning trends | Individual storms, minutes-level timing |
| 2–6 h | Short-range nowcast blend | Blended extrapolation + convection-permitting NWP | Storm clusters, rough timing |
| 6–48 h | Short range | Convection-permitting and global NWP, ensembles | Regime, timing windows (morning/afternoon), area coverage |
| 2–10 days | Medium range | Global ensembles (ECMWF ENS, GEFS), AI models | Synoptic pattern, wet/dry spells, surges |
| 10–30 days | Sub-seasonal | Extended ensembles, MJO forecasts | Tendencies (wetter/drier than normal) |
| 1–6 months | Seasonal | Seasonal models, ENSO/IOD state | Shifts in probability of above/below-normal rainfall |

**Practical predictability limit.** Small-scale features lose predictability fastest. A rough rule: the time over which a feature remains predictable scales with its size. Individual thunderstorms (≈1–10 km) are predictable for under an hour or two once they exist, and their *initiation* location is poorly predictable even a few hours ahead. Synoptic systems (≈1000 km) are predictable for days.

## 1.3 The forecaster's mental checklist

- What is the regime? (season, monsoon phase, MJO phase, any surge or squall line)
- What does climatology say for this place, date and hour? (the baseline to beat)
- What do the latest observations show, and how do they compare with what models predicted for now?
- What is the model consensus? What is the spread?
- Which models have verified best recently in this regime?
- What is the worst plausible case, and how likely is it?
- What decision is the user making, and at what probability should they act?
- What is my confidence, and how do I say it clearly?

## 1.4 Mapping to agents

| Forecaster step | Agent role | Inputs | Outputs |
| --- | --- | --- | --- |
| Observe | **Research** (observations) | Station, radar, satellite, lightning feeds | Current-state summary, anomalies vs model |
| Diagnose | **Planner** (diagnosis) | Observations, soundings, regime indicators | Regime label, ingredients assessment (moisture, instability, lift) |
| Consult models | **Research** (models) | NWP, ensembles, AI models | Per-source forecasts, aligned to location/time |
| Reconcile | **Critic** | Per-source forecasts, verification history | Disagreements, trusted sources, bias-corrected blend |
| Forecast | **Forecaster** (statistical, not an LLM) | Blend, ensembles, calibration tables | Calibrated probabilities and ranges |
| Communicate | **Writer** (LLM) | Probabilities, user decision, thresholds | Recommendation and explanation |
| Verify | **Verifier** | Forecast log, observations | Scores, updated bias and weights |
| Triage/route | **Router** (fast typed-decision model, e.g. Laya) | User question | Intent, urgency, which agents to run |

Guardrails:
- The **Forecaster** step is arithmetic and statistics (chapters 08, 09). A language model must not produce weather numbers.
- The **Writer** may only state numbers that appear in its inputs.
- **Official warnings** short-circuit the pipeline: if NEA/PUB has an active warning for the area, it is shown first.
