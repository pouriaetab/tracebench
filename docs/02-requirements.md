# Requirements

Generated from `tracebench/requirements.py`, the single source of truth. Status for each one is in `reports/TRACEABILITY.md`.

## Data

| ID | Level | Requirement | Why |
|:--|:--|:--|:--|
| **DATA-1** | unit | The loader rejects a row with a nonfinite or nonpositive price, a high below the low, an open or close outside the high to low range, or negative volume, and records the reason. | Bad input must be caught where it enters, with a reason a person can act on. |
| **DATA-2** | integration | One bad row never fails the file: every valid row still loads. | A single typo once stopped half of a live data collector. |
| **DATA-3** | unit | Timestamps must strictly increase. A row that repeats or goes back in time is rejected, never resorted. | Silently reordering data hides the upstream fault that produced it. |
| **DATA-4** | integration | Writing bars to CSV and loading them back returns the same bars (to 6 decimal places). | Scenarios are saved and replayed; the round trip must not change them. |

## Reach

| ID | Level | Requirement | Why |
|:--|:--|:--|:--|
| **R-1** | unit | With fewer than 20 bars, or invalid inputs, the model returns no answer (None), never a number. | 'Insufficient evidence' is an answer. A guessed number is not. |
| **R-2** | unit | Probability stays in [0, 1], equals 1 at the current price, falls with distance, rises with horizon and volatility, and is the same for equal log distances above and below. | Properties any touch probability must have, whatever the data. |
| **R-3** | unit | The blend weights the empirical rate by n / (n + k), gives it zero weight at n = 0, stays between its two inputs, and falls back to whichever side has a value. | The blend must never produce a number outside what its evidence supports. |
| **R-4** | validation | On known truth data with fine monitoring (16 observations per bar), expected calibration error is at most 0.03 on every seed. | The model is only useful if 30 percent means about 30 percent. |
| **R-5** | validation | Each documented limit reproduces and is quantified: coarse bars and clustered volatility both make the model overpredict touches by at least 2 points on average. | A limit that is written down but never measured is a guess. |
| **R-6** | validation | The assumption checks flag fat tails and volatility clustering when present and flag neither on clean data. | A report must say when a number comes from outside the model's assumptions. |
| **R-7** | validation | When volatility follows an intraday pattern, the seasonality adjusted model (pattern learned from earlier sessions only) has lower calibration error than the baseline on later sessions, and its Brier improvement has a 95% session bootstrap interval entirely below zero. | Change CR-2 is adopted on evidence from held out data, not on in sample fit. |
| **R-8** | unit | The intraday profile estimator recovers a known pattern (open, midday and close within 10%), a flat profile gives an adjustment factor of exactly 1, and the paired bootstrap reports zero difference for identical variants and the correct sign otherwise. | The parts of an A/B test must be verified before its result is trusted. |

## Strength

| ID | Level | Requirement | Why |
|:--|:--|:--|:--|
| **S-1** | unit | The posterior after b breaks and h holds is Beta(1 + b, 1 + h); negative counts are rejected. | The conjugate update is the model; it must be exact. |
| **S-2** | unit | With fewer than 4 tests per half the answer is 'forming', never a label. | Too little evidence must not produce a confident sounding label. |
| **S-3** | unit | The same outcomes always give the same probability. | A number that changes between two identical requests cannot be trusted or tested. |
| **S-4** | unit | With identical evidence in both halves, the probability is within 0.02 of 0.5. | No evidence of change must read as no change. |
| **S-5** | validation | When a level's break rate has NOT changed, it is called 'strengthening' at most 10 percent of the time, at every sample size from 8 to 64 tests. | A false alarm rate is a design choice; it has to be stated and met. |
| **S-6** | validation | When the break rate really falls (0.6 to 0.3), the detection rate is reported for each sample size and is at least 70 percent at 64 tests. | Lowering false alarms costs power; the cost must be visible. |

## Magnitude

| ID | Level | Requirement | Why |
|:--|:--|:--|:--|
| **M-1** | unit | The fit refuses fewer than 5 excesses, and nonfinite or negative data. | A tail fitted to two or three points is not a tail. |
| **M-2** | unit | Survival is 1 at zero and never increases; quantile is the exact inverse of tail probability; a bounded tail has zero probability past its endpoint; nothing is extrapolated below the threshold. | Internal consistency of the fitted distribution. |
| **M-3** | validation | From 200 samples with known shape xi in {0, 0.1, 0.2}, the fitted xi has |bias| at most 0.05 and RMSE at most 0.10. | The fit must recover a truth it was built to recover. |

## System

| ID | Level | Requirement | Why |
|:--|:--|:--|:--|
| **SYS-1** | integration | No lookahead: changing any bar after time t never changes a prediction made at t. | Leaked future data makes a model look skilled when it is not. |
| **SYS-2** | system | The same inputs and seeds give identical validation results on every run. | A result that cannot be reproduced cannot be verified. |
| **SYS-3** | integration | Every prediction record carries its inputs, and recomputing from the record gives the same probability. | What was scored must be exactly what was evaluated (no train/serve skew). |
| **SYS-4** | unit | The touch definition is symmetric: mirroring the price series mirrors every outcome. | Sign conventions are where silent errors live; one definition, tested both ways. |
| **SYS-5** | system | If the test run itself cannot complete, the V&V run reports ENVIRONMENT ERROR, never pass or fail. | A gate that could not run must not report a result it did not measure. |
| **SYS-6** | system | Every requirement has at least one test, and every test names a requirement that exists. | Traceability that is not checked drifts. |
