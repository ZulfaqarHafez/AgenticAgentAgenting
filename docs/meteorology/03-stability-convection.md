# 03. Stability and convection

Thunderstorms produce most of Singapore's heavy rain, lightning and gusts. Whether they form depends on three **ingredients**:

1. **Moisture**: enough water vapour in the lower and middle troposphere.
2. **Instability**: rising air stays warmer (more buoyant) than its surroundings.
3. **Lift**: something forces air upward to start it off (surface heating, sea-breeze convergence, gust fronts from earlier storms, terrain, larger-scale convergence).

A fourth factor, **vertical wind shear**, controls how organised storms become (single cells vs lines vs long-lived systems).

## 3.1 Parcel theory

Imagine a small parcel of surface air lifted without mixing:

1. It cools at the dry adiabatic rate (9.8 K/km) until it saturates at the **LCL** (cloud base).
2. Above the LCL it cools at the slower moist adiabatic rate, because condensation releases latent heat.
3. If it becomes warmer than the environment, it is buoyant and accelerates upward from the **level of free convection (LFC)**.
4. It stays buoyant until the **equilibrium level (EL)**, near the cloud top (often 13–16 km in the tropics).

The environment's temperature profile comes from a **sounding** (radiosonde, or a model profile).

## 3.2 Buoyancy, CAPE and CIN

Buoyant acceleration of a parcel:

$$B = g\,\frac{T_{v,p} - T_{v,e}}{T_{v,e}}$$

where subscripts $p$ = parcel, $e$ = environment.

**Convective Available Potential Energy** (energy available to an updraft, J/kg):

$$\text{CAPE} = g \int_{z_{LFC}}^{z_{EL}} \frac{T_{v,p} - T_{v,e}}{T_{v,e}}\,dz$$

**Convective Inhibition** (energy needed to lift the parcel to its LFC):

$$\text{CIN} = -g \int_{z_{sfc}}^{z_{LFC}} \frac{T_{v,p} - T_{v,e}}{T_{v,e}}\,dz \quad (\text{over negatively buoyant layers})$$

Discretised for model or sonde levels $i$ (layer thickness $\Delta z_i$):

$$\text{CAPE} \approx g \sum_i \frac{T_{v,p,i} - T_{v,e,i}}{T_{v,e,i}}\,\Delta z_i \quad \text{for layers with positive buoyancy above the LFC}$$

**Parcel choices** matter and must be stated:
- **SBCAPE** (surface-based): parcel from the surface. Peaks in the afternoon.
- **MLCAPE** (mixed-layer): average of the lowest ~50–100 hPa. More robust.
- **MUCAPE** (most unstable): the parcel in the lowest ~300 hPa with highest $\theta_e$.

**Interpretation (tropical context).**

| CAPE (J/kg) | Meaning |
| --- | --- |
| < 500 | Weak instability |
| 500–1500 | Moderate; afternoon showers and storms likely if triggered |
| 1500–3000 | Strong; vigorous thunderstorms |
| > 3000 | Very strong |

Tropical CAPE is often 1000–3000 J/kg every afternoon, so CAPE alone does not discriminate storm days from non-storm days in Singapore. **Mid-level moisture, triggering and CIN** often matter more.

**Theoretical maximum updraft** (no drag, no entrainment, an overestimate by 2× or more):

$$w_{max} = \sqrt{2\,\text{CAPE}}$$

Example: CAPE = 2500 J/kg gives $w_{max} \approx 71\ \text{m/s}$; real tropical updrafts are typically 5–20 m/s, because entrainment of dry air and water loading reduce buoyancy.

## 3.3 Classic stability indices

Quick indices from standard pressure levels (temperatures in °C). They are cheap and easy for agents to compute from soundings or model output.

### Lifted Index

$$LI = T_{e,500} - T_{p,500}$$

Negative means the parcel is warmer than the environment at 500 hPa (unstable). LI < −3 favours storms; < −6 very unstable.

### Showalter Index

Like LI but lifting a parcel from 850 hPa. Values ≤ 0 indicate thunderstorm potential.

### K-index (good for tropical, moisture-driven convection)

$$K = (T_{850} - T_{500}) + T_{d,850} - (T_{700} - T_{d,700})$$

The first term measures the lapse rate, the second low-level moisture, the third mid-level dryness (a large $T_{700} - T_{d,700}$ reduces K).

| K | Thunderstorm likelihood (tropical guidance, approximate) |
| --- | --- |
| < 30 | Low |
| 30–35 | Moderate, scattered |
| 35–40 | High, numerous |
| > 40 | Very high, widespread heavy rain |

