# 12. Verification

Verification measures how good forecasts are. It powers the forecast scorecard, the source weights in blending (chapter 08) and the honesty of every probability the product shows.

**Rule:** choose the score to match the question. No single number describes forecast quality.

## 12.1 Setting up verification data

For every forecast, store:
- source (model/provider), version, initialisation time, valid time, lead time
- location, variable, threshold (if any), forecast value or probability
- the matched observation (with QC flag) and how it was matched (point, neighbourhood, radar)

Match forecasts and observations over the **same period and definition**: a "rain today" forecast must be matched with the same local-day window and the same rain threshold.

## 12.2 Binary (yes/no) events: the contingency table

For events such as "rain ≥ 1 mm in the afternoon":

| | Observed yes | Observed no |
| --- | --- | --- |
| **Forecast yes** | $a$ (hits) | $b$ (false alarms) |
| **Forecast no** | $c$ (misses) | $d$ (correct negatives) |

$n = a + b + c + d$, base rate $\bar o = (a + c)/n$.

| Score | Formula | Range (perfect) | Meaning |
| --- | --- | --- | --- |
| Probability of detection (POD, hit rate) | $\dfrac{a}{a+c}$ | 0–1 (1) | Fraction of events that were forecast |
| False alarm ratio (FAR) | $\dfrac{b}{a+b}$ | 0–1 (0) | Fraction of "yes" forecasts that were wrong |
| Probability of false detection (POFD, false alarm rate) | $\dfrac{b}{b+d}$ | 0–1 (0) | Fraction of non-events wrongly forecast |
| Frequency bias | $\dfrac{a+b}{a+c}$ | 0–∞ (1) | > 1 over-forecasts, < 1 under-forecasts |
| Critical success index (CSI, threat score) | $\dfrac{a}{a+b+c}$ | 0–1 (1) | Ignores correct negatives; good for rare events |
| Equitable threat score (ETS, Gilbert skill score) | $\dfrac{a - a_r}{a + b + c - a_r}$, $a_r = \dfrac{(a+b)(a+c)}{n}$ | −1/3–1 (1) | CSI corrected for random hits |
| Heidke skill score (HSS) | $\dfrac{2(ad - bc)}{(a+c)(c+d) + (a+b)(b+d)}$ | −∞–1 (1) | Accuracy relative to random chance |
| Peirce skill score (PSS, Hanssen–Kuipers) | $\text{POD} - \text{POFD}$ | −1–1 (1) | Discrimination; independent of base rate |
| Accuracy (proportion correct) | $\dfrac{a+d}{n}$ | 0–1 (1) | **Misleading for rare events** |

### Worked example

$a = 30$, $b = 20$, $c = 10$, $d = 40$, $n = 100$ (base rate 40%):

| Score | Value |
| --- | --- |
| POD | 30/40 = 0.75 |
| FAR | 20/50 = 0.40 |
| POFD | 20/60 = 0.333 |
| Bias | 50/40 = 1.25 (over-forecasts) |
| CSI | 30/60 = 0.50 |
| $a_r$ | 50 × 40 / 100 = 20 |
| ETS | (30 − 20)/(60 − 20) = 0.25 |
| HSS | 2(1200 − 200)/(40·50 + 50·60) = 0.40 |
| PSS | 0.75 − 0.333 = 0.417 |
| Accuracy | 70/100 = 0.70 |

### The rare-event trap

For an event that happens on 2% of days, the forecast "never" scores 98% accuracy and has zero value. Use POD, FAR, CSI/ETS and PSS for rare events, and report the base rate alongside.

## 12.3 Continuous variables (temperature, wind, rain amount)

For forecasts $f_i$ and observations $o_i$:

