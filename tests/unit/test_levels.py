import pytest

from tracebench import scenarios
from tracebench.bars import Bar
from tracebench.levels import first_touch_index, touched


def mirror(bars, p0):
    """Reflect log-price around p0: p -> p0^2 / p. Highs become lows."""
    return [Bar(b.timestamp_ms, p0 * p0 / b.open, p0 * p0 / b.low, p0 * p0 / b.high,
                p0 * p0 / b.close, b.volume) for b in bars]


@pytest.mark.req("SYS-4")
def test_touch_definition_is_symmetric():
    bars = scenarios.price_bars(300, 0.003, seed=5)
    p0 = 100.0
    mirrored = mirror(bars, p0)
    for level in (99.0, 99.5, 100.4, 101.0, 102.0):
        assert touched(bars, p0, level) == touched(mirrored, p0, p0 * p0 / level)
        assert first_touch_index(bars, p0, level) == first_touch_index(mirrored, p0, p0 * p0 / level)


@pytest.mark.req("SYS-4")
def test_resistance_uses_high_and_support_uses_low():
    b = [Bar(1, 100, 101, 99, 100)]
    assert touched(b, 100, 101) and not touched(b, 100, 101.01)
    assert touched(b, 100, 99) and not touched(b, 100, 98.99)
