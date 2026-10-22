# 10. Nowcasting

Forecasting the next 0–6 hours. In the tropics, where storms form and decay quickly and models misplace them, nowcasting provides most of the actionable warning for rain, lightning and gusts.

## 10.1 Principle: extrapolation (Lagrangian persistence)

Assume the current rain field keeps moving with its recent motion and keeps its intensity:

$$R(\mathbf x, t_0 + \Delta t) = R(\mathbf x - \mathbf u\,\Delta t,\ t_0)$$

where $\mathbf u$ is the motion field. This is called **Lagrangian persistence**. It beats NWP for the first 1–2 hours for existing storms, but cannot predict **new** storms (initiation) or **decay**.

Typical skill: for tropical convection, extrapolation skill falls off quickly, often within 30–90 minutes, because cells live only 30–60 minutes. Larger organised systems (squall lines, monsoon rain bands) stay predictable for longer.

## 10.2 Estimating motion

### Cross-correlation (block matching)

Divide the radar image into blocks. For each block, find the displacement $(\Delta x, \Delta y)$ that maximises correlation with the next image:

$$\rho(\Delta x, \Delta y) = \frac{\sum (R_1 - \bar R_1)(R_2^{shift} - \bar R_2)}{\sqrt{\sum (R_1 - \bar R_1)^2 \sum (R_2^{shift} - \bar R_2)^2}}$$

Velocity = displacement / time between images. Smooth the resulting vector field.

### Optical flow

Assumes brightness (rain intensity) is conserved along motion:

$$\frac{\partial R}{\partial t} + u\frac{\partial R}{\partial x} + v\frac{\partial R}{\partial y} = 0$$

One equation, two unknowns per pixel, so a smoothness constraint is added (Horn–Schunck) or local windows are used (Lucas–Kanade). Variational echo tracking (VET) minimises the conservation residual plus a smoothness penalty over the whole field.

Open-source implementations: **pySTEPS** (Python), which includes Lucas–Kanade, VET, DARTS and the extrapolation and probabilistic schemes below.

### Cell (object) tracking

Identify storm cells as connected regions above a threshold (e.g. 35–40 dBZ), match them between frames by overlap or distance, and track centroid, area, maximum intensity and their trends. Gives per-storm attributes: "cell moving south-west at 25 km/h, intensifying."

Centroid velocity: $\mathbf u = (\mathbf c_t - \mathbf c_{t-1}) / \Delta t$.

## 10.3 Estimated time of arrival

For a storm edge at distance $d$ from a site, moving with speed $|\mathbf u|$ at angle $\alpha$ between the motion vector and the line from storm to site:

$$t_{arrival} \approx \frac{d}{|\mathbf u|\cos\alpha}\quad(\text{only if}\ \cos\alpha > 0)$$

Example: storm edge 15 km away moving at 20 km/h directly toward the site: arrival in about 45 minutes. Give it as a window (for example 30–60 minutes), because speed and direction change and storms grow or decay en route.

Check whether the site falls within the storm's swath: the perpendicular distance from the site to the storm's track line should be less than about half the storm width plus a margin.

## 10.4 Probabilistic nowcasting

Pure extrapolation is overconfident. Approaches:

- **Spatial smoothing with lead time**: blur the extrapolated field more as lead time increases (small features lose predictability first).
- **Scale decomposition (STEPS)**: split the rain field into spatial scales (cascade); each scale's predictability decays at its own rate (modelled as an autoregressive process), with stochastic noise added to generate an ensemble of nowcasts.
- **Neighbourhood probabilities**: the probability that rain exceeds a threshold within radius $r$, where $r$ grows with lead time.
- **Machine-learning nowcasting** (for example DeepMind's DGMR, Google's MetNet family): learn growth and decay from data; can extend skill beyond pure extrapolation, but need large training data and careful verification for tropical regimes.

## 10.5 Convective initiation (new storms)

Extrapolation cannot see storms that do not exist yet. Signals that new storms are forming:

| Signal | Source | Lead time (typical) |
| --- | --- | --- |
| Growing cumulus, cooling cloud tops | Satellite IR (band 13), cooling rate (chapter 06) | 15–45 min |
| Boundary collisions (sea breezes, outflows) | Radar fine lines, surface wind shifts | 15–60 min |
| Rising low-level $\theta_e$, high afternoon CAPE | Stations, models | Hours (potential only) |
| First radar echoes aloft (before rain reaches ground) | Radar | 10–20 min |
| First lightning | Lightning network | 0–10 min (storm already mature) |

**Diurnal climatology** is an essential prior, but it must be measured, not assumed: in the 2024–25 gauge sample, rain peaked around 17:00–18:00 SGT in December and April, around 11:00 in July (Sumatra squall season), and had no afternoon peak in October (chapter 19).

## 10.6 Blending nowcasts with NWP

Extrapolation is best at short lead times; NWP becomes better later. A simple lead-time-dependent blend:

$$f_{blend}(t) = \alpha(t)\,f_{nowcast}(t) + (1 - \alpha(t))\,f_{NWP}(t)$$

with $\alpha$ falling from 1 at $t = 0$ to 0 at the crossover time $t_c$. Common shapes: linear, $\alpha(t) = \max(0, 1 - t/t_c)$; or exponential, $\alpha(t) = e^{-t/\tau}$. Choose $t_c$ or $\tau$ from verification: the lead time where the nowcast's skill drops below the NWP's (often 1–3 hours for tropical convection).

Better: blend scale by scale (STEPS-style), so large scales transition to NWP later than small ones.

## 10.7 Nowcast output for agents

For a site and the next 0–3 hours, provide:
- Probability of rain ≥ 1 mm and ≥ 10 mm/h in 15–30 minute windows.
- Estimated time of arrival window and expected duration.
- Peak intensity category (light, moderate, heavy, very heavy).
- Lightning risk (strikes within the alert radius now; trend).
- Confidence level and the main reason (for example "storm well established and tracked" vs "new development possible").

Update every radar cycle (5–10 minutes). Record each nowcast for verification (chapter 12).
