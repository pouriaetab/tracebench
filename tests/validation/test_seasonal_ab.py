import pytest

from tracebench import studies


@pytest.mark.req("R-7")
def test_seasonality_adjustment_wins_on_held_out_sessions():
    r = studies.seasonal_ab()
    assert r["ece_b"] < r["ece_a"], r
    assert r["ci_high"] < 0, "the Brier improvement must be significant at 95%"
