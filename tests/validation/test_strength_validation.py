import pytest

from tracebench import studies
from tracebench.models import strength


@pytest.mark.req("S-5")
def test_false_alarm_rate_meets_requirement_at_adopted_threshold():
    for row in studies.strength_oc(strength.THRESHOLD):
        assert row["false_alarm"] <= 0.10, row


@pytest.mark.req("S-5")
@pytest.mark.xfail(strict=True, reason="KI-1: the inherited 0.75 threshold labels 19-27% of unchanged "
                                       "levels as strengthening; replaced by 0.95 (CR-1)")
def test_false_alarm_rate_at_inherited_threshold():
    for row in studies.strength_oc(strength.INHERITED_THRESHOLD):
        assert row["false_alarm"] <= 0.10, row


@pytest.mark.req("S-6")
def test_power_is_reported_and_adequate_with_enough_tests():
    rows = studies.strength_oc(strength.THRESHOLD)
    assert [r["n_tests"] for r in rows] == [8, 16, 32, 64]
    assert rows[-1]["power"] >= 0.70
    assert all(a["power"] <= b["power"] + 0.05 for a, b in zip(rows, rows[1:])), "power grows with evidence"
