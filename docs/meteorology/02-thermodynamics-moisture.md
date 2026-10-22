# 02. Thermodynamics and moisture

The state variables of air and how to convert between them. Almost every downstream calculation (stability, heat stress, cloud base) starts here.

## 2.1 Equation of state

Dry air behaves as an ideal gas:

$$p = \rho R_d T$$

Moist air is handled with the **virtual temperature** $T_v$: the temperature dry air would need to have the same density as the moist air. Water vapour is lighter than dry air, so $T_v > T$.

$$p = \rho R_d T_v, \qquad T_v \approx T\,(1 + 0.608\,q)$$

| Symbol | Meaning | Value |
| --- | --- | --- |
| $R_d$ | Gas constant, dry air | 287.05 J kg⁻¹ K⁻¹ |
| $R_v$ | Gas constant, water vapour | 461.5 J kg⁻¹ K⁻¹ |
| $\varepsilon = R_d/R_v$ | Ratio | 0.622 |
| $c_p$ | Specific heat of dry air at constant pressure | 1004 J kg⁻¹ K⁻¹ |
| $L_v$ | Latent heat of vaporisation (at 0 °C) | 2.501 × 10⁶ J kg⁻¹ |
| $g$ | Gravity | 9.80665 m s⁻² |

## 2.2 Hydrostatic balance and height

For large-scale motion, vertical pressure gradient balances gravity:

$$\frac{\partial p}{\partial z} = -\rho g$$

Integrating with the gas law gives the **hypsometric equation**, the thickness between two pressure levels:

$$\Delta z = z_2 - z_1 = \frac{R_d \bar{T}_v}{g} \ln\frac{p_1}{p_2}$$

Warmer columns are thicker. **Worked example:** the 1000–500 hPa thickness with a layer-mean $\bar T_v = 288\,\text{K}$ (typical of the tropics):

$$\Delta z = \frac{287.05 \times 288}{9.80665}\ln 2 \approx 5843\ \text{m}$$

With $\bar T_v = 283\,\text{K}$ it is ≈ 5742 m. A 5 K warmer column is ≈ 100 m thicker.

The **scale height** $H = R_d T / g \approx 8\ \text{km}$ is the height over which pressure falls by a factor of $e$ in an isothermal atmosphere: $p(z) = p_0 e^{-z/H}$.

## 2.3 Humidity variables

Water vapour can be expressed many ways. Agents must convert consistently.

### Saturation vapour pressure

The vapour pressure at which air is saturated over liquid water. The Bolton (1980) form of the Magnus equation, accurate to about 0.1% for −30 to 35 °C:

$$e_s(T) = 6.112 \exp\!\left(\frac{17.67\,T}{T + 243.5}\right)\ \text{hPa}, \quad T\ \text{in °C}$$

Roughly, $e_s$ doubles for every 10 °C of warming. This is the **Clausius–Clapeyron** relation: about 7% more water-holding capacity per °C. It is why tropical air holds so much water and why warming increases rainfall intensity.

### Vapour pressure, dewpoint and relative humidity

- Actual vapour pressure: $e = e_s(T_d)$, where $T_d$ is the **dewpoint**, the temperature to which air must be cooled at constant pressure to saturate.
- **Relative humidity:** $RH = 100\,\dfrac{e}{e_s(T)}\ \%$
- **Dewpoint from T and RH** (inverting Magnus):

$$\gamma = \ln\!\left(\frac{RH}{100}\right) + \frac{17.67\,T}{T+243.5}, \qquad T_d = \frac{243.5\,\gamma}{17.67 - \gamma}$$

- **Dewpoint depression** $T - T_d$: small values (< 3 °C) mean near-saturated air, low cloud bases.

### Mixing ratio and specific humidity

- **Mixing ratio** (mass of vapour per mass of dry air): $r = \varepsilon \dfrac{e}{p - e}$
- **Specific humidity** (mass of vapour per mass of moist air): $q = \dfrac{\varepsilon e}{p - (1-\varepsilon) e} \approx \dfrac{r}{1+r}$
- Both are often quoted in g/kg. Tropical boundary-layer values are 16–22 g/kg.

### Absolute humidity

$\rho_v = \dfrac{e}{R_v T}$ (kg m⁻³), with $e$ in Pa and $T$ in K.

### Worked example (running case)

$T = 32\,°\text{C}$, $RH = 70\%$, $p = 1008\,\text{hPa}$:

| Quantity | Calculation | Result |
| --- | --- | --- |
| $e_s$ | $6.112\exp(17.67 \cdot 32 / 275.5)$ | 47.6 hPa |
| $e$ | $0.70 \times 47.6$ | 33.3 hPa |
| $T_d$ | Magnus inverse | 25.9 °C |
| $r$ | $0.622 \times 33.3 / (1008 - 33.3)$ | 21.3 g/kg |
| $q$ | $0.622 \times 33.3 / (1008 - 0.378 \times 33.3)$ | 20.8 g/kg |
| $T_v$ | $305.15\,(1 + 0.608 \times 0.0208)$ | 309.0 K |

## 2.4 Potential temperature and lapse rates

### Potential temperature

The temperature a parcel would have if brought adiabatically (no heat exchange) to 1000 hPa. It is conserved in dry adiabatic motion, so it labels air masses:

$$\theta = T\left(\frac{p_0}{p}\right)^{R_d/c_p}, \qquad p_0 = 1000\ \text{hPa},\ R_d/c_p \approx 0.2857$$

Running case: $\theta = 305.15 \times (1000/1008)^{0.2857} = 304.5\ \text{K}$.

