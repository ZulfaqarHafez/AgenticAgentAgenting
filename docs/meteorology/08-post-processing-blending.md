# 08. Post-processing and blending

Raw model output is biased and coarse. Post-processing turns it into calibrated, location-specific guidance. This is the core of a "forecaster" agent and must be done with arithmetic and statistics, not a language model.

## 8.1 Getting a value at a location

### Nearest grid point

Simple; preferred for a coastal site when neighbours include sea points (use the nearest **land** point).

### Bilinear interpolation

For a point inside a grid cell with corner values $f_{00}, f_{10}, f_{01}, f_{11}$ and fractional position $(x, y) \in [0,1]^2$:

$$f(x,y) = f_{00}(1-x)(1-y) + f_{10}\,x(1-y) + f_{01}(1-x)\,y + f_{11}\,xy$$

Good for smooth fields (temperature, pressure, wind components). **Avoid for precipitation** in convective regimes: it smears rain, and a point forecast of "2 mm" may come from one wet corner and three dry ones. For rain use neighbourhood statistics (8.6).

### Height adjustment

$T_{site} = T_{model} + 0.0065\,(z_{model} - z_{site})$ (K, heights in m).

### Wind interpolation

Interpolate $u$ and $v$ components, not speed and direction.

## 8.2 Bias correction

**Bias** is the systematic part of the error: $b = \overline{f - o}$.

### Running-mean bias

Over the last $N$ comparable forecasts (same lead time and, ideally, same time of day):

$$\hat b = \frac{1}{N}\sum_{k=1}^{N}(f_k - o_k), \qquad f_{corrected} = f - \hat b$$

### Decaying-average (Kalman-like) bias

Updates after every verified forecast with weight $w$ (typically 0.02–0.1). Adapts to regime changes without storing history:

$$\hat b_t = (1 - w)\,\hat b_{t-1} + w\,(f_t - o_t)$$

**Worked example** with $w = 0.1$, starting from $\hat b_0 = 0$:

| Day | Forecast (°C) | Observed (°C) | Error | Updated bias |
| --- | --- | --- | --- | --- |
| 1 | 31.5 | 30.8 | +0.7 | 0.070 |
| 2 | 32.0 | 31.1 | +0.9 | 0.153 |
| 3 | 31.2 | 30.9 | +0.3 | 0.168 |
| 4 | 32.4 | 31.0 | +1.4 | 0.291 |

The model is running warm; tomorrow's 32.0 °C forecast would be corrected to ≈ 31.7 °C. With small $w$ the estimate converges slowly; a larger $w$ adapts faster but is noisier.

**Stratify** bias by lead time, time of day, season and regime: a model may be warm in the afternoon and cool at night, which a single bias would cancel out.

### Multiplicative correction for rainfall

Rain is bounded at zero and skewed, so additive correction is wrong. Use a ratio over a window: $\beta = \sum o / \sum f$, then $f_{corrected} = \beta f$. Or, better, **quantile mapping**.

### Quantile mapping

Map each forecast value to the observed value with the same cumulative probability:

$$f_{corrected} = F_{obs}^{-1}\big(F_{fcst}(f)\big)$$

where $F$ are empirical cumulative distributions built from historical forecast–observation pairs (same season, lead time). This corrects the whole distribution (too many drizzle days, too few heavy-rain events). It needs a long training period (ideally years) and care at the tails.

## 8.3 Model Output Statistics (MOS)

Regression from model predictors to observed outcomes, fitted on historical pairs:

$$\hat y = \beta_0 + \sum_{j} \beta_j x_j$$

Predictors $x_j$ can be the raw model variable, neighbouring grid values, other model fields (humidity, CAPE, wind), and time of day. Fitted by least squares: $\boldsymbol\beta = (\mathbf X^T\mathbf X)^{-1}\mathbf X^T\mathbf y$.

For **yes/no events** (rain ≥ 1 mm, thunderstorm), use **logistic regression** so outputs are probabilities:

$$P(\text{event}) = \frac{1}{1 + e^{-(\beta_0 + \sum_j \beta_j x_j)}}$$

