# 09. Ensembles and probability

The most important chapter for a decision product. Forecasts are uncertain; ensembles measure that uncertainty, and probability is the language for it.

## 9.1 Why ensembles

The atmosphere is chaotic: tiny errors in the initial state grow until forecasts diverge (Lorenz, 1963). Error growth is fastest at small scales. An **ensemble** runs the forecast many times from slightly perturbed initial conditions (and sometimes perturbed model physics) to sample the range of plausible outcomes.

- ECMWF ENS: 51 members (1 control + 50 perturbed).
- NOAA GEFS: 31 members.
- Convection-permitting ensembles: typically 10–30 members.

## 9.2 Ensemble statistics

For members $x_1, \dots, x_N$:

| Statistic | Formula | Use |
| --- | --- | --- |
| Mean | $\bar x = \frac{1}{N}\sum_i x_i$ | Best single estimate (for smooth variables) |
| Spread (standard deviation) | $s = \sqrt{\frac{1}{N-1}\sum_i (x_i - \bar x)^2}$ | Uncertainty |
| Median, quantiles | Sort members; the $q$-quantile is near position $q(N-1)$ | Ranges (10th–90th percentile) |
| Exceedance probability | $P(X \ge \tau) \approx \frac{1}{N}\sum_i \mathbb 1(x_i \ge \tau)$ | Event probabilities |

**Worked example.** A 20-member ensemble of 24-hour rainfall at a site (mm):

`0, 0, 0, 0, 0, 0, 0, 1.2, 2.5, 3.0, 4.1, 5.5, 6.0, 8.2, 9.0, 12.4, 15.0, 18.3, 22.0, 30.5`

- Mean = 6.9 mm, spread ≈ 8.7 mm (larger than the mean: typical of skewed rainfall).
- $P(\ge 1\ \text{mm}) = 13/20 = 65\%$.
- $P(\ge 10\ \text{mm}) = 5/20 = 25\%$.
- Median ≈ 3.6 mm (between the 10th and 11th sorted values, 3.0 and 4.1).

**Do not use the ensemble mean for rainfall decisions.** It blends dry and wet members into a misleading "light rain everywhere" value. Use exceedance probabilities and quantiles instead.

### Sampling limits

With $N$ members the smallest non-zero probability is $1/N$, and the sampling error of an estimated probability is about $\sqrt{p(1-p)/N}$. For $p = 0.3$, $N = 20$: ±10 percentage points. Small ensembles cannot resolve rare events; combine with neighbourhood methods or post-processing.

A slightly more robust probability estimate that avoids 0% and 100% (which are rarely justified) is

$$\hat p = \frac{k + 1/3}{N + 2/3}$$

where $k$ is the number of members exceeding the threshold (a common plotting-position adjustment). Calibration against observations (chapter 08) is still needed.

## 9.3 Is the ensemble reliable? (spread–skill)

For a **well-calibrated** ensemble, the observation behaves like one more member. Then, averaged over many cases:

$$\text{RMSE}(\bar x) \approx \sqrt{\frac{N+1}{N}}\;\overline{s}$$

- If RMSE is much larger than the spread, the ensemble is **under-dispersive** (overconfident). This is common, especially near the surface and in the tropics.
- If RMSE is smaller, it is over-dispersive.

### Rank histogram (Talagrand diagram)

For each case, rank the observation among the sorted members (rank 1 to $N+1$) and build a histogram over many cases.
- Flat: reliable.
- U-shaped: under-dispersive (observation often outside the ensemble range).
- Dome-shaped: over-dispersive.
- Sloped: biased.

## 9.4 Probability fundamentals agents must get right

### What a probability of precipitation means

$PoP = 40\%$ for a location and period means: in the long run, on occasions with this forecast, measurable rain (usually ≥ 0.1–0.2 mm) occurs **at that location** during that period about 40% of the time. It does **not** mean rain for 40% of the time or over 40% of the area.

For an area, the US NWS definition is $PoP = C \times A$, where $C$ is confidence that rain will occur somewhere in the area and $A$ is the fraction of the area expected to get rain.

### Point vs area probability

The chance of rain **somewhere** in a large area is higher than at a single point. For an event with point probability $p$, the probability that at least one of $n$ independent sub-areas gets rain is $1 - (1-p)^n$. Real sub-areas are correlated, so the true value is between $p$ and that bound. Always state which one is meant.

### Time-window probability

Probability of rain in a 6-hour window is higher than in any single hour within it. Combine hourly probabilities only with care: if hours were independent, $P_{6h} = 1 - \prod_h (1 - p_h)$, but rain in consecutive hours is strongly correlated, so this overestimates. Prefer computing window probabilities directly from members (did member $i$ rain at any time in the window?).

### Conditional and compound events

"Rain ≥ 10 mm **and** gusts ≥ 15 m/s": compute from members jointly (count members where both occur), never multiply marginal probabilities unless independent.

## 9.5 Calibration

A probability forecast is **reliable** (calibrated) if events forecast with probability $p$ happen with frequency $p$. Raw ensemble probabilities are usually overconfident near the surface. Fix with post-processing (chapter 08: logistic regression, EMOS, isotonic regression) and check with reliability diagrams (chapter 12).

**Sharpness** is the tendency to forecast probabilities near 0 or 1. The goal is **maximum sharpness subject to reliability**: be as decisive as you can while staying honest.

## 9.6 Scenarios and clustering

When the ensemble splits into distinct outcomes (for example "surge arrives Tuesday" vs "Thursday"), the mean is a physically impossible average. Cluster members (k-means on key fields, or simple grouping by event timing) and present **scenarios with probabilities**: "60%: rain arrives Tuesday afternoon; 40%: holds off until Thursday."

## 9.7 Combining uncertainty sources

Total uncertainty in a site forecast comes from:
1. **Initial-condition and model uncertainty**: sampled by the ensemble.
2. **Representativeness**: point vs grid (chapter 05).
3. **Post-processing parameter uncertainty**: from finite training data.

Raw ensembles capture only the first. Calibrated post-processing accounts for all three statistically, which is why calibrated probabilities are wider than raw ensemble spread suggests.

## 9.8 Model confidence vs weather probability

A decision or classification model (for example Laya or Jev) returns a probability that **its own answer** is correct ("is this question about outdoor activity? yes, 0.92"). That is **not** a weather probability.

- Weather probabilities come only from ensembles, statistical post-processing and verification.
- Never pass a classifier's confidence into a forecast probability, and never present it to users as a chance of weather.
- Keep them in separate, clearly named fields: for example `p_rain_ge_1mm` vs `router_confidence`.
