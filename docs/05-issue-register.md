# 5. Defects, known issues and changes

A V&V process produces findings. Each one is recorded with an id, the evidence,
and what was done, so nothing is fixed silently and nothing known is hidden.

## Defects

### TB-1: tail shape returned with the wrong sign (fixed)

- **Found by:** VAL-M1, parameter recovery (requirement M-3).
- **Symptom:** on heavy tailed data with true xi = 0.2, the fit returned about
  -0.2: every heavy tail was reported as a bounded one. The bias grew with the
  true xi and did not shrink with more data (see the validation report).
- **Cause:** the method of moments formula was copied from a paper that writes the
  distribution with k = -xi. Their k was used as xi.
- **Why earlier tests missed it:** the unit tests checked the code against the
  formula as written. Code and formula agreed; the formula was wrong. Only a
  known truth test compares against the world.
- **Fix:** xi = 0.5 * (1 - mean^2 / variance).
- **Regression tests:** `test_regression_tb1_heavy_tail_is_not_reported_as_bounded`,
  `test_the_original_estimator_would_have_failed`.

## Known issues

KI-1 and KI-2 are defects: each is a written requirement that the design (KI-1) or the model on real
data (KI-2) failed to meet. They are recorded as known issues because each stayed open under its ID until a
change request (CR-1, CR-2) resolved it on evidence.

### KI-1: inherited strengthening threshold fails the false alarm requirement

- **Requirement:** S-5, at most 10 percent false "strengthening" labels.
- **Evidence:** at the inherited threshold of 0.75, unchanged levels were labelled
  strengthening 19 to 27 percent of the time (VAL-S1).
- **Status:** the design moved to 0.95 (CR-1), which meets S-5. The failing check
  on 0.75 stays in the suite as a strict expected failure, documenting why the
  change was made.

### KI-2: the touch model is miscalibrated on real intraday data (resolved by CR-2)

- **Requirement:** R-4 sets calibration error at most 0.03.
- **Evidence:** on 507,080 predictions over real one minute bars, ECE 0.052 and
  5.2 points of overprediction; 6.1 points around midday
  ([07-field-validation.md](07-field-validation.md)).
- **Root cause:** intraday volatility follows a daily shape; a trailing window at
  midday still contains the busy open.
- **Status:** CR-2 brings held out ECE to 0.020.

## Changes

### CR-1: strengthening threshold 0.75 to 0.95

- **Motivation:** KI-1.
- **Evidence it works:** false alarms between 0.04 and 0.06 at every sample size tested (1,000 simulated levels per cell).
- **Cost, stated:** power at 16 tests falls from about 0.66 to about 0.30; at 64
  tests it is 0.81 (S-6). Small samples now more often read "holding",
  which is the honest answer when the evidence is thin.

## Open defect: documented limits

1. **Discrete monitoring (model R).** Coarse bars make the model overpredict
   touches by about 4 points. Mitigation: prefer finer bars, or apply a
   discrete barrier correction (Broadie, Glasserman and Kou, 1997).
2. **Clustered volatility (model R).** About 3 points of overprediction; flagged
   at run time by the clustering check.
3. **Small samples (model M).** Below about 50 excesses, xi is biased low by 0.05
   to 0.25 even after the fix. Mitigation: report the sample size with every fit.

### CR-2: rescale volatility by the intraday profile

- **Motivation:** KI-2.
- **Evidence it works:** offline A/B test, profile learned from January to June,
  both variants scored on July to September (280 sessions, 93,800 paired
  predictions): ECE 0.045 to 0.020, Brier improvement 0.0047 with a 95% session
  bootstrap interval of [0.0039, 0.0055]. Repeated in CI on simulated sessions (R-7).
- **Cost, stated:** B needs a profile learned from past sessions, so it cannot run
  on the first day of a new instrument; slight underprediction remains in the
  lowest bins.
