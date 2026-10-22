# 14. Singapore and regional meteorology

Singapore (about 1.35° N, 103.8° E) is a small, low-lying island at the southern tip of the Malay Peninsula, with the Strait of Malacca and Sumatra to the west and the South China Sea to the east. Its weather is equatorial: hot, humid and rainy all year, with no dry season, and controlled by monsoons, convection and the diurnal cycle rather than fronts and pressure systems.

## 14.1 Climate facts (verify current normals with MSS)

| Item | Value | Source note |
| --- | --- | --- |
| Mean annual temperature | ≈ 27.5–28 °C; 2023 annual mean 28.2 °C at Changi, 0.4 °C above the 1991–2020 average | MSS annual climate report |
| Typical daily range | Max ≈ 30.5–32 °C, min ≈ 24–26 °C | MSS normals |
| January example (1991–2020) | Mean max 30.6 °C, mean min 24.3 °C, rainfall ≈ 222 mm, ≈ 13 rain days | MSS station statistics |
| Mean annual rainfall | Changi 2,149 mm (1991–2020, 26 complete years; range 1,119–2,886 mm); western and central stations are wetter | Computed from MSS daily files (chapter 19) |
| Relative humidity | Typically > 90% at night and early morning, 60–70% on sunny afternoons | General climatology |
| Wettest months | December (338 mm at Changi), November (257 mm), January (227 mm) | Chapter 19 |
| Driest month | February (108 mm, 6.4 rain days at Changi) | Chapter 19 |
| Lightning | High thunderstorm frequency by global standards | MSS |

The 2014–2023 decade was Singapore's warmest on record (mean 28.06 °C), and warming is ongoing. Use recent normals and trend-aware baselines (chapter 11).

## 14.2 The four seasons

### Northeast monsoon (about December to early March)

- Prevailing northeasterly winds from the South China Sea.
- **Wet phase (December–January)**: prolonged widespread rain, especially during **monsoon surges** (chapter 04): 1–3 days of continuous moderate to heavy rain, windy and cooler (daily maximum sometimes only 25–27 °C).
- **Dry phase (late January/February–early March)**: drier, sunnier, often windy; February is typically the driest month.
- Afternoon showers still occur on many days.

### Inter-monsoon (about late March to May)

- Light and variable winds, strong daytime heating.
- **Afternoon and early-evening thunderstorms** are the dominant pattern: intense, localised, short (often 1–2 hours) with lightning and gusts. In April 2025, 87% of heavy gauge-hours fell between 12:00 and 21:00 (chapter 19).
- April–May are among the hottest months.

### Southwest monsoon (about June to September)

- Prevailing southwesterly to southeasterly winds.
- Generally less rain than other seasons, but:
  - **Sumatra squalls**: lines of thunderstorms that develop over Sumatra or the Strait of Malacca at night and sweep eastward across Singapore, usually **pre-dawn to late morning**, with strong gusts (often 40–80 km/h) and heavy rain for 1–2 hours.
  - **Haze** risk from land and forest fires in Sumatra and Kalimantan, carried by the southwesterly flow, especially in El Niño and positive IOD years (chapter 15).
- Afternoon thunderstorms also occur, particularly with sea-breeze convergence.

### Inter-monsoon (about October to November)

- Light, variable winds again; often described as afternoon and evening thunderstorms, but the timing varies by year: in October 2025 heavy rain came mostly pre-dawn and late at night (chapter 19). Use multi-year hourly baselines rather than assuming.
- November is one of the wettest months as the northeast monsoon sets in.

## 14.3 Key rain-producing systems

