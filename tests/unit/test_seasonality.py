import numpy as np
import pytest

from tracebench import scenarios
from tracebench.seasonality import estimate_profile, paired_bootstrap, seasonal_factor


@pytest.mark.req("R-8")
def test_profile_estimator_recovers_a_known_pattern():
    prof = scenarios.u_shaped_profile()
    sessions = [scenarios.price_bars(len(prof), 0.002, seed=9000 + i, profile=prof) for i in range(200)]
    est = estimate_profile(sessions, len(prof))
    for sl in (slice(0, 30), slice(150, 240), slice(360, 390)):
        assert est[sl].mean() == pytest.approx(prof[sl].mean(), rel=0.10)


@pytest.mark.req("R-8")
def test_flat_profile_changes_nothing():
    assert seasonal_factor(np.ones(390), range(0, 120), range(120, 150)) == 1.0


@pytest.mark.req("R-8")
def test_factor_scales_with_the_volatility_ahead():
    prof = np.ones(390)
    prof[200:] = 4.0
    assert seasonal_factor(prof, range(80, 200), range(200, 230)) == pytest.approx(2.0)


@pytest.mark.req("R-8")
def test_paired_bootstrap_zero_and_sign():
    rows_same = [(s, 0.3, 0.3, s % 2 == 0) for s in range(40) for _ in range(5)]
    r = paired_bootstrap(rows_same, reps=200)
    assert r["diff"] == 0.0 and r["ci_low"] == 0.0 and r["ci_high"] == 0.0
    rows_better = [(s, 0.9, 0.1, False) for s in range(40) for _ in range(5)]
    r = paired_bootstrap(rows_better, reps=200)
    assert r["diff"] < 0 and r["ci_high"] < 0
