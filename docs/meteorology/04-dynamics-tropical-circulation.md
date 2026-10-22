# 04. Dynamics and tropical circulation

Why winds blow, why mid-latitude forecasting rules break down near the equator, and the large-scale patterns that drive Southeast Asian weather.

## 4.1 The momentum equation (horizontal)

$$\frac{D\vec V_h}{Dt} = -\frac{1}{\rho}\nabla_h p - f\,\hat k \times \vec V_h + \vec F$$

The terms are acceleration, pressure-gradient force, Coriolis force and friction $\vec F$.

### Coriolis parameter

$$f = 2\Omega\sin\varphi, \qquad \Omega = 7.292 \times 10^{-5}\ \text{s}^{-1}$$

| Latitude | $f$ (s⁻¹) |
| --- | --- |
| 1.35° N (Singapore) | $3.4 \times 10^{-6}$ |
| 45° N | $1.03 \times 10^{-4}$ |

Coriolis at Singapore is about **30 times weaker** than at mid-latitudes, and zero at the equator.

## 4.2 Geostrophic balance, and why it fails near the equator

At mid-latitudes, large-scale flow is close to **geostrophic**: the pressure gradient balances Coriolis, so wind blows along isobars:

$$\vec V_g = \frac{1}{\rho f}\,\hat k \times \nabla_h p, \qquad u_g = -\frac{1}{\rho f}\frac{\partial p}{\partial y}, \quad v_g = \frac{1}{\rho f}\frac{\partial p}{\partial x}$$

The **Rossby number** measures how important Coriolis is relative to acceleration:

$$Ro = \frac{U}{f L}$$

Geostrophy holds when $Ro \ll 1$. For $U = 10\ \text{m/s}$ and $L = 1000\ \text{km}$:
- At 45°: $Ro \approx 0.1$ (geostrophic).
- At Singapore: $Ro \approx 3$ (**not** geostrophic).

**Consequences for agents:**
- Pressure charts are of limited use near the equator. Pressure gradients are tiny (a few hPa across the whole region), and wind is not tied to isobars.
- Tropical forecasters analyse **streamlines** (wind direction patterns), **convergence/divergence** and **moisture** rather than isobars and fronts.
- Fronts barely exist in the deep tropics. Do not import mid-latitude rules ("falling pressure means rain coming") without checking they hold locally. The **diurnal pressure tide** (twice-daily pressure oscillation of ~2–3 hPa, peaking near 10:00 and 22:00 local) dominates pressure changes in the tropics and must be removed before interpreting pressure tendencies.

## 4.3 Convergence, divergence and vertical motion

Mass continuity (incompressible approximation):

$$\frac{\partial u}{\partial x} + \frac{\partial v}{\partial y} + \frac{\partial w}{\partial z} = 0 \quad\Rightarrow\quad \frac{\partial w}{\partial z} = -\nabla_h\cdot\vec V_h$$

Low-level **convergence** ($\nabla_h\cdot\vec V_h < 0$) forces rising air. With convergence of $10^{-5}\ \text{s}^{-1}$ through a 1 km layer, $w \approx 1\ \text{cm/s}$ at the top of that layer. That is small but sustained over hours and enough to deepen moisture and trigger convection.

Divergence from gridded winds (finite differences, grid spacing $\Delta x, \Delta y$ in metres):

$$\nabla\cdot\vec V \approx \frac{u_{i+1,j} - u_{i-1,j}}{2\Delta x} + \frac{v_{i,j+1} - v_{i,j-1}}{2\Delta y}$$

On a latitude–longitude grid: $\Delta x = R_E\cos\varphi\,\Delta\lambda$, $\Delta y = R_E\,\Delta\varphi$ (radians), $R_E = 6.371 \times 10^6$ m.

**Vorticity** (spin), relevant for tropical disturbances:

$$\zeta = \frac{\partial v}{\partial x} - \frac{\partial u}{\partial y}$$

## 4.4 Local circulations

### Sea and land breezes

Daytime: land heats faster than sea, so a low-level onshore flow (sea breeze) develops, typically from late morning, 3–8 m/s, penetrating tens of km inland. Night: the reverse (land breeze), weaker.

Over Singapore and the Malay Peninsula, sea breezes from opposite coasts converge, giving afternoon convection over the interior. Over the Strait of Malacca and Sumatra, land breezes at night converge over the water, contributing to the nocturnal development of Sumatra squalls.

### Urban heat island

