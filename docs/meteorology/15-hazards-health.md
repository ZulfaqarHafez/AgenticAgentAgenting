# 15. Hazards and health

The weather hazards that matter most for decisions in Singapore and the region, with thresholds and the official schemes agents must respect. Official warnings always take precedence over anything the agents compute.

## 15.1 Heavy rain and flash floods

### Rain-rate categories

There is no single global standard. Commonly used:

| Category | Rate (mm/h) | Source |
| --- | --- | --- |
| Light | < 2.5 | AMS glossary |
| Moderate | 2.5–7.6 | AMS glossary |
| Heavy | > 7.6 | AMS glossary |
| Very heavy / intense | > 20–30 | Common operational use |
| Violent | > 50 | UK Met Office |

For Singapore drainage, what matters is **short-duration intensity**. Drains are designed for specific return periods, so bursts of 60–100+ mm in an hour can exceed capacity in places, especially low-lying areas and where drains are blocked or under upgrade.

### Flash floods

- Form within tens of minutes of intense rain, and usually subside within an hour or so once rain stops.
- Driven by local rain rate, catchment response, drain capacity, high tides (for coastal outlets) and blockages.
- **PUB water-level sensors**: more than 1,000 sensors in drains and canals. PUB's SMS subscription sends progressive alerts when a selected canal reaches **50%, 75%, 90% and 100%** of its depth (**verify** current scheme). PUB also issues flood-risk and flash-flood warnings through its Telegram channel and the myENV app.
- Agent rule: if PUB reports high water levels or flash floods in an area, show it immediately and do not contradict it.

### Useful rain-based triggers (for internal risk scoring, calibrate locally)

- Radar-estimated or gauge rain ≥ 30 mm in 30 minutes, or ≥ 50 mm in 1 hour, over a catchment: elevated flash-flood potential.
- Rising nowcast probability of ≥ 50 mm/h within 1 hour over a known flood-prone area: early heads-up.

These are starting points for a risk score, not official thresholds.

## 15.2 Lightning

- Singapore has a high frequency of thunderstorms; lightning is a leading weather-related safety risk for outdoor workers, sports, golf, beaches and events.
- **Detection-based alert logic** (chapter 06): alert when strikes are detected within a radius (for example 8–15 km) of a site; all-clear after 15–30 minutes without strikes in the radius.
- **Flash-to-bang distance**: $d \approx \Delta t/3$ km.
- **30-30 guidance**: go indoors if thunder follows lightning within 30 s; wait 30 minutes after the last thunder.
- NEA provides lightning information (myENV app); a real-time lightning API exists on data.gov.sg (chapter 16).

## 15.3 Squall winds and gusts

- Sumatra squalls and strong thunderstorm outflows can produce gusts of 40–80 km/h (11–22 m/s), occasionally more.
- Impacts: falling trees and branches, disrupted cranes and port operations, small craft, outdoor structures (tents, stages).
- **Gust estimate from mean wind** (approximate, depends on terrain roughness): $V_{gust} \approx G\,V_{mean}$ with gust factor $G \approx 1.4$–2 over land. In convective downbursts the gust is not related to the prior mean wind, so use convective diagnostics ($\Delta\theta_e$, dry mid-levels, radar) instead.
- **Beaufort conversion**: $V \approx 0.836\,B^{3/2}$ m/s.
- Typical operational limits: many cranes must stop above ~15–20 m/s (check each operator's limits); tents and temporary structures often have much lower limits (check their certification).

## 15.4 Haze and air quality

### Sources

Transboundary smoke from land and forest fires in Sumatra and Kalimantan, mostly during the southwest monsoon (June–October), worse in El Niño and positive-IOD years (chapter 04).

### Singapore's Pollutant Standards Index (PSI)

24-hour PSI bands used by NEA (**verify** current health advisories):

| 24-h PSI | Descriptor |
| --- | --- |
| 0–50 | Good |
| 51–100 | Moderate |
| 101–200 | Unhealthy |
| 201–300 | Very unhealthy |
| > 300 | Hazardous |

PSI is computed from sub-indices for six pollutants (PM2.5, PM10, ozone, CO, NO₂, SO₂); the overall PSI is the **maximum** sub-index:

$$PSI = \max_j\,I_j, \qquad I_j = \frac{I_{hi} - I_{lo}}{C_{hi} - C_{lo}}(C_j - C_{lo}) + I_{lo}$$

where $C_j$ is the pollutant concentration and $[C_{lo}, C_{hi}]$ is the breakpoint band it falls in, mapped linearly to index band $[I_{lo}, I_{hi}]$. Breakpoint tables are published by NEA.

### 1-hour PM2.5 concentration bands (NEA)

| Band | 1-h PM2.5 (µg/m³) | Meaning |
| --- | --- | --- |
| I | 0–55 | Normal |
| II | 56–150 | Elevated |
| III | 151–250 | High |
| IV | ≥ 251 | Very high |

(**verify** current bands and associated advice.)

### Haze forecasting logic

1. **Hotspots**: satellite fire detections (3.9 µm channel; NASA FIRMS, ASEAN Specialised Meteorological Centre hotspot maps).
2. **Transport**: low-level winds (and trajectories) from hotspot regions toward Singapore. A southwesterly to southerly flow from Sumatra is the classic haze pattern.
3. **Dispersion**: rain removes smoke (wet deposition); stable nights trap it near the surface.
4. **Persistence**: haze episodes often last days to weeks; persistence is a strong baseline.

The **ASEAN Specialised Meteorological Centre (ASMC)**, hosted by MSS, monitors regional fires and haze.

## 15.5 Heat stress

### WBGT and NEA heat stress advisory

NEA's heat stress advisory (launched 2023) uses Wet Bulb Globe Temperature (chapter 02):

| WBGT | Heat stress | Public guidance (summary) |
| --- | --- | --- |
| < 31 °C | Low | Continue normal activities; stay hydrated |
| 31 to < 33 °C | Moderate | Reduce outdoor activities, drink more fluids, take regular breaks |
| ≥ 33 °C | High | Minimise outdoor activities, actively cool down |

- NEA operates nine WBGT stations islandwide; published readings are 15-minute averages from the nearest station.
- Some sectors use stricter thresholds (for example outdoor adventure education providers take precautions above 30 °C WBGT).
- Higher-risk groups (outdoor workers, elderly, young children, people with chronic conditions, athletes) need lower thresholds.

### Work–rest guidance

Occupational standards (for example ACGIH/ISO 7243) set WBGT limits that depend on workload and acclimatisation. A product advising workplaces should follow the official Singapore Ministry of Manpower guidance on heat stress (**verify**), not invent work–rest schedules.

### Heat index

The heat index (chapter 02) is common in apps but is not Singapore's official measure; prefer WBGT.

## 15.6 Coastal and marine

- **High tides**: spring tides combined with heavy rain raise flood risk where drains outlet to the sea. Tide predictions are published by the Maritime and Port Authority (MPA).
- **Strait of Malacca and Singapore Strait**: squalls create sudden strong winds and rough seas for small craft.
- **Waterspouts** occasionally form under convective clouds over coastal waters.

## 15.7 Hazard priority for an agent

1. Active official warnings (NEA heavy rain, PUB flood, NEA haze/heat advisories).
2. Lightning within the alert radius (immediate safety).
3. Flash-flood risk in the user's area.
4. Squall gusts for wind-sensitive operations.
5. Heat stress for outdoor activity.
6. Haze for health-sensitive users.
7. General rain probability for convenience decisions.
