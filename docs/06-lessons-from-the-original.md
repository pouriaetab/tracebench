# 6. Lessons from the original system

tracebench was rebuilt from a larger private project: an intraday market data
desk that recorded quotes and trades, found support and resistance levels, ran
the three models in this repository on them, and raised short term alerts. That
system was used live for several weeks. Some of it worked. A good deal of it did
not, and the failures are the more useful half of this page, because each one is
a V&V lesson with a concrete symptom behind it.

Numbers below are the original system's own measurements on its recorded data.
No account, position or financial result of any kind is included. See [DISCLAIMER.md](../DISCLAIMER.md).

## What worked

1. **"Insufficient evidence" as a real answer.** Every model returned no value,
   not a guess, when its inputs were too thin, and the interface said so. This
   survived intact into tracebench (R-1, S-2, M-1).
2. **Assumptions measured on the live data.** The touch model reported the
   kurtosis and volatility clustering of the data it was actually using. tracebench
   adds what was missing: validated flag levels (R-6).
3. **Time-ordered validation for the learned model.** The alert confidence model
   was split by trading day (train, validate, untouched test), refused to fit on
   thin data, and was only promoted if it beat the base rate on held out days.
   That discipline is what later exposed how weak it was.
4. **Grading every alert after the fact.** Each alert was graded at a ladder of
   horizons (1, 2, 5, 10, 20 and 30 minutes) from the moment it fired. Without that
   ledger, none of the failures below could have been measured.
5. **A single pre handoff gate.** Syntax, unit tests, type checks, a render check,
   the launcher's own tests and a live smoke test, in one script. It caught many
   regressions before they reached the live session.

## What failed, and the V&V practice that catches it

### 1. The models were never validated

The three models shipped with a note saying "not yet formally backtested". Rebuilding
them here with known truth validation found a sign error in the tail model (TB-1)
and a false alarm rate of 19 to 27 percent in the strengthening signal (KI-1).
- **Practice:** validate against ground truth before a number reaches a user.
- **In tracebench:** M-3, S-5, and the whole `tests/validation` folder.

### 2. The alert signal was never better than a coin flip

When finally measured over 32,074 recorded alerts across 12 sessions, the
short horizon alerts resolved in their own direction 37 to 43 percent of the time
at one minute, on every session. Users had reported that the signal was
"degrading"; the ledger showed it had never been above chance. The trigger needed
a 2 sigma move first, and at these horizons prices partly reverse after a sharp
move, so the signal entered after the move by construction. Stronger triggers did
worse, not better.
- **Practice:** a confirmation is not a prediction. Before trusting an alert,
  compare what follows it with what follows any moment at all (a baseline).
- **In tracebench:** calibration against observed outcomes is the core of R-4.

### 3. A learned confidence score barely beat the base rate

The confidence model's best held out result was an AUC of 0.558, with log-loss
0.6642 against 0.6673 for simply predicting the base rate. One horizon out of
twelve earned a model at all.
- **Practice:** always report the no skill baseline next to a model's score. A
  model that does not beat it is not a model, whatever its complexity.

### 4. Train/serve skew: the model scored different inputs than it learned from

The scoring code passed 13 of the model's 21 features; the other 8 were silently
filled with defaults on every live prediction.
- **Practice:** build the scoring input from the same record as the training input,
  and test that they are identical.
- **In tracebench:** SYS-3, every prediction record can be recomputed from itself.

### 5. A sign applied twice

A new module applied a sign convention a second time to values that were already
stored with it. One group of outcomes was reported as 52 percent favourable with a
positive average, when the recorded data said 41.7 percent with a negative average.
- **Practice:** verify a stored convention against the data, not by reading the code
  that wrote it; keep one definition and test it both ways.
- **In tracebench:** SYS-4, the mirrored series test of the touch definition.

### 6. Filters did not rescue a signal that was late

Every obvious filter was measured (trend alignment, VWAP side, market direction) at
60, 300 and 1,800 seconds. Every cell had a negative average outcome in the
signal's own direction; hit rates of 40 to 49 percent with negative averages meant
the misses were larger than the hits.
- **Practice:** judge a signal against its own cost, per bucket, with a standard
  error, before building anything on top of it.

### 7. Green tests, stopped application

The system was handed back "all green" while it had been stopped for 20 minutes.
- **Practice:** a passing test suite is not a running system. Check the system's own
  signs of life: heartbeat age, process id, the tail of its log, a live smoke test.

### 8. A gate that lied about why it failed

A full disk made the test harness's temporary file creation fail, and the gate
reported "10 failures" for tests it never ran.
- **Practice:** separate "the product failed" from "the check could not run".
- **In tracebench:** SYS-5, the ENVIRONMENT ERROR verdict.

### 9. Tests with an expiry date

Two tests pinned a news headline to a fixed date inside a 7-day freshness window.
They passed for exactly seven days, then failed looking like a product bug.
- **Practice:** never hard code a calendar date inside a rolling window; build
  fixtures relative to now, or freeze time.

### 10. Time zones and calendar boundaries

A scheduled end of day job fired an hour late because the scheduler used the
machine's time zone. A monthly file was named after its first record and did not
roll over at the month boundary.
- **Practice:** boundary value tests at every calendar edge (midnight, month end,
  daylight saving change), and name the time zone on every schedule.

## The decision

The original system will most likely be replaced by a new design built from these
lessons. tracebench keeps the parts worth keeping, the three models and the
discipline of saying "not enough evidence", and adds what the original lacked:
written requirements, tests at every level, validation against ground truth, and
a traceability matrix that shows, for each requirement, the evidence that it holds.