| Score | Formula | Notes |
| --- | --- | --- |
| Mean error (bias) | $ME = \frac1n\sum (f_i - o_i)$ | Sign shows warm/cold or wet/dry bias |
| Mean absolute error | $MAE = \frac1n\sum \lvert f_i - o_i\rvert$ | Robust, easy to explain |
| Root mean squared error | $RMSE = \sqrt{\frac1n\sum (f_i - o_i)^2}$ | Penalises large errors |
| Correlation | Pearson $r$ | Pattern agreement, ignores bias |
| Error decomposition | $MSE = ME^2 + s_{f-o}^2$ | Bias part plus random part |

### Skill scores

Any score $S$ can be turned into a skill score relative to a reference forecast (climatology, persistence):

$$SS = \frac{S - S_{ref}}{S_{perfect} - S_{ref}}$$

For error scores where perfect = 0, $SS = 1 - S/S_{ref}$. $SS > 0$ means better than the reference. Example: a temperature MAE of 0.9 °C vs persistence MAE of 1.2 °C gives $SS = 1 - 0.9/1.2 = 0.25$.

## 12.4 Probability forecasts

### Brier score

For probability $p_i$ and outcome $o_i \in \{0, 1\}$:

$$BS = \frac{1}{n}\sum_{i=1}^{n}(p_i - o_i)^2$$

0 is perfect; lower is better.

**Worked example.** Forecasts $p = [0.9, 0.7, 0.2, 0.6, 0.1]$, outcomes $o = [1, 1, 0, 0, 0]$:

Squared errors: 0.01, 0.09, 0.04, 0.36, 0.01; $BS = 0.51/5 = 0.102$.

Reference (climatology, base rate 0.4): $BS_{clim} = \bar o(1 - \bar o) = 0.24$.

Brier skill score: $BSS = 1 - 0.102/0.24 = 0.575$.

### Murphy decomposition

Group forecasts into $K$ probability bins (for example 0, 0.1, …, 1). In bin $k$ there are $n_k$ forecasts with probability $p_k$ and observed frequency $\bar o_k$:

$$BS = \underbrace{\frac1n\sum_k n_k(p_k - \bar o_k)^2}_{\text{reliability (lower is better)}} - \underbrace{\frac1n\sum_k n_k(\bar o_k - \bar o)^2}_{\text{resolution (higher is better)}} + \underbrace{\bar o(1 - \bar o)}_{\text{uncertainty}}$$

- **Reliability**: do 70% forecasts verify 70% of the time? (calibration)
- **Resolution**: do forecasts separate event days from non-event days?
- **Uncertainty**: depends only on the climate, not the forecast.

(The decomposition is exact when every forecast in a bin has the same probability.)

### Reliability diagram

Plot $\bar o_k$ (y-axis) against $p_k$ (x-axis) per bin, with the diagonal as perfect reliability, and show the number of forecasts per bin (sharpness). Points below the diagonal: overconfident (events happen less often than forecast). Points above: underconfident.

### ROC curve and area

For a probability forecast, choose decision thresholds $t$ ("forecast yes if $p \ge t$"). For each threshold compute POD and POFD. Plot POD (y) against POFD (x).

- Area under the curve (AUC): 0.5 = no discrimination, 1 = perfect. Calculate with the trapezoidal rule over the points.
- ROC measures **discrimination only**; a forecast can have good ROC but poor calibration (fix with recalibration).

### Logarithmic (ignorance) score

$$IGN = -\frac1n\sum_i \log_2 p_i(o_i)$$

where $p_i(o_i)$ is the probability given to what actually happened. Strongly penalises confident wrong forecasts (and is infinite for a 0% forecast of an event that happens), so never issue exactly 0% or 100%.

## 12.5 Continuous probability forecasts: CRPS

The continuous ranked probability score compares a forecast cumulative distribution $F$ with the observation $y$:

$$CRPS(F, y) = \int_{-\infty}^{\infty}\big[F(x) - \mathbb 1(x \ge y)\big]^2\,dx$$

It is in the units of the variable, reduces to MAE for a deterministic forecast, and lower is better.

**For an ensemble** of $N$ members (the "energy" form):

