import pytest

from tracebench import studies


@pytest.mark.req("R-4")
def test_calibrated_under_its_own_assumptions():
    r = studies.reach_calibration("fine")
    for s in r["per_seed"]:
        assert s["ece"] <= 0.03, f"seed {s['seed']}: ECE {s['ece']:.4f}"


@pytest.mark.req("R-5")
@pytest.mark.parametrize("scenario", ["coarse", "garch"])
def test_documented_limit_reproduces(scenario):
    r = studies.reach_calibration(scenario)
    over = sum(s["over_prediction"] for s in r["per_seed"]) / len(r["per_seed"])
    assert over >= 0.02, f"{scenario}: expected over-prediction, got {over:+.4f}"
    fine = studies.reach_calibration("fine")
    assert r["pooled"].ece > fine["pooled"].ece


@pytest.mark.req("R-6")
def test_assumption_checks_flag_violations_and_only_violations():
    res = studies.assumption_checks()
    assert not any(r["fat_tails"] or r["clustered_volatility"] for r in res["normal"])
    assert all(r["fat_tails"] for r in res["fat_tails"])
    assert all(r["clustered_volatility"] for r in res["clustered"])