### Equivalent potential temperature

$\theta_e$ also includes the latent heat the parcel would release if all its vapour condensed. It is conserved in both dry and moist adiabatic motion, so it is the best single measure of how much energy a low-level parcel carries. High $\theta_e$ near the surface under lower $\theta_e$ aloft means potential instability.

Bolton (1980), eq. 43 (with $r$ in kg/kg, $T_L$ the temperature at the lifting condensation level):

$$T_L = \frac{1}{\dfrac{1}{T_d - 56} + \dfrac{\ln(T/T_d)}{800}} + 56 \quad (\text{K})$$

$$\theta_e = T\left(\frac{1000}{p}\right)^{0.2854(1 - 0.28 r)} \exp\!\left[\left(\frac{3.376}{T_L} - 0.00254\right) 1000\,r\,(1 + 0.81 r)\right]$$

Running case: $T_L = 297.5\ \text{K}$, $\theta_e \approx 368\ \text{K}$. Tropical boundary-layer $\theta_e$ of 350–370 K is typical; values above ~355 K under a dry mid-troposphere favour strong convection.

A cruder approximation, useful for intuition: $\theta_e \approx \theta \exp\!\left(\dfrac{L_v r}{c_p T_L}\right)$.

### Lapse rates

The rate temperature falls with height, $\Gamma = -\partial T/\partial z$.

| Lapse rate | Value | Meaning |
| --- | --- | --- |
| Dry adiabatic $\Gamma_d = g/c_p$ | 9.8 K/km | Unsaturated parcel cooling as it rises |
| Moist (saturated) adiabatic $\Gamma_m$ | ≈ 4 K/km in warm tropical air, rising to ≈ 6–7 K/km in cold air | Saturated parcel; condensation releases heat |
| Standard atmosphere | 6.5 K/km | Reference average, used for height corrections |

Stability depends on the environment's lapse rate $\Gamma_e$:
- $\Gamma_e < \Gamma_m$: **absolutely stable**
- $\Gamma_m < \Gamma_e < \Gamma_d$: **conditionally unstable** (unstable only if saturated). The tropical troposphere is usually here.
- $\Gamma_e > \Gamma_d$: **absolutely unstable** (only in a shallow layer near hot ground)

### Lifting condensation level (cloud base)

Height where a rising parcel saturates. Espy's approximation:

$$z_{LCL} \approx 125\,(T - T_d)\ \text{m}$$

Running case: $125 \times (32 - 25.9) \approx 770\ \text{m}$. Afternoon cumulus bases over Singapore are commonly 600–1000 m.

## 2.5 Wet-bulb temperature

The lowest temperature reachable by evaporating water into the air. It drives heat stress. Stull (2011) empirical formula (T in °C, RH in %, valid for RH 5–99% and T −20 to 50 °C at sea-level pressure, error within about ±1 °C):

$$T_w = T\arctan\!\big[0.151977\,(RH + 8.313659)^{1/2}\big] + \arctan(T + RH) - \arctan(RH - 1.676331) + 0.00391838\,RH^{3/2}\arctan(0.023101\,RH) - 4.686035$$

(arctan in radians.) Running case: $T_w \approx 27.5\ °\text{C}$.

For exact values, solve the psychrometric equation iteratively: $e = e_s(T_w) - \gamma_p\,p\,(T - T_w)$ with psychrometer constant $\gamma_p \approx 6.6 \times 10^{-4}\ \text{K}^{-1}$.

## 2.6 Heat stress indices

### Heat index (apparent temperature)

US NWS Rothfusz regression, with $T$ in °F and $RH$ in %:

$$
\begin{aligned}
HI = {}& -42.379 + 2.04901523\,T + 10.14333127\,RH - 0.22475541\,T\,RH - 0.00683783\,T^2 \\
& - 0.05481717\,RH^2 + 0.00122874\,T^2 RH + 0.00085282\,T\,RH^2 - 0.00000199\,T^2 RH^2
\end{aligned}
$$

Valid when $HI \gtrsim 80\,°\text{F}$; NWS applies small adjustments at very low or very high RH. Running case: $T = 89.6\,°\text{F}$ gives $HI \approx 104.7\,°\text{F} \approx 40.4\,°\text{C}$.

### Wet Bulb Globe Temperature (WBGT)

The occupational heat-stress standard, and the index Singapore's NEA uses for its heat stress advisories (chapter 15):

$$WBGT_{outdoor} = 0.7\,T_{nw} + 0.2\,T_g + 0.1\,T_a$$

$$WBGT_{indoor} = 0.7\,T_{nw} + 0.3\,T_g$$

- $T_{nw}$: natural wet-bulb temperature (wet wick exposed to sun and wind, not the psychrometric $T_w$)
- $T_g$: black globe temperature (captures radiant heat)
- $T_a$: air temperature

WBGT needs radiation and wind information; it cannot be computed from T and RH alone. Use observed WBGT where available (NEA publishes it), or a physically based model such as Liljegren et al. (2008).

## 2.7 Density and pressure corrections

- **Station pressure to sea-level pressure** (small heights): $p_{msl} \approx p_{stn}\exp\!\left(\dfrac{g\,z}{R_d \bar{T}_v}\right)$
- **Temperature height correction** when using model grid temperatures at a site of different elevation: $T_{site} = T_{model} + \Gamma\,(z_{model} - z_{site})$ with $\Gamma = 6.5\ \text{K/km}$. Singapore is low-lying (highest point ≈ 164 m), so this matters little locally but a lot in mountainous regions.
