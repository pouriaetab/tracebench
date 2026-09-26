import sys

import pytest

from tracebench import report


@pytest.mark.req("SYS-5")
@pytest.mark.parametrize("code, written, verdict", [
    (0, True, "PASS"), (1, True, "FAIL"),
    (0, False, "ENVIRONMENT ERROR"),   # claimed success but wrote nothing
    (1, False, "ENVIRONMENT ERROR"),
    (2, True, "ENVIRONMENT ERROR"),    # interrupted
    (3, True, "ENVIRONMENT ERROR"),    # internal error
    (4, False, "ENVIRONMENT ERROR"),   # usage error
    (5, False, "ENVIRONMENT ERROR"),   # no tests collected
    (None, False, "ENVIRONMENT ERROR"),  # could not even start
])
def test_run_classification(code, written, verdict):
    assert report.classify_run(code, written) == verdict


@pytest.mark.req("SYS-5")
def test_missing_interpreter_is_an_environment_error(tmp_path):
    verdict, _, log = report.run_tests(python=str(tmp_path / "no-such-python"),
                                       results=tmp_path / "r.json")
    assert verdict == "ENVIRONMENT ERROR" and "could not start" in log


@pytest.mark.req("SYS-5")
def test_environment_error_report_shows_why_not_results():
    text = report.test_report("ENVIRONMENT ERROR", {}, "ModuleNotFoundError: numpy")
    assert "ENVIRONMENT ERROR" in text and "ModuleNotFoundError" in text
    assert "| unit |" not in text


@pytest.mark.req("SYS-5")
def test_results_left_by_an_earlier_run_are_not_trusted(tmp_path):
    """A stale results file from a previous run must not turn a run that
    could not start into a PASS."""
    stale = tmp_path / "r.json"
    stale.write_text('{"run_id": "an-older-run", "tests": {}}', encoding="utf-8")
    verdict, _, _ = report.run_tests(python=str(tmp_path / "no-such-python"), results=stale)
    assert verdict == "ENVIRONMENT ERROR"
