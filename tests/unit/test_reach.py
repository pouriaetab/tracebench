import math

import numpy as np
import pytest

from tracebench import scenarios
from tracebench.models import reach

SIG = 0.002


@pytest.mark.req("R-1")
def test_too_little_history_gives_no_answer():
    bars = scenarios.price_bars(reach.MIN_BARS_FOR_VOL - 1, SIG, seed=1)
    assert reach.estimate_volatility(bars) is None


@pytest.mark.req("R-1")
@pytest.mark.parametrize("args", [
    (100, 101, None, 30), (100, 101, 0.0, 30), (100, 101, -1.0, 30), (100, 101, float("nan"), 30),
    (0, 101, SIG, 30), (100, -5, SIG, 30), (100, 101, SIG, 0),
])
def test_invalid_inputs_give_no_answer(args):
    assert reach.touch_probability(*args) is None


@pytest.mark.req("R-1")
def test_enough_history_gives_an_answer():
    bars = scenarios.price_bars(400, SIG, seed=1)
    s = reach.estimate_volatility(bars)
    assert s is not None and 0.5 * SIG < s < 1.5 * SIG


@pytest.mark.req("R-2")
def test_probability_properties():
    p = lambda lvl, s=SIG, h=30: reach.touch_probability(100.0, lvl, s, h)
    assert p(100.0) == 1.0
    grid = [p(100 * math.exp(k * 0.002)) for k in range(0, 40)]
    assert all(0.0 <= x <= 1.0 for x in grid)
    assert all(a >= b for a, b in zip(grid, grid[1:])), "must fall with distance"
    assert p(101, h=60) > p(101, h=30), "must rise with horizon"
    assert p(101, s=0.004) > p(101), "must rise with volatility"
    assert p(100 * math.exp(0.01)) == pytest.approx(p(100 * math.exp(-0.01))), "symmetric in log-distance"


@pytest.mark.req("R-2")
def test_probability_matches_the_closed_form():
    d, s, h = 0.01, 0.002, 25
    expected = 2 * (1 - 0.5 * (1 + math.erf((d / (s * math.sqrt(h))) / math.sqrt(2))))
    assert reach.touch_probability(100, 100 * math.exp(d), s, h) == pytest.approx(expected)


@pytest.mark.req("R-3")
def test_blend_weight_and_bounds():
    assert reach.shrinkage_weight(0) == 0.0
    assert reach.shrinkage_weight(15) == pytest.approx(0.5)
    assert reach.shrinkage_weight(10_000) > 0.99
    for n in (1, 5, 15, 60):
        value, w = reach.blend(0.8, n, 0.2)
        assert 0.2 <= value <= 0.8 and w == pytest.approx(n / (n + reach.SHRINKAGE_K))


@pytest.mark.req("R-3")
def test_blend_falls_back_to_whichever_side_has_a_value():
    assert reach.blend(None, 0, 0.3) == (0.3, 0.0)
    assert reach.blend(0.6, 10, None) == (0.6, 1.0)
    assert reach.blend(None, 0, None) == (None, 0.0)
