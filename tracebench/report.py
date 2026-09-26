"""One command for the whole V&V run:

    python -m tracebench.report

1. Runs the test suite (unit, integration, system, validation) and records which
   requirement each test verifies.
2. Classifies the run honestly: PASS, FAIL, or ENVIRONMENT ERROR when the suite
   could not run at all (a crash, a missing dependency). An environment error is
   never reported as a pass or as test failures (REQ SYS-5).
3. Writes reports/: TEST_REPORT.md, TRACEABILITY.md, VALIDATION_REPORT.md, and
   regenerates docs/02-requirements.md from the requirement registry.

Exit code: 0 PASS, 1 FAIL, 3 ENVIRONMENT ERROR.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from collections import Counter
from pathlib import Path

from tracebench import studies, trace
from tracebench.models import strength
from tracebench.requirements import LEVELS, REQUIREMENTS

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
EXIT = {"PASS": 0, "FAIL": 1, "ENVIRONMENT ERROR": 3}


def classify_run(exit_code: int | None, results_written: bool) -> str:
    """pytest exits 0 when everything passed and 1 when tests failed. Anything
    else (interrupted, internal error, usage error, no tests collected) or a
    missing results file means the suite did not run to completion."""
    if exit_code == 0 and results_written:
        return "PASS"
    if exit_code == 1 and results_written:
        return "FAIL"
    return "ENVIRONMENT ERROR"


def run_tests(python: str = sys.executable, results: Path | None = None,
              extra: list[str] | None = None) -> tuple[str, Path, str]:
    results = results or (REPORTS / "results.json")
    results.parent.mkdir(parents=True, exist_ok=True)
    # A results file left by an earlier run must never be read as this run's
    # results. Each run gets an id; results only count if they carry it.
    run_id = uuid.uuid4().hex
    env = dict(os.environ, TRACEBENCH_RESULTS=str(results), TRACEBENCH_RUN_ID=run_id)
    cmd = [python, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests", *(extra or [])]
    try:
        proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
        code, log = proc.returncode, proc.stdout + proc.stderr
    except OSError as e:
        code, log = None, f"could not start the test run: {e}"
    return classify_run(code, trace.run_id_of(results) == run_id), results, log


def test_report(verdict: str, results: dict, log_tail: str) -> str:
    by_level = {lv: Counter() for lv in LEVELS}
    for nodeid, r in results.items():
        parts = nodeid.split("/")
        level = parts[1] if len(parts) > 2 and parts[1] in by_level else "other"
        by_level.setdefault(level, Counter())[r["outcome"]] += 1
    lines = ["# Test report", "", f"**Verdict: {verdict}**", "",
             "| Level | Passed | Failed | Known issue (xfail) | Other |", "|:--|--:|--:|--:|--:|"]
    for lv, c in by_level.items():
        if not c:
            continue
        other = sum(v for k, v in c.items() if k not in ("passed", "failed", "xfailed"))
        lines.append(f"| {lv} | {c['passed']} | {c['failed']} | {c['xfailed']} | {other} |")
    bad = [(n, r) for n, r in results.items() if r["outcome"] in ("failed", "error", "xpassed")]
    if bad:
        lines += ["", "## Failures", ""] + [f"- `{n}` ({r['outcome']})" for n, r in bad]
    kis = [(n, r) for n, r in results.items() if r["outcome"] == "xfailed"]
    if kis:
        lines += ["", "## Known issues (accepted deviations)", ""] + \
                 [f"- `{n}`: {r.get('reason', '')}" for n, r in kis]
    if verdict == "ENVIRONMENT ERROR":
        lines += ["", "## Why the run could not complete", "", "```", log_tail[-3000:], "```"]
    return "\n".join(lines) + "\n"


def _fmt(x, nd=3):
    return "n/a" if x is None else f"{x:.{nd}f}"


def validation_report() -> str:
    L = ["# Validation report", "",
         "Every number below is produced by `tracebench/studies.py` from seeded scenarios, so the "
         "report is identical on every run (SYS-2). Tests in `tests/validation/` assert the thresholds.", ""]
    L += ["## VAL-R1, VAL-R2: touch probability calibration (R-4, R-5)", "",
          "Simulated market: driftless random walk, per bar volatility 0.2%, 20,000 bars per seed, "
          "levels at 0.25 to 2.5 expected moves above and below price, 30 bar horizon.", "",
          "| Scenario | What it breaks | ECE per seed | Mean overprediction |", "|:--|:--|:--|--:|"]
    what = {"fine": "nothing (16 observations per bar)", "coarse": "continuous monitoring (1 observation per bar)",
            "garch": "constant volatility (GARCH clustering)", "fat": "normal returns (Student-t, 3 df)"}
    pooled = {}
    for sc in studies.REACH_SCENARIOS:
        r = studies.reach_calibration(sc)
        pooled[sc] = r["pooled"]
        eces = ", ".join(_fmt(s["ece"]) for s in r["per_seed"])
        over = sum(s["over_prediction"] for s in r["per_seed"]) / len(r["per_seed"])
        L.append(f"| {sc} | {what[sc]} | {eces} | {over * 100:+.1f} pts |")
    for sc in ("fine", "coarse"):
        L += ["", f"Reliability table, {sc} (all seeds pooled):", "",
              "| Predicted bin | n | Mean predicted | Observed | ± SE |", "|:--|--:|--:|--:|--:|"]
        for b in pooled[sc].bins:
            L.append(f"| {b.lo:.1f} to {b.hi:.1f} | {b.n} | {b.mean_pred:.3f} | {b.observed:.3f} | {b.se:.3f} |")
    L += ["", "Reading it: with fine monitoring the model is calibrated to within about a point. The small "
          "residual overprediction that remains is itself discrete monitoring (16 looks per bar is still "
          "not continuous) plus noise in the estimated volatility. With one observation per bar the model "
          "overpredicts in every bin, because the formula assumes every instant is watched (discrete "
          "monitoring bias). Clustered volatility overpredicts too: the trailing volatility estimate lags "
          "the regime.", ""]
    ab = studies.seasonal_ab()
    L += ["## VAL-R5: intraday seasonality A/B test on simulated sessions (R-7, CR-2)", "",
          "240 simulated sessions of 390 one minute bars with a U-shaped volatility pattern. The pattern "
          "is learned from the first 120 sessions only; A (baseline) and B (seasonality adjusted) are "
          "compared on the last 120.", "",
          "| | First 30 min | Midday | Last 30 min |", "|:--|--:|--:|--:|",
          f"| True pattern | {ab['true_profile'][:30].mean():.2f} | {ab['true_profile'][150:240].mean():.2f} | "
          f"{ab['true_profile'][-30:].mean():.2f} |",
          f"| Learned from training sessions | {ab['estimated_profile'][:30].mean():.2f} | "
          f"{ab['estimated_profile'][150:240].mean():.2f} | {ab['estimated_profile'][-30:].mean():.2f} |", "",
          "| Variant | ECE | Brier |", "|:--|--:|--:|",
          f"| A baseline | {ab['ece_a']:.4f} | {ab['brier_a']:.5f} |",
          f"| B seasonality adjusted | {ab['ece_b']:.4f} | {ab['brier_b']:.5f} |", "",
          f"Brier B minus A {ab['diff']:+.5f}, 95% session bootstrap interval [{ab['ci_low']:+.5f}, "
          f"{ab['ci_high']:+.5f}], {ab['predictions']:,} predictions in {ab['sessions']} sessions. "
          "The same test on real market data is in docs/07-field-validation.md.", ""]
    L += ["## VAL-R3: assumption checks (R-6)", "", "8 seeds of 5,000 bars each.", "",
          "| Data | Excess kurtosis (range) | Clustering (range) | Flagged fat tails | Flagged clustering |",
          "|:--|:--|:--|--:|--:|"]
    for name, reps in studies.assumption_checks().items():
        k = [r["excess_kurtosis"] for r in reps]
        c = [r["vol_clustering"] for r in reps]
        L.append(f"| {name} | {min(k):.2f} to {max(k):.2f} | {min(c):.3f} to {max(c):.3f} | "
                 f"{sum(r['fat_tails'] for r in reps)}/{len(reps)} | {sum(r['clustered_volatility'] for r in reps)}/{len(reps)} |")
    L += ["", "## VAL-S1: strengthening signal, operating characteristic (S-5, S-6)", "",
          "1,000 simulated levels per cell. False alarm: break rate unchanged at 0.5. "
          "Power: break rate falls from 0.6 to 0.3.", ""]
    for thr, label in ((strength.INHERITED_THRESHOLD, "inherited design (KI-1)"),
                       (strength.THRESHOLD, "adopted (CR-1)")):
        L += [f"Threshold {thr}, {label}:", "", "| Tests | False alarm | Power |", "|--:|--:|--:|"]
        for r in studies.strength_oc(thr):
            L.append(f"| {r['n_tests']} | {r['false_alarm']:.3f} ± {r['false_alarm_se']:.3f} | "
                     f"{r['power']:.3f} ± {r['power_se']:.3f} |")
        L.append("")
    L += ["## VAL-M1: tail shape recovery (M-3) and defect TB-1", "",
          "500 fits per cell, GPD samples with sigma = 1.", "",
          "| True xi | n | Bias (fixed) | RMSE (fixed) | Bias (original) |", "|--:|--:|--:|--:|--:|"]
    for xi in (0.0, 0.1, 0.2, 0.35):
        for n in (20, 50, 200, 1000):
            a = studies.magnitude_recovery(xi, n)
            b = studies.magnitude_recovery(xi, n, original=True)
            L.append(f"| {xi} | {n} | {a['bias']:+.3f} | {a['rmse']:.3f} | {b['bias']:+.3f} |")
    L += ["", "Reading it: the original estimator's bias grows with the true xi and never shrinks with more "
          "data, the signature of a formula error rather than noise. The fixed estimator's bias shrinks "
          "toward zero as n grows. Below about 50 samples, and for xi near 0.35, even the fixed "
          "estimator is biased low: a documented limit of the method of moments.", ""]
    return "\n".join(L)


def requirements_doc() -> str:
    L = ["# Requirements", "", "Generated from `tracebench/requirements.py`, the single source of truth. "
         "Status for each one is in `reports/TRACEABILITY.md`.", ""]
    area = None
    for r in REQUIREMENTS:
        if r.area != area:
            area = r.area
            L += [f"## {area.capitalize()}", "", "| ID | Level | Requirement | Why |", "|:--|:--|:--|:--|"]
        L.append(f"| **{r.id}** | {r.level} | {r.text} | {r.rationale} |")
        if r is REQUIREMENTS[-1] or REQUIREMENTS[REQUIREMENTS.index(r) + 1].area != area:
            L.append("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tracebench.report")
    ap.add_argument("--no-validation-report", action="store_true",
                    help="skip regenerating VALIDATION_REPORT.md (the tests still validate)")
    args = ap.parse_args(argv)
    REPORTS.mkdir(exist_ok=True)
    (ROOT / "docs" / "02-requirements.md").write_text(requirements_doc(), encoding="utf-8")
    verdict, rpath, log = run_tests()
    results = trace.load_results(rpath) if verdict != "ENVIRONMENT ERROR" else {}
    (REPORTS / "TEST_REPORT.md").write_text(test_report(verdict, results, log), encoding="utf-8")
    if results:
        (REPORTS / "TRACEABILITY.md").write_text(trace.to_markdown(trace.matrix(results)), encoding="utf-8")
    if not args.no_validation_report and verdict != "ENVIRONMENT ERROR":
        (REPORTS / "VALIDATION_REPORT.md").write_text(validation_report(), encoding="utf-8")
    print(f"tracebench: {verdict}  (reports in {REPORTS.relative_to(ROOT)}/)")
    if verdict == "ENVIRONMENT ERROR":
        print(log[-2000:])
    return EXIT[verdict]


if __name__ == "__main__":
    sys.exit(main())
