"""Traceability wiring. Every test declares the requirement(s) it verifies:

    @pytest.mark.req("R-2")
    def test_probability_falls_with_distance(): ...

At the end of the run, if TRACEBENCH_RESULTS is set, each test's requirements
and outcome are written there as JSON; tracebench/trace.py turns that into the
traceability matrix.
"""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_RESULTS: dict = {}


def pytest_configure(config):
    config.addinivalue_line("markers", "req(*ids): the requirement ids this test verifies")


def pytest_collection_modifyitems(items):
    for item in items:
        ids = [i for m in item.iter_markers("req") for i in m.args]
        item.user_properties.append(("reqs", ids))


def pytest_runtest_logreport(report):
    reqs = dict(report.user_properties).get("reqs", [])
    rec = _RESULTS.setdefault(report.nodeid, {"reqs": reqs, "outcome": "passed"})
    if report.when == "call":
        if hasattr(report, "wasxfail"):
            rec["outcome"] = "xfailed" if report.skipped else "xpassed"
            rec["reason"] = report.wasxfail
        elif report.failed:
            rec["outcome"] = "failed"
        elif report.skipped:
            rec["outcome"] = "skipped"
    elif report.failed:
        rec["outcome"] = "error"
    elif report.skipped and rec["outcome"] == "passed":
        rec["outcome"] = "xfailed" if hasattr(report, "wasxfail") else "skipped"
        if hasattr(report, "wasxfail"):
            rec["reason"] = report.wasxfail


def pytest_sessionfinish(session, exitstatus):
    out = os.environ.get("TRACEBENCH_RESULTS")
    if out:
        payload = {"run_id": os.environ.get("TRACEBENCH_RUN_ID"), "tests": _RESULTS}
        Path(out).write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