Dense urban areas stay warmer, especially at night (Singapore's urban–rural difference can reach several °C on calm, clear nights). Urban heating and roughness can enhance and shift afternoon convection.

## 4.5 Large-scale tropical circulation

### Hadley circulation and ITCZ

Air rises near the equator in the **Intertropical Convergence Zone (ITCZ)**, a band of convergence and convection, flows poleward aloft, sinks in the subtropics, and returns as trade winds. Over Southeast Asia the ITCZ concept merges with the monsoon trough, which migrates with the seasons.

### The Asian–Australian monsoon

A seasonal reversal of winds driven by land–sea heating contrasts:
- **Northeast (boreal winter) monsoon**: flow from the South China Sea, northeasterly over Singapore.
- **Southwest (boreal summer) monsoon**: southwesterly flow from the Indian Ocean across Sumatra.
- **Inter-monsoon periods**: light, variable winds; local heating and sea breezes dominate.

Details for Singapore are in chapter 14.

### Cold surges and monsoon surges

During the northeast monsoon, outbreaks of cold air from Siberia/China (**cold surges**) accelerate northeasterlies over the South China Sea. When they reach the equatorial region they increase low-level convergence and moisture, producing **monsoon surges**: prolonged, widespread rain over Singapore lasting one to several days, often with gusty winds and lower temperatures.

**Indicators agents can monitor:** pressure rise over southern China and the northern South China Sea, strengthening of 925–850 hPa northeasterlies over the southern South China Sea (an operational rule of thumb is sustained winds of order 10 m/s or more, **verify** against MSS definitions), and model forecasts of surges 3–7 days ahead.

### Borneo vortex

A cyclonic circulation near Borneo during the northeast monsoon that can interact with surges and shift rain away from or toward Singapore.

## 4.6 Intraseasonal and interannual variability

### Madden–Julian Oscillation (MJO)

An eastward-moving envelope of enhanced convection that circles the tropics in 30–60 days, travelling at about 5 m/s. When the active phase is over the Maritime Continent, rainfall over Singapore tends to be enhanced; when the suppressed phase is overhead, drier.

- **RMM index**: two principal components (RMM1, RMM2) from combined outgoing longwave radiation and 850/200 hPa winds. Amplitude $A = \sqrt{RMM1^2 + RMM2^2}$; $A > 1$ means an active MJO. The phase (1–8) is the angular sector of $(RMM1, RMM2)$. **Phases 4–5** correspond to enhanced convection over the Maritime Continent.
- The MJO is predictable 2–4 weeks ahead in good ensembles, which gives a basis for sub-seasonal outlooks.
- The Maritime Continent "barrier": the MJO often weakens crossing the islands because of the strong diurnal cycle over land.

### Equatorial waves

Kelvin waves (eastward, ~10–20 m/s), equatorial Rossby waves (westward) and mixed Rossby–gravity waves modulate convection over days to a week or two. They show up in filtered OLR and wind fields.

### ENSO (El Niño–Southern Oscillation)

- **El Niño** (warm central/eastern Pacific): the rising branch of the Walker circulation shifts east, so the Maritime Continent tends to be **drier and warmer**, especially June–October, with higher haze risk from fires.
- **La Niña**: tends to bring **wetter** conditions to the region.
- **Niño 3.4 index**: sea surface temperature anomaly in 5°N–5°S, 170°W–120°W. El Niño conventionally when the 3-month running mean (ONI) ≥ +0.5 °C for several consecutive overlapping seasons; La Niña when ≤ −0.5 °C.

### Indian Ocean Dipole (IOD)

The difference in sea surface temperature anomaly between the western (50°E–70°E, 10°S–10°N) and south-eastern (90°E–110°E, 10°S–0°) Indian Ocean (the Dipole Mode Index). A **positive IOD** (cooler south-east Indian Ocean) tends to reduce rainfall over Sumatra and Singapore in the southwest monsoon and late in the year, compounding El Niño dryness and haze risk.

## 4.7 Scale summary for agents

| Phenomenon | Space scale | Time scale | Main forecast source |
| --- | --- | --- | --- |
| Single thunderstorm | 1–10 km | 30–60 min | Radar nowcast |
| Sea-breeze convergence storms | 10–50 km | Hours (afternoon) | Climatology + convection-permitting NWP + radar |
| Sumatra squall line | 100–500 km long | 6–12 h | Satellite/radar tracking + NWP |
| Monsoon surge | 1000+ km | 1–5 days | Global NWP and ensembles |
| Tropical/equatorial waves | 1000s km | Days–2 weeks | Ensembles, filtered diagnostics |
| MJO | Planetary | 30–60 days | Extended-range ensembles, RMM |
| ENSO / IOD | Ocean basin | Months–years | Seasonal models and indices |
