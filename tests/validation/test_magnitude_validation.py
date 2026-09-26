import pytest

from tracebench import studies


@pytest.mark.req("M-3")
@pytest.mark.parametrize("xi", [0.0, 0.1, 0.2])
def test_recovers_a_known_tail_shape(xi):
    r = studies.magnitude_recovery(xi, 200)
    assert r["n_fits"] == 500
    assert abs(r["bias"]) <= 0.05 and r["rmse"] <= 0.10, r


@pytest.mark.req("M-3")
@pytest.mark.parametrize("xi", [0.1, 0.2])
def test_the_original_estimator_would_have_failed(xi):
    """Keeps defect TB-1 visible: the inherited estimator fails the same check."""
    r = studies.magnitude_recovery(xi, 200, original=True)
    assert abs(r["bias"]) > 0.05
