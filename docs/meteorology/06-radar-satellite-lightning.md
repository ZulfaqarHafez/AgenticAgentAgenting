# 06. Radar, satellite and lightning

The remote-sensing tools that dominate short-range forecasting in the tropics.

## 6.1 Weather radar fundamentals

A radar sends microwave pulses and measures the power scattered back by raindrops, hail and other targets.

### Range and geometry

Range from echo delay: $r = \dfrac{c\,\Delta t}{2}$.

The beam rises with distance (Earth curvature plus beam elevation). With standard refraction (effective Earth radius $k_e R_E$, $k_e = 4/3$), beam centre height above the radar:

$$h = \sqrt{r^2 + (k_e R_E)^2 + 2 r k_e R_E \sin\theta_e} - k_e R_E + h_0$$

At 100 km and 0.5° elevation the beam centre is about 1.5 km up. At long range the radar overshoots shallow rain, so rain far from the radar is under-detected.

### Reflectivity

The radar reflectivity factor depends on drop diameter to the sixth power:

$$Z = \sum_i N_i D_i^6 \quad (\text{mm}^6\,\text{m}^{-3}), \qquad dBZ = 10\log_{10} Z$$

Because of the $D^6$ dependence, a few large drops dominate the signal.

| dBZ | Typical meaning |
| --- | --- |
| < 20 | Drizzle, cloud, or noise |
| 20–35 | Light to moderate rain |
| 35–45 | Moderate to heavy rain |
| 45–55 | Very heavy rain, thunderstorm cores |
| > 55 | Possible hail (rare at Singapore's surface) or extremely heavy rain |

### Z–R relationships (reflectivity to rain rate)

Rain rate $R$ (mm/h) is estimated by a power law $Z = a R^b$, so:

$$R = \left(\frac{Z}{a}\right)^{1/b} = \left(\frac{10^{dBZ/10}}{a}\right)^{1/b}$$

| Relation | $a$ | $b$ | Use |
| --- | --- | --- | --- |
| Marshall–Palmer | 200 | 1.6 | Stratiform rain, general default |
| WSR-88D convective | 300 | 1.4 | Mid-latitude convection |
| Rosenfeld tropical | 250 | 1.2 | Tropical convective rain |

**Worked example.** Rain rate implied by different dBZ values:

| dBZ | Marshall–Palmer (mm/h) | Convective 300/1.4 (mm/h) | Tropical 250/1.2 (mm/h) |
| --- | --- | --- | --- |
| 30 | 2.7 | 2.4 | 3.2 |
| 40 | 11.5 | 12.2 | 21.6 |
| 50 | 48.6 | 63.4 | 147 |

The choice of relation changes the estimated rain rate by **2–3× at high reflectivity**. Tropical rain has many small drops, so for the same Z it produces more rain than Marshall–Palmer suggests. Always calibrate against local gauges, and cap reflectivity (commonly at 53–55 dBZ) to avoid hail contamination giving absurd rates.

### Radar error sources

- **Attenuation**: heavy rain absorbs the signal, especially at C- and X-band, so storms behind other storms look weaker.
- **Beam blockage** by terrain and buildings.
- **Ground clutter and sea clutter**; anomalous propagation in strong inversions.
- **Bright band**: melting snow just below the freezing level (≈ 4.5–5 km in the tropics) appears much stronger than the rain it becomes.
- **Overshooting** at long range.
- **Z–R uncertainty**, as above.

### Dual polarisation

Modern radars transmit horizontal and vertical pulses. Extra variables:
- **ZDR** (differential reflectivity): drop shape, larger flattened drops give higher ZDR.
- **KDP** (specific differential phase): accurate for heavy rain and immune to attenuation. $R \approx 40.5\,K_{DP}^{0.85}$ (S-band, approximate; coefficients vary with wavelength).
- **ρHV** (correlation coefficient): separates rain from non-meteorological targets.

### Radar products agents may use

- **CAPPI**: reflectivity at a constant altitude.
- **Composite (column maximum) reflectivity**: strongest echo in each column.
- **Echo tops**: highest altitude with reflectivity above a threshold (e.g. 18 dBZ); tall tops mean deep convection.
- **Accumulated rainfall** over 1 h, 3 h, 24 h.
- **Motion vectors** for nowcasting (chapter 10).

## 6.2 Satellite meteorology

### Geostationary vs polar-orbiting

- **Geostationary** (≈ 35,786 km altitude, fixed over the equator): continuous view of the same area. Himawari-9 (Japan, 140.7°E) covers Southeast Asia, with full-disk images every 10 minutes at 0.5–2 km resolution.
- **Polar-orbiting**: higher resolution and sounding instruments, but each place is seen only a few times per day.

### Himawari AHI channels (selected)

| Band | Wavelength (µm) | Resolution | Use |
| --- | --- | --- | --- |
| 3 | 0.64 (visible) | 0.5 km | Cloud texture, daytime only |
| 7 | 3.9 | 2 km | Fog, fire hotspots (haze sources), night low cloud |
| 8 | 6.2 (water vapour) | 2 km | Upper-tropospheric moisture |
| 10 | 7.3 (water vapour) | 2 km | Mid-level moisture |
| 13 | 10.4 (clean IR window) | 2 km | Cloud-top temperature, day and night |
| 15 | 12.4 | 2 km | Split-window with band 13 (thin cirrus, dust) |

### Brightness temperature

Satellites measure radiance $L_\lambda$. Converting to brightness temperature (the temperature of a black body emitting that radiance) inverts the Planck function:

$$B_\lambda(T) = \frac{2hc^2}{\lambda^5}\frac{1}{e^{hc/(\lambda k_B T)} - 1} \quad\Rightarrow\quad T_B = \frac{hc}{\lambda k_B}\left[\ln\!\left(1 + \frac{2hc^2}{\lambda^5 L_\lambda}\right)\right]^{-1}$$

Data providers usually supply brightness temperature directly.

### Interpreting infrared cloud-top temperature

Cloud tops cool with height (roughly following the environmental lapse rate), so cold tops mean tall clouds:

| Band 13 $T_B$ | Meaning (tropics) |
| --- | --- |
| > 280 K (> 7 °C) | Clear sky or low cloud |
| 250–280 K | Mid-level cloud |
| 230–250 K | Developing cumulonimbus or thick mid/high cloud |
| < 220 K (< −53 °C) | Deep convection; heavy rain likely beneath |
| < 200 K (< −73 °C) | Very intense convection; overshooting tops |

Caveat: thin cirrus can be cold without rain below. Combining channels helps:
- **Band 13 minus band 15** (split window): large positive differences indicate thin cirrus rather than thick cloud.
- **Band 8 (6.2 µm) minus band 13**: near zero or positive values indicate tops reaching or overshooting the tropopause.

### Cloud-top cooling rate

Rapid cooling of tops signals a growing storm, often 15–45 minutes before heavy rain or lightning. Compute per pixel or per tracked cloud object:

$$\frac{\Delta T_B}{\Delta t} = \frac{T_B(t) - T_B(t - 10\,\text{min})}{10\,\text{min}}$$

Cooling of several K per 10–15 minutes in cumulus that are not yet glaciated is a common convective-initiation signal. Tracking needs cloud-object matching between frames (motion compensation), otherwise advection is mistaken for cooling.

### Satellite rainfall estimates

- **GPM IMERG** (NASA): merged microwave and IR precipitation, 0.1°, 30-minute. Early run available within hours. Good for the region and the ocean, less accurate for point totals.
- **GSMaP** (JAXA): similar, near real time.

### Fire hotspots and haze

The 3.9 µm channel detects fires. Hotspot counts over Sumatra and Kalimantan, combined with wind trajectories toward Singapore, are the basis for haze outlooks (chapter 15).

## 6.3 Lightning

### Detection

- **Ground-based networks** detect radio emissions and locate strokes by time of arrival. Detection efficiency and location accuracy vary (hundreds of metres to a few km).
- **Cloud-to-ground (CG)** vs **intra-cloud (IC)** lightning. IC usually increases first in a developing storm.
- Geostationary lightning imagers (on some satellites) detect total lightning optically; Himawari-9 does not carry one.

### Distance from thunder (flash-to-bang)

Sound travels at about 343 m/s (at 20 °C), light effectively instantly:

$$d \approx 0.343\,\Delta t\ \text{km} \approx \frac{\Delta t}{3}\ \text{km}$$

A 30-second gap means the strike was about 10 km away, within striking range.

### Lightning as a nowcasting signal

- A **lightning jump** (sudden increase in total flash rate) often precedes intense rain, strong gusts or hail by 10–30 minutes. A common algorithm (the "2σ" method): compute the flash rate trend $DFRDT = \Delta(\text{flash rate})/\Delta t$ over recent intervals; flag a jump when the latest $DFRDT$ exceeds twice the standard deviation of the previous ~10 minutes of $DFRDT$ (with a minimum flash rate threshold).
- First lightning in a cell marks electrification and the start of a hazard window for outdoor activity.
- **Lightning density** (flashes per km² per year) from climatology helps calibrate risk; Singapore's is high by global standards.

### Lightning safety logic

- **30-30 rule** (traditional): seek shelter if flash-to-bang ≤ 30 s; wait 30 minutes after the last thunder before resuming. Many organisations now simplify to "When thunder roars, go indoors."
- Detection-based alerting: alert when strikes occur within a radius (e.g. 8–15 km) of a site, and clear the alert after a quiet period (e.g. 15–30 minutes with no strikes within the radius).
