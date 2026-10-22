# 11. Climatology and extremes

Climatology is what normally happens. It is the baseline every forecast must beat and the prior for every probability.

## 11.1 Climate normals

A **climate normal** is a 30-year average (WMO standard periods, currently 1991–2020). Compute separately for each:
- location (station or grid cell),
- calendar period (month, or a smoothed day-of-year window),
- hour of day, for variables with a strong diurnal cycle (rain, temperature, wind, lightning).

### Smoothed day-of-year climatology

Raw daily means from 30 years are noisy. Smooth with a moving window (e.g. ±15 days) or fit harmonics:

$$\mu(d) = a_0 + \sum_{k=1}^{K}\left[a_k\cos\frac{2\pi k d}{365.25} + b_k\sin\frac{2\pi k d}{365.25}\right]$$

with $K = 2$–3 harmonics, fitted by least squares on day of year $d$. The same idea applies to diurnal cycles with period 24 h.

### Climatological event frequency

For an event such as "rain ≥ 1 mm between 14:00 and 18:00":

$$p_{clim} = \frac{\text{number of days with the event}}{\text{number of days with valid data}}$$

computed per month or day-of-year window. This $p_{clim}$ is the baseline probability forecast, and the reference for skill scores (chapter 12).

## 11.2 Anomalies

- **Anomaly**: $x' = x - \mu$
- **Standardised anomaly**: $z = \dfrac{x - \mu}{\sigma}$, which makes values comparable across places and seasons.
- **Percentile rank**: where the value falls in the historical distribution for that place and time (better than $z$ for skewed variables like rainfall).

For forecasts, the **model-climate anomaly** is useful: compare a model's forecast with that same model's own historical forecasts for the date (the ECMWF Extreme Forecast Index is built this way). It removes model bias from "is this unusual?" judgements.

## 11.3 Rainfall statistics

Rainfall is intermittent and highly skewed, so means mislead.

- **Wet-day frequency**: fraction of days with ≥ 1 mm (or ≥ 0.2 mm; state the threshold).
- **Intensity**: mean rainfall on wet days.
- **Percentiles of wet-day totals** (90th, 99th) for "heavy" thresholds.
- **Distribution models**: wet-day amounts are often fitted with a **gamma distribution**:

$$f(x; k, \theta) = \frac{x^{k-1}e^{-x/\theta}}{\Gamma(k)\,\theta^k}, \quad x > 0$$

Method-of-moments estimates: $\hat k = \bar x^2/s^2$, $\hat\theta = s^2/\bar x$. The full distribution is a mixture: probability $1 - p_{wet}$ of zero, plus $p_{wet}$ times the gamma.

### Intensity–duration–frequency (IDF)

Urban drainage design and flash-flood risk use IDF curves: for each duration (5 min, 15 min, 1 h, 3 h, 24 h), the rainfall depth expected once per $T$ years. Short-duration intensity (for example 60–100+ mm in 1 hour) is what overwhelms drains in Singapore, not daily totals.

## 11.4 Extremes and return periods

### Return period and exceedance probability

If an event has annual exceedance probability $p$, its **return period** is $T = 1/p$ years.

Probability of at least one occurrence in $n$ years:

$$P = 1 - (1 - 1/T)^n$$

Examples:
- A 100-year event over 30 years: $1 - 0.99^{30} \approx 26\%$.
- A 50-year event over 10 years: $1 - 0.98^{10} \approx 18\%$.

"100-year event" does not mean once a century; it means 1% chance every year.

### Generalised extreme value (GEV) distribution

For block maxima (for example each year's maximum 1-hour rainfall):

$$F(x) = \exp\!\left\{-\left[1 + \xi\,\frac{x - \mu}{\sigma}\right]^{-1/\xi}\right\}$$

with location $\mu$, scale $\sigma$ and shape $\xi$ ($\xi = 0$ gives the Gumbel distribution $F(x) = \exp\{-e^{-(x-\mu)/\sigma}\}$). The $T$-year return level is the value with $F(x_T) = 1 - 1/T$:

$$x_T = \mu - \frac{\sigma}{\xi}\left\{1 - \left[-\ln(1 - 1/T)\right]^{-\xi}\right\} \quad (\xi \ne 0)$$

Gumbel case: $x_T = \mu - \sigma\ln[-\ln(1 - 1/T)]$.

Fit by maximum likelihood or L-moments. Return levels beyond about twice the record length are very uncertain; always give confidence intervals.

### Peaks over threshold

Alternative to block maxima: model all exceedances above a high threshold $u$ with a generalised Pareto distribution. Uses more data than annual maxima.

## 11.5 Trends and non-stationarity

Climate is changing, so normals drift. In the tropics, warming increases saturation vapour pressure by about 7% per °C (Clausius–Clapeyron, chapter 02), and short-duration extreme rainfall intensities are expected to increase at a similar or higher rate. For agents:
- Use recent normals (1991–2020) rather than older periods.
- Prefer recent years when estimating rare-event thresholds, or include a trend term.
- Do not assume historical return periods apply unchanged.

## 11.6 Baselines every forecast must beat

| Baseline | Definition | When it is hard to beat |
| --- | --- | --- |
| Climatology | $p_{clim}$ or $\mu$ for this place and time | Long lead times, rare events |
| Diurnal climatology | Climatology for this hour of day | Afternoon convection in inter-monsoon periods |
| Persistence | Tomorrow = today | Stable regimes (monsoon surges, dry spells, haze episodes) |
| Lagrangian persistence | Extrapolated radar | 0–1 h |

A forecast system is only useful where it shows positive skill against the relevant baseline (chapter 12). Agents should track and report this honestly.
