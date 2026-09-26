from dataclasses import replace

import pytest

from tracebench import replay, scenarios
from tracebench.bars import Bar
from tracebench.models import reach


def preds_by_t(preds):
    out = {}
    for p in preds:
        out.setdefault(p.t, []).append((p.level, p.sigma, p.p))
    return out


@pytest.mark.req("SYS-1")
def test_changing_the_future_never_changes_a_past_prediction():
    bars = scenarios.price_bars(2000, 0.002, seed=11)
    cut = 1200
    shocked = bars[:cut + 1] + [Bar(b.timestamp_ms, b.open * 3, b.high * 3, b.low * 3, b.close * 3)
                                for b in bars[cut + 1:]]
    a, b = preds_by_t(replay.replay(bars)), preds_by_t(replay.replay(shocked))
    past = [t for t in a if t <= cut]
    assert past, "the test needs predictions before the cut"
    for t in past:
        assert a[t] == b[t], f"prediction at t={t} moved when only the future changed"


@pytest.mark.req("SYS-1")
def test_outcomes_do_use_the_future():
    """The control for the test above: outcomes are graded from future bars, so
    changing the future must change at least one outcome. Without this, the
    no-lookahead test could pass because nothing depends on the future at all."""
    bars = scenarios.price_bars(2000, 0.002, seed=11)
    shocked = bars[:1001] + [Bar(b.timestamp_ms, b.open * 3, b.high * 3, b.low * 3, b.close * 3)
                             for b in bars[1001:]]
    a = {(p.t, p.level): p.touched for p in replay.replay(bars) if p.t < 1001}
    b = {(p.t, p.level): p.touched for p in replay.replay(shocked) if p.t < 1001}
    assert a != b


@pytest.mark.req("SYS-3")
def test_every_record_can_be_recomputed_from_itself():
    for p in replay.replay(scenarios.price_bars(1500, 0.002, seed=12)):
        assert reach.touch_probability(p.price, p.level, p.sigma, p.horizon) == p.p


@pytest.mark.req("SYS-3")
def test_record_sigma_is_the_sigma_of_the_bars_available_then():
    bars = scenarios.price_bars(1500, 0.002, seed=13)
    for p in replay.replay(bars)[:50]:
        window = bars[max(0, p.t + 1 - reach.VOL_LOOKBACK_BARS): p.t + 1]
        assert reach.estimate_volatility(window) == p.sigma
