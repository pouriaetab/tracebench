"""The validation studies. Tests (tests/validation) and the report
(python -m tracebench.report) call the same functions, so the numbers a test
asserts on are the numbers the report prints.
"""
from __future__ import annotations

import numpy as np

from tracebench import evaluate, replay, scenarios, seasonality
from tracebench.models import magnitude, reach, strength

SIGMA = 0.002          # per bar volatility of the simulated market
N_BARS = 20_000
SEEDS = (101, 102, 103, 104, 105)

REACH_SCENARIOS = {
    "fine":   dict(substeps=16),
    "coarse": dict(substeps=1),
    "garch":  dict(substeps=16, garch=(0.02, 0.15, 0.83)),
    "fat":    dict(substeps=16, innovations="t"),
}


def reach_calibration(scenario: str, seeds=SEEDS) -> dict:
    kw = REACH_SCENARIOS[scenario]
    per_seed, all_p, all_y = [], [], []
    for s in seeds:
        preds = replay.replay(scenarios.price_bars(N_BARS, SIGMA, seed=s, **kw))
        p = np.array([x.p for x in preds])
        y = np.array([x.touched for x in preds])
        c = evaluate.calibration(p, y)
        per_seed.append({"seed": s, "n": c.n, "ece": c.ece, "brier": c.brier,
                         "over_prediction": float(p.mean() - y.mean())})
        all_p.append(p)
        all_y.append(y)
    pooled = evaluate.calibration(np.concatenate(all_p), np.concatenate(all_y))
    return {"scenario": scenario, "per_seed": per_seed, "pooled": pooled}


def assumption_checks(seeds=range(201, 209), n=5000) -> dict:
    cfg = {"normal": dict(substeps=16), "fat_tails": dict(substeps=2, innovations="t"),
           "clustered": dict(substeps=16, garch=(0.02, 0.15, 0.83))}
    out = {}
    for name, kw in cfg.items():
        out[name] = [reach.assumption_report(scenarios.price_bars(n, SIGMA, seed=s, **kw), n) for s in seeds]
    return out


def strength_oc(threshold: float, sizes=(8, 16, 32, 64), reps: int = 1000,
                mc_samples: int = 4000) -> list[dict]:
    rows = []
    for n in sizes:
        null = scenarios.break_sequences(n, 0.5, 0.5, reps, seed=1000 + n)
        alt = scenarios.break_sequences(n, 0.6, 0.3, reps, seed=2000 + n)
        fa = [strength.assess(list(r), threshold, samples=mc_samples)[0] == "strengthening" for r in null]
        pw = [strength.assess(list(r), threshold, samples=mc_samples)[0] == "strengthening" for r in alt]
        (fa_rate, fa_se), (pw_rate, pw_se) = evaluate.rate(fa), evaluate.rate(pw)
        rows.append({"n_tests": n, "false_alarm": fa_rate, "false_alarm_se": fa_se,
                     "power": pw_rate, "power_se": pw_se})
    return rows


def magnitude_recovery(xi: float, n: int, reps: int = 500, original: bool = False) -> dict:
    fit = magnitude.fit_moments_original if original else magnitude.fit_moments
    est = []
    for r in range(reps):
        f = fit(scenarios.gpd_sample(n, xi, 1.0, seed=100_000 + 1000 * n + r + int(xi * 1e4)))
        est.append(None if f is None else f[0])
    return {"xi": xi, "n": n, **evaluate.recovery(est, xi)}


def seasonal_ab(n_train: int = 120, n_test: int = 120, seed: int = 5000) -> dict:
    """A/B test of CR-2 on simulated sessions with a known intraday pattern.
    The profile is estimated from the first n_train sessions only; A and B are
    compared on the next n_test sessions."""
    prof = scenarios.u_shaped_profile()
    sessions = [scenarios.price_bars(len(prof), SIGMA, seed=seed + i, profile=prof)
                for i in range(n_train + n_test)]
    est = seasonality.estimate_profile(sessions[:n_train], len(prof))
    rows = seasonality.replay_sessions(sessions[n_train:], est)
    a = np.array([r[1] for r in rows]); b = np.array([r[2] for r in rows]); y = np.array([r[3] for r in rows])
    return {"true_profile": prof, "estimated_profile": est,
            "ece_a": evaluate.calibration(a, y).ece, "ece_b": evaluate.calibration(b, y).ece,
            **seasonality.paired_bootstrap(rows)}
