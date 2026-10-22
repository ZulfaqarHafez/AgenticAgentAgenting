# 18. Constants, units and glossary

## 18.1 Physical constants

| Symbol | Name | Value |
| --- | --- | --- |
| $g$ | Standard gravity | 9.80665 m s⁻² |
| $R_d$ | Gas constant, dry air | 287.05 J kg⁻¹ K⁻¹ |
| $R_v$ | Gas constant, water vapour | 461.5 J kg⁻¹ K⁻¹ |
| $\varepsilon$ | $R_d/R_v$ | 0.622 |
| $c_p$ | Specific heat of dry air, constant pressure | 1004 J kg⁻¹ K⁻¹ |
| $c_v$ | Specific heat of dry air, constant volume | 717 J kg⁻¹ K⁻¹ |
| $\kappa$ | $R_d/c_p$ | 0.2857 |
| $L_v$ | Latent heat of vaporisation (0 °C) | 2.501 × 10⁶ J kg⁻¹ |
| $L_f$ | Latent heat of fusion | 3.34 × 10⁵ J kg⁻¹ |
| $\rho_w$ | Density of liquid water | 1000 kg m⁻³ |
| $\Omega$ | Earth's rotation rate | 7.292 × 10⁻⁵ s⁻¹ |
| $R_E$ | Mean Earth radius | 6.371 × 10⁶ m |
| $\sigma_{SB}$ | Stefan–Boltzmann constant | 5.670 × 10⁻⁸ W m⁻² K⁻⁴ |
| $c$ | Speed of light | 2.998 × 10⁸ m s⁻¹ |
| $h$ | Planck constant | 6.626 × 10⁻³⁴ J s |
| $k_B$ | Boltzmann constant | 1.381 × 10⁻²³ J K⁻¹ |
| $p_0$ | Reference pressure | 1000 hPa |
| — | Standard sea-level pressure | 1013.25 hPa |
| — | Standard lapse rate | 6.5 K km⁻¹ |
| — | Speed of sound (20 °C) | 343 m s⁻¹ |

## 18.2 Unit conversions

| From | To | Multiply by / formula |
| --- | --- | --- |
| °C | K | + 273.15 |
| °C | °F | × 1.8 + 32 |
| m/s | km/h | × 3.6 |
| m/s | knots | × 1.944 |
| knots | m/s | × 0.5144 |
| hPa | Pa | × 100 |
| inHg | hPa | × 33.864 |
| mm rain | kg m⁻² | × 1 |
| m (ECMWF precip) | mm | × 1000 |
| kg m⁻² s⁻¹ (precip rate) | mm/h | × 3600 |
| g/kg | kg/kg | × 0.001 |
| SGT | UTC | − 8 h |

## 18.3 Formula index

| Formula | Chapter |
| --- | --- |
| Ideal gas law, virtual temperature | 02 |
| Hypsometric equation, scale height | 02 |
| Saturation vapour pressure (Magnus/Bolton), dewpoint, RH, mixing ratio, specific humidity | 02 |
| Potential temperature, equivalent potential temperature (Bolton) | 02 |
| LCL height (Espy), lapse rates | 02 |
| Wet-bulb (Stull), heat index (Rothfusz), WBGT | 02 |
| Buoyancy, CAPE, CIN, $w_{max}$ | 03 |
| Lifted, Showalter, K-index, Total Totals | 03 |
| Precipitable water, bulk shear | 03 |
| Coriolis parameter, geostrophic wind, Rossby number | 04 |
| Continuity, divergence, vorticity | 04 |
| MJO RMM amplitude, ENSO, IOD indices | 04 |
| QC: range, step, persistence, buddy (MAD) checks; IDW; radar–gauge bias | 05 |
| Radar range and beam height, dBZ, Z–R, KDP rain | 06 |
| Planck brightness temperature, cooling rate, flash-to-bang | 06 |
| CFL condition, data assimilation cost function, scalar Kalman update | 07 |
| Bilinear interpolation, running and decaying bias, quantile mapping | 08 |
| MOS regression, logistic regression, EMOS/NGR, BMA, inverse-MSE weights, log-odds blending | 08 |
| Ensemble mean, spread, exceedance probability, spread–skill, sampling error | 09 |
| Point vs area probability, time-window probability | 09 |
| Lagrangian persistence, optical flow, cross-correlation, arrival time, nowcast–NWP blend | 10 |
| Harmonic climatology, anomalies, gamma distribution, return periods, GEV/Gumbel | 11 |
| Contingency scores (POD, FAR, POFD, CSI, ETS, HSS, PSS, bias) | 12 |
| ME, MAE, RMSE, skill scores | 12 |
| Brier score and decomposition, ROC/AUC, ignorance, CRPS (ensemble and Gaussian), FSS | 12 |
| Bootstrap confidence intervals | 12 |
| Cost–loss rule, economic value, expected expense | 13 |
| PSI sub-index interpolation, gust factor, Beaufort | 15 |

