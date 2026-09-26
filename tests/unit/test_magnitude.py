import math

import numpy as np
import pytest

from tracebench import scenarios
from tracebench.models import magnitude as M


@pytest.mark.req("M-1")
@pytest.mark.parametrize("data", [[], [1.0] * 4, [1.0, 2.0, float("nan"), 3.0, 4.0, 5.0],
                                  [1.0, 2.0, -3.0, 4.0, 5.0], [2.0] * 10])
def test_fit_refuses_bad_or_thin_data(data):
    assert M.fit_moments(data) is None


@pytest.mark.req("M-2")
@pytest.mark.parametrize("xi", [-0.3, 0.0, 0.2])
def test_survival_starts_at_one_and_never_rises(xi):
    ys = np.linspace(0, 10, 200)
    s = [M.survival(y, xi, 1.0) for y in ys]
    assert s[0] == pytest.approx(1.0)
    assert all(a >= b for a, b in zip(s, s[1:]))


@pytest.mark.req("M-2")
def test_bounded_tail_is_zero_past_its_endpoint():
    xi, sig = -0.25, 1.0
    endpoint = -sig / xi
    assert M.survival(endpoint + 0.01, xi, sig) == 0.0


@pytest.mark.req("M-2")
@pytest.mark.parametrize("xi", [-0.2, 0.0, 0.15])
def test_quantile_inverts_tail_probability(xi):
    u, rate, sig = 2.0, 0.5, 1.3
    for p in (0.4, 0.1, 0.01):
        x = M.quantile(p, u, rate, xi, sig)
        assert M.tail_probability(x, u, rate, xi, sig) == pytest.approx(p, rel=1e-9)


@pytest.mark.req("M-2")
def test_no_extrapolation_below_the_threshold():
    assert M.quantile(0.9, 2.0, 0.5, 0.1, 1.0) is None
    assert M.tail_probability(1.0, 2.0, 0.5, 0.1, 1.0) is None


@pytest.mark.req("M-3")
def test_regression_tb1_heavy_tail_is_not_reported_as_bounded():
    """Defect TB-1: the inherited estimator flipped the sign of xi. On a large
    heavy-tailed sample the fixed fit must be positive and the original negative."""
    y = scenarios.gpd_sample(200_000, 0.2, 1.0, seed=1)
    assert M.fit_moments(y)[0] == pytest.approx(0.2, abs=0.02)
    assert M.fit_moments_original(y)[0] < 0