$$CRPS = \frac1N\sum_{i=1}^N\lvert x_i - y\rvert - \frac{1}{2N^2}\sum_{i=1}^N\sum_{j=1}^N\lvert x_i - x_j\rvert$$

Worked example: members $\{2, 5, 8\}$, observation $y = 6$:
- First term: $(4 + 1 + 2)/3 = 2.333$
- Pairwise differences over all ordered pairs sum to $2(3 + 6 + 3) = 24$; second term $= 24/(2 \cdot 9) = 1.333$
- $CRPS = 1.0$

**For a Gaussian forecast** $\mathcal N(\mu, \sigma^2)$, with $z = (y - \mu)/\sigma$, $\Phi$ the standard normal CDF and $\varphi$ its density:

$$CRPS = \sigma\left[z\,(2\Phi(z) - 1) + 2\varphi(z) - \frac{1}{\sqrt\pi}\right]$$

Example: $\mu = 10$, $\sigma = 4$, $y = 15$ gives $CRPS \approx 3.15$.

The CRPS skill score $CRPSS = 1 - \overline{CRPS}/\overline{CRPS}_{ref}$ compares with climatology.

## 12.6 Spatial verification for convective rain

Point verification of high-resolution rain suffers from the **double penalty**: a storm forecast 10 km too far west is counted as both a miss (where it happened) and a false alarm (where it was forecast), scoring worse than forecasting nothing.

### Fractions skill score (FSS)

Convert forecast and observed fields to binary (rain ≥ threshold), then compute the fraction of "yes" points in a square neighbourhood of size $L$ around each grid point, giving fields $P_f$ and $P_o$:

$$FSS = 1 - \frac{\frac1N\sum (P_f - P_o)^2}{\frac1N\left[\sum P_f^2 + \sum P_o^2\right]}$$

- FSS rises with neighbourhood size $L$.
- A forecast is considered **useful** at scales where $FSS \ge 0.5 + f_o/2$, where $f_o$ is the observed base rate (fraction of the domain with rain).
- The smallest useful $L$ tells you the scale at which to issue forecasts (and the neighbourhood radius for chapter 08).

### Object-based methods

Identify rain objects in forecast and observation, match them, and compare location error, area, intensity and timing (for example MODE, SAL: Structure–Amplitude–Location). Useful for diagnosing *how* a model is wrong.

## 12.7 Sample size and significance

- Standard error of an observed frequency: $\sqrt{\bar o(1-\bar o)/n}$. With $n = 50$ and $\bar o = 0.3$: ±0.065. With $n = 500$: ±0.020.
- Reliability diagrams need tens of cases per bin; rare-event scores need many events, not just many days.
- **Compare sources on the same cases** (paired comparison), and use bootstrap resampling to get confidence intervals for score differences: resample days with replacement many times (e.g. 1000), recompute the score difference each time, and take the 2.5th and 97.5th percentiles.
- Account for autocorrelation: consecutive days are not independent. Use block bootstrap (resample blocks of several days).

## 12.8 The forecast scorecard (for the product)

For each source, location cluster, variable, lead time and season, keep running:

| Variable type | Primary scores |
| --- | --- |
| Rain yes/no (≥ 1 mm per period) | Brier score, BSS vs climatology, reliability, POD/FAR at the user's decision threshold |
| Heavy rain (≥ 20 mm/h, ≥ 50 mm/day) | POD, FAR, CSI/ETS, FSS (for gridded) |
| Temperature, WBGT | ME (bias), MAE, CRPS (if probabilistic) |
| Wind and gusts | ME, MAE; POD/FAR above gust thresholds |
| Timing of rain onset | Mean and spread of onset time error |
| Nowcasts | CSI/FSS by lead time (15, 30, 60, 120 min) |

Display rules:
- Always show sample size and the verification period.
- Show skill against climatology and persistence, not just raw scores.
- Use rolling windows (for example last 90 days) plus same-season-last-year for regime awareness.
- Feed the results into blending weights and bias correction (chapter 08), with minimum sample sizes before trusting them.