## 18.4 Glossary

| Term | Meaning |
| --- | --- |
| **Analysis** | Best estimate of the current atmospheric state from data assimilation |
| **AIFS** | ECMWF's operational AI forecasting system |
| **Base rate** | Climatological frequency of an event in the verification sample |
| **Bias** | Systematic forecast error (mean of forecast minus observation) |
| **Brier score** | Mean squared error of probability forecasts |
| **CAPE** | Convective available potential energy: buoyant energy for updrafts |
| **CIN** | Convective inhibition: energy barrier before free convection |
| **Climatology** | Long-term statistics for a place and time; the baseline forecast |
| **Convection-permitting model** | NWP with grid spacing ≲ 4 km that simulates storms explicitly |
| **CRPS** | Continuous ranked probability score for probabilistic forecasts of continuous variables |
| **dBZ** | Logarithmic radar reflectivity |
| **Dewpoint** | Temperature at which air becomes saturated when cooled at constant pressure |
| **Diurnal cycle** | Daily cycle driven by solar heating |
| **Ensemble** | Set of forecasts from perturbed initial conditions/physics |
| **ENSO** | El Niño–Southern Oscillation |
| **ERA5** | ECMWF's global reanalysis, hourly, 1940–present |
| **ETS** | Equitable threat score |
| **FSS** | Fractions skill score, neighbourhood verification for gridded rain |
| **Geostrophic wind** | Wind balancing pressure gradient and Coriolis; invalid near the equator |
| **IOD** | Indian Ocean Dipole |
| **ITCZ** | Intertropical Convergence Zone |
| **K-index** | Stability index combining lapse rate and moisture at 850–500 hPa |
| **LCL** | Lifting condensation level (cloud base for a lifted parcel) |
| **LFC** | Level of free convection |
| **Lead time** | Valid time minus initialisation time |
| **MJO** | Madden–Julian Oscillation, 30–60 day eastward-moving convective envelope |
| **Monsoon surge** | Strengthening of NE monsoon winds bringing prolonged heavy rain to Singapore |
| **MOS** | Model output statistics: regression post-processing of model output |
| **Nowcast** | Forecast for 0–6 hours, dominated by extrapolation |
| **NWP** | Numerical weather prediction |
| **Parameterisation** | Simplified representation of sub-grid processes |
| **PoP** | Probability of precipitation at a point over a period |
| **Potential temperature (θ)** | Temperature after adiabatic descent/ascent to 1000 hPa |
| **Precipitable water** | Total column water vapour as liquid depth |
| **PSI** | Pollutant Standards Index (Singapore air quality) |
| **Radiosonde** | Balloon-borne instrument measuring vertical profiles |
| **Reanalysis** | Consistent historical analysis from a fixed assimilation system |
| **Reliability** | Agreement between forecast probabilities and observed frequencies |
| **Resolution (forecast)** | Ability to separate event and non-event cases |
| **Return period** | Average interval between exceedances (1 / annual probability) |
| **Rossby number** | Ratio of inertial to Coriolis forces |
| **SINGV** | MSS's convection-permitting regional model |
| **Spread** | Ensemble standard deviation |
| **Sumatra squall** | Organised line of storms from Sumatra/Strait of Malacca, mostly pre-dawn to morning |
| **θe** | Equivalent potential temperature |
| **Valid time** | Time a forecast applies to |
| **WBGT** | Wet Bulb Globe Temperature, heat stress index used by NEA |
| **Z–R relation** | Power law converting radar reflectivity to rain rate |

## 18.5 Key references

- Ahrens, C. D., *Meteorology Today*: introductory text.
- Wallace, J. M. and Hobbs, P. V., *Atmospheric Science: An Introductory Survey*: thermodynamics and dynamics.
- Holton, J. R. and Hakim, G. J., *An Introduction to Dynamic Meteorology*.
- Wilks, D. S., *Statistical Methods in the Atmospheric Sciences*: verification, post-processing, ensembles.
- Jolliffe, I. T. and Stephenson, D. B. (eds), *Forecast Verification: A Practitioner's Guide*.
- Bolton, D. (1980), "The computation of equivalent potential temperature", *Monthly Weather Review*.
- Stull, R. (2011), "Wet-bulb temperature from relative humidity and air temperature", *J. Applied Meteorology and Climatology*.
- Roberts, N. M. and Lean, H. W. (2008), fractions skill score, *Monthly Weather Review*.
- Richardson, D. S. (2000), economic value of ensemble forecasts, *QJRMS*.
- Wheeler, M. C. and Hendon, H. H. (2004), RMM MJO index, *Monthly Weather Review*.
- COMET MetEd (meted.ucar.edu): free training, including tropical meteorology.
- MSS (weather.gov.sg): Singapore climate and seasonal information.
