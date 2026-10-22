# 07. Numerical and AI weather models

How forecast models work, what their output means, and what their limits are.

## 7.1 What a numerical weather prediction (NWP) model is

A model solves the equations of atmospheric motion on a 3-D grid, stepping forward in time from an estimate of the current state.

### The governing equations (the "primitive equations")

1. **Momentum** (Newton's second law with pressure gradient, Coriolis, friction): $\dfrac{D\vec V}{Dt} = -\dfrac{1}{\rho}\nabla p - 2\vec\Omega\times\vec V + \vec g + \vec F$
2. **Mass continuity**: $\dfrac{\partial\rho}{\partial t} + \nabla\cdot(\rho\vec V) = 0$
3. **Thermodynamic energy**: $c_p\dfrac{DT}{Dt} - \dfrac{1}{\rho}\dfrac{Dp}{Dt} = Q$ (heating from radiation, latent heat, surface fluxes)
4. **Water substance conservation**: $\dfrac{Dq}{Dt} = S_q$ (sources and sinks from evaporation, condensation, precipitation)
5. **Equation of state**: $p = \rho R_d T_v$

Most global models use the **hydrostatic** approximation for vertical motion; convection-permitting models are **non-hydrostatic** because vertical accelerations in storms matter.

### Discretisation and time step

The domain is divided into grid cells (horizontal spacing $\Delta x$, many vertical levels). For explicit schemes the **CFL condition** limits the time step:

$$\Delta t \le C\,\frac{\Delta x}{c_{max}}$$

where $c_{max}$ is the fastest signal speed and $C \lesssim 1$. Halving $\Delta x$ requires roughly halving $\Delta t$ too, so doubling horizontal resolution costs about **8×** more computation (2 × 2 horizontally × 2 in time), more with extra vertical levels.

### Effective resolution

A model cannot represent features near its grid spacing. The **effective resolution** is typically **4–7 × Δx**. A 9 km model resolves features of roughly 40–60 km. This is why global models cannot place individual thunderstorms.

## 7.2 Data assimilation (the starting point)

The initial state is estimated by combining a short previous forecast (the **background**, $\mathbf{x}_b$) with new observations ($\mathbf{y}$), weighted by their error covariances. The 3D-Var/4D-Var cost function:

$$J(\mathbf{x}) = \tfrac12(\mathbf{x} - \mathbf{x}_b)^T\mathbf{B}^{-1}(\mathbf{x} - \mathbf{x}_b) + \tfrac12(\mathbf{y} - H(\mathbf{x}))^T\mathbf{R}^{-1}(\mathbf{y} - H(\mathbf{x}))$$

- $\mathbf B$: background error covariance; $\mathbf R$: observation error covariance; $H$: observation operator mapping model state to observed quantities.
- The minimising $\mathbf x$ is the **analysis**. 4D-Var does this over a time window using the model dynamics; ensemble Kalman filters estimate $\mathbf B$ from an ensemble.

The scalar intuition: combining two estimates with error variances $\sigma_b^2$ and $\sigma_o^2$,

$$x_a = x_b + K(y - x_b), \qquad K = \frac{\sigma_b^2}{\sigma_b^2 + \sigma_o^2}, \qquad \sigma_a^2 = (1 - K)\sigma_b^2$$

The analysis is always more certain than either input. The same formula is useful in agents when combining a model forecast with a fresh observation.

**Tropical challenge:** there are fewer conventional observations over oceans, and the weak link between pressure and wind near the equator means mass observations constrain winds poorly. Tropical analyses are less accurate than mid-latitude ones.

## 7.3 Parameterisation

Processes smaller than the grid or too complex to resolve are represented by simplified schemes:

| Process | Why parameterised |
| --- | --- |
| **Deep convection** | Updrafts are 1–10 km wide; unresolved below ~4 km grid spacing |
| Cloud microphysics | Droplets and ice particles are microscopic |
| Radiation | Full line-by-line radiative transfer is too expensive |
| Boundary layer turbulence | Eddies are metres to hundreds of metres |
| Land surface, urban, ocean coupling | Surface heterogeneity |

**Convection schemes** are the largest source of tropical forecast error. Typical problems:
- Rain starts too early in the day (often around noon instead of mid-afternoon) and is too light and widespread ("drizzle problem").
- The diurnal cycle over land and coasts is poorly timed.
- Organised systems (squall lines) are poorly represented.

**Convection-permitting models** ($\Delta x \lesssim 4$ km, often 1.5–3 km) switch off the deep convection scheme and simulate storms explicitly. They produce realistic-looking storms with a better diurnal cycle, but individual cells are often misplaced by tens of km or mistimed by an hour or more. **Their output should be used probabilistically** (neighbourhood methods, ensembles), not taken literally at a point.

## 7.4 Models relevant to Southeast Asia

| Model | Operator | Type | Approx. grid | Notes |
| --- | --- | --- | --- | --- |
| IFS HRES | ECMWF | Global deterministic | 9 km | Usually the most accurate global model |
| IFS ENS | ECMWF | Global ensemble, 51 members | 9 km (since 2023) | Key source for probabilities |
| AIFS | ECMWF | Global AI model | ~0.25° | Operational since 2025 (**verify** status); ensemble version also run |
| GFS | NOAA (US) | Global deterministic | ~13 km | Free and open |
| GEFS | NOAA | Global ensemble, 31 members | ~25 km | Free and open |
| ICON | DWD (Germany) | Global | ~13 km | Global ensemble also available |
| UM global | UK Met Office | Global | ~10 km | |
| SINGV | MSS (Singapore) | Regional convection-permitting | ~1.5 km over Singapore (**verify**) | Built with the UK Met Office from the Unified Model; tuned for the region |

Open data access: ECMWF publishes a subset of HRES/ENS/AIFS output openly (0.25°); NOAA publishes GFS/GEFS openly; Open-Meteo aggregates many models behind one API (chapter 16).

**Run cycles and latency.** Global models run 2–4 times daily (00, 06, 12, 18 UTC). Output arrives several hours after the nominal time. Always record the **initialisation time** and the **valid time**; lead time = valid − init.

## 7.5 AI weather models

Machine-learning models trained on decades of reanalysis (mostly ERA5) that produce forecasts much faster than physics models.

| Model | Developer | Notes |
| --- | --- | --- |
| GraphCast | Google DeepMind | Graph neural network, 0.25°, 6-hour steps, 10 days; beat HRES on many upper-air scores |
| GenCast | Google DeepMind | Diffusion-based **ensemble** model; strong probabilistic skill |
| Pangu-Weather | Huawei | 3-D transformer |
| FourCastNet | NVIDIA | Fourier neural operator |
| Aurora | Microsoft | Foundation model, fine-tuned for weather and air quality |
| AIFS | ECMWF | Operational AI model at ECMWF |

**Strengths:** large-scale patterns (pressure, winds, temperature, tropical cyclone tracks) at 1–10 days; very cheap to run, enabling large ensembles.

**Weaknesses relevant to Singapore:**
- Trained at ~0.25° (~28 km), so they cannot represent individual tropical storms.
- Deterministic AI models trained to minimise mean squared error produce **smooth** fields: they underpredict extremes and intense rain.
- Precipitation is often weaker than physical variables; some models do not output it at all.
- Still initialised from physics-based analyses.

**Practical stance:** treat AI models as additional ensemble members or as large-scale guidance (surges, MJO, wind regimes), not as point rainfall forecasts. Verify them like any other source (chapter 12).

## 7.6 Reanalysis

A reanalysis runs one fixed modern assimilation system over past decades to produce a consistent historical record. **ERA5** (ECMWF): hourly, 0.25°, 1940–present. Uses: climatology baselines, training statistical models, and "model climate" for anomaly detection. Limitations: rainfall is a model product, not an observation, and is biased in convective regions.

## 7.7 Reading model output correctly

- **Accumulated vs instantaneous**: rainfall is usually accumulated since initialisation or over the previous output interval; temperature is instantaneous. Differencing accumulated fields gives interval totals: $P_{t_1\to t_2} = A(t_2) - A(t_1)$.
- **Units**: model precipitation is often in metres (ECMWF) or kg m⁻² (= mm). Convert explicitly.
- **Grid vs point**: a grid value is an area average (chapter 05). Do not compare it directly with a single gauge without accounting for this.
- **Spin-up**: the first few hours of a run may be unbalanced, especially for rain. Convection-permitting models often need a few hours before storms look realistic.
- **Time zone**: model times are UTC. Singapore afternoon (14:00–18:00 SGT) is 06:00–10:00 UTC.
- **Land–sea mask**: Singapore is small; coarse models may treat its grid cell as partly or entirely sea, distorting temperature and the diurnal cycle. Prefer the nearest land grid point, or a convection-permitting model.
