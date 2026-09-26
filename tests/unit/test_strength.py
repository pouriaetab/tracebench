import pytest

from tracebench.models import strength


@pytest.mark.req("S-1")
def test_conjugate_update():
    assert strength.posterior(3, 7) == (4.0, 8.0)
    assert strength.posterior_mean(4.0, 8.0) == pytest.approx(1 / 3)


@pytest.mark.req("S-1")
def test_negative_counts_rejected():
    with pytest.raises(ValueError):
        strength.posterior(-1, 3)


@pytest.mark.req("S-2")
@pytest.mark.parametrize("n", [0, 1, 5, 7])
def test_too_few_tests_is_forming(n):
    assert strength.assess([1, 0] * (n // 2) + [1] * (n % 2)) == ("forming", None)


@pytest.mark.req("S-3")
def test_same_outcomes_same_answer():
    seq = [1, 1, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0]
    assert strength.assess(seq) == strength.assess(seq)


@pytest.mark.req("S-4")
@pytest.mark.parametrize("b, h", [(0, 0), (2, 2), (5, 5), (10, 30)])
def test_identical_evidence_reads_as_no_change(b, h):
    p = strength.prob_break_rate_fell(strength.posterior(b, h), strength.posterior(b, h))
    assert abs(p - 0.5) <= 0.02


@pytest.mark.req("S-2")
def test_clear_change_is_labelled():
    earlier, recent = [1] * 10, [0] * 10
    label, p = strength.assess(earlier + recent)
    assert label == "strengthening" and p > 0.99
    assert strength.assess(recent + earlier)[0] == "weakening"
