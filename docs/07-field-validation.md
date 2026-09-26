# 7. Field validation: the touch model on real market data, and an A/B test

Simulation proves a model can recover a truth it was built for. It cannot show
what the real world does to it. This page is the model run against real
one minute bars, the problem that surfaced, and the controlled comparison that
decided the fix.

The raw data is licensed market data and is not in this repository. The script
that produced every number here is: `python -m tracebench.field DATA_DIR --split-month 6`.
It prints aggregates only.

## The data

| | |
|:--|--:|
| Instruments | 10 of the most actively traded US equities and ETFs |
| Period | January to September 2026 |
| Files read | 90 (one per symbol per month) |
| One minute bars read | 1,398,672 |
| Rejected by the loader | 0 (9 duplicate timestamps collapsed) |
| Regular-session bars (09:30 to 16:00 ET) | 612,531 |
| Sessions (symbol-days) | 1,605, of which 1,510 complete (at least 360 of 390 bars) |
| Predictions graded | 507,080 |

Each session is replayed separately so that no prediction spans an overnight
gap. At every 10th bar the model estimates volatility from the previous 120 bars
of the same session, predicts the chance of touching 14 levels (0.25 to 2.5
expected moves above and below), and the outcome is graded from the next 30 bars.

## Finding: the baseline is miscalibrated on real data (KI-2)

| Predicted bin | n | Mean predicted | Observed |
|:--|--:|--:|--:|
| 0.0 to 0.1 | 144,880 | 0.029 | 0.028 |
| 0.1 to 0.2 | 72,440 | 0.134 | 0.092 |
| 0.3 to 0.4 | 72,440 | 0.317 | 0.229 |
| 0.4 to 0.5 | 72,440 | 0.453 | 0.355 |
| 0.6 to 0.7 | 72,440 | 0.617 | 0.531 |
| 0.8 to 0.9 | 72,440 | 0.803 | 0.753 |

ECE **0.052** against a requirement of 0.03, Brier 0.144, and the model predicts
touches **5.2 points** more often than they happen, in every bin above 10%.

Diagnosis. The simulation study had already measured two ways the model
overpredicts (coarse monitoring and clustered volatility). Real one minute bars
record the true high and low, so coarse monitoring is not it. Splitting the
predictions by time of day showed the pattern: overprediction of 6.1 points
around midday, and 1.2 points of underprediction in the last hour. Intraday
volatility is not constant; it follows a daily shape. Learned from the data:

| Part of the session | Relative volatility (1.00 = session average) |
|:--|--:|
| First 30 minutes | 3.94 |
| Midday | 0.57 |
| Last 30 minutes | 0.66 |

At midday the trailing 120 minute window still contains the busy morning, so
the model expects more movement than is coming.

## The A/B test (CR-2)

- **A:** the baseline model.
- **B:** the same model with volatility rescaled by the intraday profile
  (`tracebench/seasonality.py`).
- **Design:** the profile is learned from January to June only (1,230 sessions).
  Both variants are scored on July to September (280 sessions, 93,800
  predictions) that played no part in building B. Same predictions, same
  outcomes: a paired comparison.
- **Uncertainty:** predictions within a session are correlated, so the
  confidence interval comes from resampling whole sessions (cluster bootstrap,
  2,000 resamples).

| Variant | ECE | Brier | Mean overprediction |
|:--|--:|--:|--:|
| A baseline | 0.0449 | 0.15055 | +3.6 pts |
| B seasonality adjusted | **0.0204** | **0.14583** | -0.9 pts |

Brier B minus A: **-0.00472**, 95% interval [-0.00552, -0.00388]. B was better in
100% of resamples. Calibration error fell by more than half and now meets R-4's
threshold on held out real data.

## Why this is the right test design

1. **Held out in time.** B's only learned part (the profile) never saw the test
   months. Testing on the training months would flatter B.
2. **Paired.** Both variants score identical events, so market noise cancels in
   the difference.
3. **Clustered uncertainty.** Treating 93,800 correlated predictions as
   independent would give an interval far too narrow.
4. **The same test in CI.** `tests/validation/test_seasonal_ab.py` repeats the
   design on simulated sessions with a known pattern (R-7), so the method itself
   is verified every build.

## What this does not show

1. Ten liquid instruments over nine months. Thinly traded instruments and other
   regimes are untested.
2. The residual: B slightly underpredicts in the lowest bins. A time-of-day term
   in the horizon, or a longer training window, are the next candidates.
