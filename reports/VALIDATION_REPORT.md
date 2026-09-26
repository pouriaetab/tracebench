# Validation report

Every number below is produced by `tracebench/studies.py` from seeded scenarios, so the report is identical on every run (SYS-2). Tests in `tests/validation/` assert the thresholds.

## VAL-R1, VAL-R2: touch probability calibration (R-4, R-5)

Simulated market: driftless random walk, per bar volatility 0.2%, 20,000 bars per seed, levels at 0.25 to 2.5 expected moves above and below price, 30 bar horizon.

| Scenario | What it breaks | ECE per seed | Mean overprediction |
|:--|:--|:--|--:|
| fine | nothing (16 observations per bar) | 0.012, 0.014, 0.018, 0.007, 0.007 | +1.1 pts |
| coarse | continuous monitoring (1 observation per bar) | 0.039, 0.045, 0.037, 0.042, 0.040 | +4.1 pts |
| garch | constant volatility (GARCH clustering) | 0.035, 0.042, 0.034, 0.033, 0.031 | +2.7 pts |
| fat | normal returns (Student-t, 3 df) | 0.017, 0.022, 0.019, 0.028, 0.027 | +2.1 pts |

Reliability table, fine (all seeds pooled):

| Predicted bin | n | Mean predicted | Observed | ± SE |
|:--|--:|--:|--:|--:|
| 0.0 to 0.1 | 15740 | 0.029 | 0.028 | 0.001 |
| 0.1 to 0.2 | 7870 | 0.134 | 0.127 | 0.004 |
| 0.3 to 0.4 | 7870 | 0.317 | 0.308 | 0.005 |
| 0.4 to 0.5 | 7870 | 0.453 | 0.437 | 0.006 |
| 0.6 to 0.7 | 7870 | 0.617 | 0.599 | 0.006 |
| 0.8 to 0.9 | 7870 | 0.803 | 0.779 | 0.005 |

Reliability table, coarse (all seeds pooled):

| Predicted bin | n | Mean predicted | Observed | ± SE |
|:--|--:|--:|--:|--:|
| 0.0 to 0.1 | 15740 | 0.029 | 0.022 | 0.001 |
| 0.1 to 0.2 | 7870 | 0.134 | 0.109 | 0.004 |
| 0.3 to 0.4 | 7870 | 0.317 | 0.273 | 0.005 |
| 0.4 to 0.5 | 7870 | 0.453 | 0.392 | 0.006 |
| 0.6 to 0.7 | 7870 | 0.617 | 0.550 | 0.006 |
| 0.8 to 0.9 | 7870 | 0.803 | 0.728 | 0.005 |

Reading it: with fine monitoring the model is calibrated to within about a point. The small residual overprediction that remains is itself discrete monitoring (16 looks per bar is still not continuous) plus noise in the estimated volatility. With one observation per bar the model overpredicts in every bin, because the formula assumes every instant is watched (discrete monitoring bias). Clustered volatility overpredicts too: the trailing volatility estimate lags the regime.

## VAL-R5: intraday seasonality A/B test on simulated sessions (R-7, CR-2)

240 simulated sessions of 390 one minute bars with a U-shaped volatility pattern. The pattern is learned from the first 120 sessions only; A (baseline) and B (seasonality adjusted) are compared on the last 120.

| | First 30 min | Midday | Last 30 min |
|:--|--:|--:|--:|
| True pattern | 2.30 | 0.79 | 1.03 |
| Learned from training sessions | 2.26 | 0.79 | 1.05 |

| Variant | ECE | Brier |
|:--|--:|--:|
| A baseline | 0.0188 | 0.14541 |
| B seasonality adjusted | 0.0102 | 0.14459 |

Brier B minus A -0.00081, 95% session bootstrap interval [-0.00115, -0.00046], 40,320 predictions in 120 sessions. The same test on real market data is in docs/07-field-validation.md.

## VAL-R3: assumption checks (R-6)

8 seeds of 5,000 bars each.

| Data | Excess kurtosis (range) | Clustering (range) | Flagged fat tails | Flagged clustering |
|:--|:--|:--|--:|--:|
| normal | -0.12 to 0.04 | -0.018 to 0.030 | 0/8 | 0/8 |
| fat_tails | 11.04 to 131.73 | -0.007 to 0.085 | 8/8 | 1/8 |
| clustered | 1.91 to 12.52 | 0.109 to 0.290 | 8/8 | 8/8 |

## VAL-S1: strengthening signal, operating characteristic (S-5, S-6)

1,000 simulated levels per cell. False alarm: break rate unchanged at 0.5. Power: break rate falls from 0.6 to 0.3.

Threshold 0.75, inherited design (KI-1):

| Tests | False alarm | Power |
|--:|--:|--:|
| 8 | 0.188 ± 0.012 | 0.424 ± 0.016 |
| 16 | 0.214 ± 0.013 | 0.664 ± 0.015 |
| 32 | 0.267 ± 0.014 | 0.890 ± 0.010 |
| 64 | 0.274 ± 0.014 | 0.971 ± 0.005 |

Threshold 0.95, adopted (CR-1):

| Tests | False alarm | Power |
|--:|--:|--:|
| 8 | 0.047 ± 0.007 | 0.157 ± 0.012 |
| 16 | 0.038 ± 0.006 | 0.298 ± 0.014 |
| 32 | 0.048 ± 0.007 | 0.567 ± 0.016 |
| 64 | 0.059 ± 0.007 | 0.808 ± 0.012 |

## VAL-M1: tail shape recovery (M-3) and defect TB-1

500 fits per cell, GPD samples with sigma = 1.

| True xi | n | Bias (fixed) | RMSE (fixed) | Bias (original) |
|--:|--:|--:|--:|--:|
| 0.0 | 20 | -0.088 | 0.235 | +0.088 |
| 0.0 | 50 | -0.036 | 0.141 | +0.036 |
| 0.0 | 200 | -0.008 | 0.067 | +0.008 |
| 0.0 | 1000 | -0.001 | 0.031 | +0.001 |
| 0.1 | 20 | -0.144 | 0.266 | -0.056 |
| 0.1 | 50 | -0.066 | 0.158 | -0.134 |
| 0.1 | 200 | -0.020 | 0.077 | -0.180 |
| 0.1 | 1000 | -0.004 | 0.037 | -0.196 |
| 0.2 | 20 | -0.159 | 0.273 | -0.241 |
| 0.2 | 50 | -0.089 | 0.149 | -0.311 |
| 0.2 | 200 | -0.034 | 0.087 | -0.366 |
| 0.2 | 1000 | -0.009 | 0.045 | -0.391 |
| 0.35 | 20 | -0.246 | 0.320 | -0.454 |
| 0.35 | 50 | -0.151 | 0.202 | -0.549 |
| 0.35 | 200 | -0.080 | 0.111 | -0.620 |
| 0.35 | 1000 | -0.035 | 0.062 | -0.665 |

Reading it: the original estimator's bias grows with the true xi and never shrinks with more data, the signature of a formula error rather than noise. The fixed estimator's bias shrinks toward zero as n grows. Below about 50 samples, and for xi near 0.35, even the fixed estimator is biased low: a documented limit of the method of moments.
