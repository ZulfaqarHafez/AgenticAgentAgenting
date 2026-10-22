# 05. Observations and quality control

Every forecast and every verification score depends on observations. Raw observations contain errors, so an agent must quality-control them before use.

## 5.1 Observation types

| Type | Measures | Typical cadence | Notes |
| --- | --- | --- | --- |
| Automatic weather station (AWS) | Temperature, humidity, pressure, wind, rainfall | 1–5 min | Point measurement; Singapore has a dense network (dozens of rain gauges) |
| Tipping-bucket rain gauge | Rainfall | Per tip (often 0.2 mm) | Under-catches in strong wind and very heavy rain |
| Radiosonde (weather balloon) | Vertical profiles of T, $T_d$, wind, pressure | 00 and 12 UTC (Singapore station WSSS/48698, **verify**) | Basis for stability indices |
| Weather radar | Precipitation intensity, motion | 5–10 min | See chapter 06 |
| Geostationary satellite | Cloud, cloud-top temperature, water vapour | 10 min full disk (Himawari) | See chapter 06 |
| Lightning detection | Strike location and time | Seconds | See chapter 06 |
| Wind profilers, aircraft (AMDAR), buoys | Upper winds, ocean surface | Varies | Mainly feed models |

## 5.2 Measurement standards (WMO)

- **Temperature and humidity**: 1.25–2 m above ground, in a ventilated, shaded screen, over grass.
- **Wind**: 10 m above ground, away from obstacles (ideally a distance of 10× obstacle height). Reported as **mean wind** (usually 10-minute average, WMO) and **gust** (maximum 3-second average).
- **Rainfall**: accumulations over defined periods; rain rate from short-period accumulations.
- **Time**: always store in UTC. Singapore local time is UTC+8.

## 5.3 Unit handling

| Quantity | Conversions |
| --- | --- |
| Wind | 1 m/s = 3.6 km/h = 1.944 kt; 1 kt = 0.5144 m/s |
| Wind direction | Meteorological convention: direction the wind blows **from**, degrees clockwise from north. $u = -|V|\sin\phi$, $v = -|V|\cos\phi$ |
| Pressure | 1 hPa = 100 Pa = 1 mb |
| Temperature | K = °C + 273.15; °F = 1.8 °C + 32 |
| Rainfall | 1 mm = 1 L/m² = 1 kg/m² |

Wind direction from components: $\phi = \operatorname{atan2}(-u, -v)$ in degrees, wrapped to $[0, 360)$.

**Never average wind directions arithmetically** (the mean of 350° and 10° is 0°, not 180°). Average the $u$ and $v$ components instead, or use circular mean $\bar\phi = \operatorname{atan2}(\overline{\sin\phi}, \overline{\cos\phi})$.

## 5.4 Quality-control algorithms

Run these checks in order. Flag rather than delete, and keep the flag with the data.

### 1. Range (gross error) check

Reject values outside physically plausible limits for the location. Example limits for Singapore:

| Variable | Plausible range |
| --- | --- |
| Temperature | 18–40 °C |
| Relative humidity | 20–100% |
| Sea-level pressure | 990–1025 hPa |
| 5-minute rainfall | 0–25 mm (≈ 300 mm/h) |
| Wind speed | 0–40 m/s |

(These are conservative starting values. Tune them from the station's historical extremes.)

### 2. Step (rate-of-change) check

Flag jumps between consecutive readings larger than physically plausible:

$$|x_t - x_{t-1}| > \Delta_{max}$$

For temperature at 1–5 minute intervals, a few °C is plausible (storm outflows can drop temperature 5–8 °C in 10–20 minutes), so set $\Delta_{max}$ generously and combine with other checks.

### 3. Persistence (stuck sensor) check

Flag a sensor that reports the same value for too long when variation is expected: the standard deviation over a window $< \sigma_{min}$, or an identical value for N consecutive readings (for example temperature constant for 2+ hours in daytime).

### 4. Internal consistency

- $T_d \le T$ always.
- $RH \le 100\%$ (allow small instrument error up to ~103%, then cap).
- Rain without cloud on satellite and no radar echo is suspicious (gauge malfunction, irrigation, cleaning).
- Gust ≥ mean wind.

### 5. Spatial (buddy) check

Compare each station with neighbours within radius $R$. Use robust statistics so one bad neighbour does not distort the check:

$$\text{flag if}\quad \frac{|x_s - \operatorname{median}(x_{nbrs})|}{\max(\operatorname{MAD}(x_{nbrs}),\ \sigma_{floor})} > k$$

where $\operatorname{MAD} = \operatorname{median}(|x_i - \operatorname{median}(x)|)$, $k \approx 3$–5, and $\sigma_{floor}$ prevents division by zero when all neighbours agree. For temperature, adjust neighbours for elevation first.

**Caution for rainfall:** tropical rain is extremely localised. A gauge reading 40 mm while neighbours 3 km away read 0 can be correct. Use radar to confirm before rejecting. Never buddy-check rainfall against gauges alone.

### 6. Temporal completeness

Track missing data. Do not compute daily totals or verification scores from incomplete records without flagging them. A common rule: require ≥ 90% of expected readings for a valid aggregate.

## 5.5 Representativeness

A station measures one point. A model grid box represents an area average. These differ in principle, not just because of error:

- A 9 km global model's rainfall is a grid-box average, which smooths out a 60 mm/h point downpour into a few mm/h.
- **Representativeness error** must be included when comparing models with stations, especially for rainfall and convection.
- For verification of convective rain, prefer **area-based** observations (radar-derived rainfall, or the maximum or mean over several gauges in an area) and **neighbourhood** methods (chapter 12).

## 5.6 Gridding point observations

To turn stations into a map (or compare with a grid):

**Inverse distance weighting (IDW):**

$$\hat x(s_0) = \frac{\sum_i w_i x_i}{\sum_i w_i}, \qquad w_i = \frac{1}{d(s_0, s_i)^p},\ p \approx 2$$

Simple, but no uncertainty estimate and it produces "bullseyes".

**Ordinary kriging** fits a spatial covariance (variogram) and gives both an estimate and its variance. Better for temperature; rainfall needs care (intermittency, skewness).

**Radar–gauge merging**: adjust radar rainfall with gauges, for example a mean field bias correction $\beta = \sum G_i / \sum R_i$ over gauge locations, then $R_{adj} = \beta R$. More advanced: kriging with external drift, or conditional merging.

## 5.7 Data handling rules for agents

1. Store raw values, QC flags and corrected values separately.
2. Timestamp everything in UTC, with the observation's averaging period.
3. Record the source, station ID, latitude/longitude and elevation.
4. Treat missing data as missing, never as zero (especially rainfall).
5. Distinguish "0 mm observed" from "no observation".