Fit by maximising log-likelihood. Logistic regression on ensemble statistics (for example ensemble mean and spread) is a standard way to produce calibrated probabilities.

Keep predictors few and physically meaningful, and validate on data not used for fitting (cross-validation by year).

## 8.4 Ensemble post-processing

### EMOS / NGR (non-homogeneous Gaussian regression)

For variables close to Gaussian (temperature), model the predictive distribution as $\mathcal N(\mu, \sigma^2)$ with

$$\mu = a + b\,\bar x_{ens}, \qquad \sigma^2 = c + d\,s_{ens}^2$$

where $\bar x_{ens}$ and $s_{ens}^2$ are the ensemble mean and variance. Fit $a, b, c, d$ by minimising CRPS over training data (chapter 12). This corrects both bias and under- or over-dispersion.

For rainfall, use a censored or zero-adjusted distribution (for example a censored, shifted gamma) because of the many zeros.

### Isotonic regression and reliability calibration

For probabilities, recalibrate with a monotone mapping learned from past forecasts: bin raw probabilities, compute the observed frequency in each bin, and map raw to observed. Isotonic regression does this without fixed bins while preserving order.

## 8.5 Multi-model blending

Combining several sources usually beats the best single source, because errors partly cancel.

### Equal weights

$\bar f = \frac{1}{M}\sum_m f_m$. A strong default when there is little verification history.

### Inverse-error weights

Weight each source by the inverse of its recent mean squared error:

$$w_m = \frac{1/\text{MSE}_m}{\sum_k 1/\text{MSE}_k}, \qquad \bar f = \sum_m w_m f_m$$

**Worked example.** Recent RMSE of three temperature sources: A = 1.2 °C, B = 1.8 °C, C = 2.5 °C. Inverse-MSE weights: A 0.597, B 0.265, C 0.138. With forecasts 31.0, 32.4 and 30.2 °C, the blend is ≈ 31.26 °C.

Cautions:
- Estimate MSE over enough cases (≥ 30–60) stratified by lead time; noisy weights can be worse than equal weights.
- Sources are correlated (models share observations and physics), so blending gives less benefit than independent errors would suggest.
- Bias-correct before blending.

### Bayesian model averaging (BMA)

The predictive density is a weighted mixture of per-source densities:

$$p(y) = \sum_m w_m\,g_m(y \mid f_m)$$

with weights and kernel widths fitted by maximum likelihood (EM algorithm). Gives a full distribution, not just a blended value.

### Blending probabilities

For event probabilities from several sources, average in log-odds space (more principled than averaging probabilities when sources are calibrated):

$$\operatorname{logit}(\bar p) = \sum_m w_m \operatorname{logit}(p_m), \qquad \operatorname{logit}(p) = \ln\frac{p}{1-p}$$

Then recalibrate the result against verification.

## 8.6 Neighbourhood statistics for convective rain

Because convection-permitting models misplace storms, a point value is unreliable. Use statistics over a neighbourhood of radius $r$ around the site:

- **Neighbourhood probability**: fraction of grid points within $r$ where rain ≥ threshold: $P_{nbhd} = \frac{1}{N_r}\sum_{i \in r}\mathbb 1(f_i \ge \tau)$.
- **Neighbourhood maximum**: the largest value within $r$ ("rain is possible up to X nearby").
- Choose $r$ from verification: the radius at which the forecast becomes skilful (the fractions skill score in chapter 12 gives this directly). Typical values for tropical convection are 10–40 km.

Combining neighbourhood with ensembles (all members, all points within $r$) gives smoother, better-calibrated probabilities.

## 8.7 Order of operations

1. Extract the site value (nearest land point, or neighbourhood for rain).
2. Correct units and time zone; compute interval values from accumulations.
3. Bias-correct per source (stratified).
4. Blend sources (weights from verification).
5. Convert to probabilities or quantiles (ensemble counting, EMOS, logistic regression).
6. Recalibrate (isotonic/reliability).
7. Store everything with versioned parameters so results can be verified and reproduced.
