import pytest

from tracebench import studies


@pytest.mark.req("SYS-2")
def test_validation_results_are_identical_on_every_run():
    a = studies.reach_calibration("fine", seeds=(101,))
    b = studies.reach_calibration("fine", seeds=(101,))
    assert a["per_seed"] == b["per_seed"]
    assert studies.strength_oc(0.95, sizes=(16,), reps=200) == studies.strength_oc(0.95, sizes=(16,), reps=200)
    assert studies.magnitude_recovery(0.1, 50, reps=100) == studies.magnitude_recovery(0.1, 50, reps=100)