| System | When | Time of day | Character | Forecasting approach |
| --- | --- | --- | --- | --- |
| Diurnal convection | All year; strongest Apr and Dec in the 2024–25 sample | Late afternoon (15:00–19:00 SGT) in Dec 2024 and Apr 2025; **not** in Oct 2025 (chapter 19) | Localised, intense, short; sea-breeze triggered | Diurnal climatology + CAPE/moisture + radar nowcast |
| Sumatra squall | Mainly SW monsoon and inter-monsoons (Apr–Nov) | Pre-dawn to morning (≈ 04:00–10:00 SGT) | Organised line, gusty, 1–2 h heavy rain | Track on satellite/radar from Sumatra overnight; NWP for development |
| Monsoon surge | NE monsoon (Dec–Feb) | Any; often prolonged | Widespread, continuous, windy | Global NWP and ensembles, 3–7 days ahead |
| MJO active phase | All year | Modulates others | Enhances rainfall for 1–3 weeks | RMM phase 4–5, extended-range ensembles |
| Tropical cyclones (distant) | Mainly May–Dec in South China Sea / Bay of Bengal | n/a | Rarely direct (Singapore is too close to the equator), but can draw moisture or cause dry, hazy spells | Global NWP |

### Sumatra squalls: details

- **Formation**: nocturnal land breezes from Sumatra and the Malay Peninsula converge over the Strait of Malacca; combined with southwest monsoon flow and a low-level jet, this organises convection into lines.
- **Movement**: eastward at about 30–50 km/h. Satellite and radar can track them for hours before arrival.
- **Arrival estimate**: distance to the squall line divided by its speed (chapter 10), updated hourly.
- **Hazards**: strong gusts (falling trees, disrupted port and construction operations), heavy rain, lightning.

### Diurnal convection: details

- Sea breezes typically begin late morning. Convergence zones over the island interior, western Singapore and southern Johor favour storm initiation.
- Storms are often triggered first over **Johor** or **western Singapore** and propagate along outflow boundaries.
- Climatologically, rain is more frequent in the **west and centre** of the island than the east in many seasons; check gauge climatology per area.

## 14.4 Spatial variability

- Rain can vary dramatically across distances of a few km in a single storm.
- The island's daily rainfall map often shows one area with 50–100 mm and another with none.
- For a product, forecast and verify **by area** (for example the 47 areas used in NEA's 2-hour forecasts or by planning region) and by nearest gauge, not for "Singapore" as a whole.

## 14.5 Local data and services

- **MSS (Meteorological Service Singapore)**, part of NEA, issues forecasts, warnings and climate information, and runs the station network, radar and the SINGV model (chapter 07).
- **NEA forecasts**: 2-hour area nowcasts (updated every 30 minutes), 24-hour forecasts, 4-day outlooks, fortnightly and monthly outlooks.
- **PUB** (national water agency) manages drains and canals, water-level sensors and flood alerts (chapter 15).
- **Heavy rain warnings**: NEA SMS and app alerts when heavy rain is expected; follow-ups when it is no longer expected.

## 14.6 Regional neighbours relevant to forecasts

| Region | Why it matters |
| --- | --- |
| Sumatra and Strait of Malacca | Origin of squalls; fire hotspots for haze |
| Johor (Malaysia) | Afternoon storms often form here and drift south |
| South China Sea | Monsoon surges, moisture source in NE monsoon |
| Kalimantan (Borneo) | Fire hotspots; Borneo vortex |
| Java Sea / Indian Ocean | Moisture source; IOD influence |

Agents should monitor an area of at least a few hundred km around Singapore (roughly 98–108° E, 3° S–6° N) for incoming systems.

## 14.7 Common forecasting pitfalls in Singapore

1. **Treating "rain in Singapore" as one event.** Always localise.
2. **Trusting global-model point rain.** Global models drizzle too often and too lightly; use convection-permitting models, ensembles and neighbourhood methods.
3. **Ignoring the diurnal cycle.** The time of day is often the strongest single predictor of rain.
4. **Using mid-latitude rules.** Pressure tendencies, fronts and geostrophic reasoning do not apply (chapter 04).
5. **Forgetting time zones.** Model output is in UTC; Singapore is UTC+8.
6. **Coastal grid cells.** Coarse models may treat Singapore as sea.
7. **Overconfident timing.** Forecast windows (for example 14:00–18:00), not exact times.
