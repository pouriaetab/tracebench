# 9. Analysis at scale: data volumes, features, methods, evaluations and A/B tests

## How much data was analysed

| Analysis | Data | Size |
|:--|:--|--:|
| Field validation of model R (this repo, [07](07-field-validation.md)) | Real one minute bars, 10 instruments, Jan to Sep 2026 | 1,398,672 bars read · 612,531 in-session · 507,080 graded predictions |
| Field A/B test, CR-2 (this repo) | Held out sessions, Jul to Sep 2026 | 280 sessions · 93,800 paired predictions · 2,000 cluster-bootstrap resamples |
| Simulation validation (this repo, every build) | Seeded scenarios with known truth | 400,000 simulated bars and 220,360 predictions for calibration · 93,600 bars and 40,320 predictions for the seasonal A/B · 120,000 bars for assumption checks · 16,000 simulated levels for the operating characteristic · 16,000 distribution fits for parameter recovery |
| Alert signal study (original system) | Every recorded alert joined to the tick lake at its own timestamp | 32,074 alerts · 12 sessions · features computed from up to 84 million ticks, using only data at or before each alert |
| Event study (original system) | A 2 second grid over every instrument and second of the session | 2.06 million grid points · 40 instruments · 5 sessions |
| Alert outcome grading (original system) | Every alert graded at 6 horizons | 187,352 outcomes |
| Filter study (original system) | Graded alerts by regime filter, 3 horizons | about 4,900 alerts · 7 filters × 3 horizons |
| Model training (original system) | Retraining history of the alert confidence model | 672 recorded fits across 12 model variants |

## Features, overall and per model

| Model or study | Inputs / features | Count |
|:--|:--|--:|
| **R** touch probability | price, level, horizon, realized volatility (from up to 300 bars); plus 2 assumption diagnostics (excess kurtosis, volatility clustering) and, with CR-2, a 390-point intraday volatility profile | 4 inputs + 2 diagnostics + profile |
| **S** strengthening | breaks and holds in the earlier and recent halves of a level's tests | 4 counts |
| **M** tail size | the sample of post test excursions, a threshold quantile | 1 distribution → 2 fitted parameters |
| Alert-confidence model (original) | trigger size and surge, quote imbalance, spread, session phase (pre, regular, after), trend with or against (instrument, market, recent), VWAP side, day and market return in the alert's direction, time of day, burst shape (single print share, burst count), order flow direction, acceleration, range position | **24** |
| Alert signal study (original) | the 20 production features above that were available at the time, plus 15 order flow and tape features: order flow imbalance over 10, 30 and 60 s, tick imbalance, range position, trade count, realized-volatility ratio, acceleration, intensity, pre alert 5 minute return, pullback in spreads, large print share, VWAP distance, quote imbalance, micro price deviation | **35** |
| Alert record (original) | everything stored per alert, including context and model version | 37 fields |

## Statistical methods, and where each is used

| Method | Where |
|:--|:--|
| Reflection principle for Brownian motion (barrier touch probability) | Model R |
| Realized volatility | Model R |
| Empirical Bayes shrinkage, weight n / (n + k) | Model R blend |
| Intraday seasonality profile (normalised squared returns by minute of session) | CR-2 |
| Beta-Binomial conjugate update | Model S |
| Monte Carlo comparison of two posteriors | Model S |
| Peaks over threshold, Generalized Pareto, method of moments | Model M |
| Excess kurtosis; lag 1 autocorrelation of squared returns (ARCH proxy) | Assumption checks |
| Driftless random walk with subbar monitoring; Student-t innovations; GARCH(1,1) | Known truth scenarios |
| Ridge-regularised logistic regression (numpy) | Original alert confidence model |
| Order-flow imbalance (Cont, Kukanov and Stoikov, 2014) | Original signal study |
| Robust z-scores with median absolute deviation | Original event study |

## Evaluation metrics

| Metric | Measures | Used for |
|:--|:--|:--|
| Reliability table, ECE, Brier score | Calibration of probabilities | Model R, simulated and real |
| False-alarm rate and power with standard errors | Operating characteristic | Model S |
| Bias, RMSE, 5th and 95th percentiles of estimates | Parameter recovery | Model M |
| AUC, log-loss against the base rate | Ranking and probability quality | Original alert model |
| Hit rate and mean return against the median spread, per bucket | Whether a signal clears its own cost | Original signal and filter studies |
| Cluster (session) bootstrap intervals | Uncertainty of a difference | A/B tests |

## A/B tests and controlled comparisons

All are offline: variants are compared on the same recorded events, not by
randomly assigning live traffic. For a model that only reads data, a paired offline
comparison on held out data is the stronger design, because both variants see
exactly the same events.

| Comparison | Design | Result |
|:--|:--|:--|
| **CR-2, real data** (this repo) | Profile learned Jan to Jun, both variants scored on Jul to Sep, paired, session bootstrap | ECE 0.045 → 0.020; Brier −0.0047, 95% interval [−0.0055, −0.0039] |
| **CR-2, simulated** (this repo, runs in CI) | Same design, known intraday pattern | B better, interval excludes zero (R-7) |
| **CR-1, strength threshold** (this repo) | 0.75 vs 0.95 on the same simulated levels | False alarms 19 to 27% → 4 to 6%; power cost reported |
| **TB-1, estimator fix** (this repo) | Original vs fixed estimator on the same samples | Bias −0.37 → −0.03 at xi = 0.2, n = 200 |
| Feature sets (original) | Day-wise walk forward: train on days up to k, test on day k+1; 20 vs 35 features | AUC 0.582 → 0.594; top-20% hit rate 46 to 47% vs a 39% base rate |
| Trigger vs baseline (original) | Alerted seconds vs every second on the 2 second grid | 42.7% vs 42.2% continuation: the trigger added nothing over chance |
| Rule change by counterfactual replay (original) | One recorded session replayed with and without a new rule | 129 alerts and 57 reversals → 116 and 36 |
| Champion and challenger (original) | A new fit replaces the current model only if it beats the base rate on held out days | 4 of 6 variants promoted after the order flow features, test AUC 0.556 to 0.560 |