Thresholds are region-specific; calibrate them against local thunderstorm records (chapter 12).

**Worked example:** $T_{850} = 18$, $T_{d,850} = 16$, $T_{700} = 9$, $T_{d,700} = 6$, $T_{500} = -6$:

$$K = (18 - (-6)) + 16 - (9 - 6) = 24 + 16 - 3 = 37$$

### Total Totals

$$TT = T_{850} + T_{d,850} - 2\,T_{500}$$

Same example: $TT = 18 + 16 + 12 = 46$. Values above ~44 favour thunderstorms in mid-latitudes; tropical thresholds differ and must be calibrated.

## 3.4 Precipitable water

Total water vapour in a column, as the depth of liquid if it all condensed:

$$PW = \frac{1}{\rho_w g}\int_{p_{top}}^{p_{sfc}} q\,dp$$

With $q$ in kg/kg, $p$ in Pa and $\rho_w = 1000\ \text{kg m}^{-3}$, $PW$ comes out in metres; multiply by 1000 for mm. Equivalently $PW(\text{mm}) = \frac{1}{g}\int q\,dp$ because 1 kg m⁻² of water is 1 mm deep.

Discretised: $PW \approx \frac{1}{g}\sum_i \bar q_i\,\Delta p_i$.

Tropical PW is typically 45–65 mm; values above ~55–60 mm favour heavy rain. A sharp rise in PW is a signal of a moist surge or approaching disturbance.

## 3.5 Mid-level dryness and entrainment

Rising updrafts mix in (entrain) environmental air. Dry mid-levels (700–500 hPa relative humidity below ~50%) weaken updrafts by evaporative cooling, which suppresses deep convection. But once storms do form, dry mid-level air can strengthen downdrafts and surface gusts (through evaporative cooling of falling rain).

Useful diagnostics:
- $RH_{700-500}$ (layer mean relative humidity)
- $\theta_e$ difference between the surface and its minimum in mid-levels: $\Delta\theta_e = \theta_{e,sfc} - \theta_{e,min}$. Large values (> 20–25 K) indicate potential for strong evaporatively driven downdrafts and gusts.

## 3.6 Vertical wind shear and organisation

Bulk shear between two heights:

$$\Delta \vec V = \vec V(z_2) - \vec V(z_1), \qquad |\Delta \vec V| = \sqrt{(u_2 - u_1)^2 + (v_2 - v_1)^2}$$

| 0–6 km bulk shear | Typical storm mode |
| --- | --- |
| < 10 m/s | Short-lived single cells, pulse storms; outflows trigger new cells |
| 10–20 m/s | Multicell clusters, lines (e.g. squall lines) |
| > 20 m/s | Organised, long-lived systems (rare in deep tropics except with squall lines and monsoon surges) |

Singapore mostly sees weak shear (single and multicell storms). Sumatra squall lines are an exception: they organise along a low-level jet and a shallow layer of shear (chapter 14).

## 3.7 Triggers (lift)

- **Daytime heating**: the land surface heats, creating thermals; convection starts when the boundary layer reaches the LFC.
- **Sea and land breezes**: daytime sea breezes from different coasts converge inland, a major trigger over Singapore and the Malay Peninsula.
- **Gust fronts (outflow boundaries)**: cold air from earlier storms lifts warm air at its edge, triggering new cells. Collisions between outflows are favoured spots.
- **Terrain**: hills force ascent (more relevant over Sumatra and Peninsular Malaysia than Singapore).
- **Large-scale convergence**: monsoon surges, tropical waves, and MJO active phases.

## 3.8 Rain production

Approximate rainfall from a moisture budget. Over an area, rainfall rate is roughly moisture convergence plus surface evaporation minus change in storage:

$$P \approx -\frac{1}{g}\int \nabla\cdot(q\vec V)\,dp + E - \frac{\partial PW}{\partial t}$$

**Precipitation efficiency** (fraction of condensed water reaching the ground) is high (often 50–90%) in warm, moist tropical air, which is why tropical storms produce intense rain rates (50–150 mm/h in the heaviest cores).

## 3.9 What an agent should check (convection checklist)

1. Is there enough moisture? PW > ~50 mm, low-level $T_d$ > ~24 °C.
2. Is there instability? MLCAPE > ~1000 J/kg, LI < −3, K > 30 (calibrated locally).
3. Is the mid-level too dry or too moist? $RH_{700-500}$.
4. Is there a trigger? Time of day, sea-breeze convergence, outflows, approaching squall line or surge.
5. How organised could it get? 0–6 km shear.
6. What do convection-permitting models and radar trends say?

Ingredients define the **potential**; the trigger and radar define **whether and where**.
