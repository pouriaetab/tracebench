"""Validation measures. Each returns plain numbers so a test can assert on them
and a report can print them.

Calibration: when the model says 30%, does the event happen about 30% of the
time? Predictions are grouped into bins by predicted probability, and each bin's
average prediction is compared with its observed frequency.
  Brier score: mean (p - outcome)^2, lower is better.
  ECE (expected calibration error): the bin size weighted mean gap between
  predicted and observed. 0 is perfect.

Operating characteristic: for a classifier with a threshold, the false alarm
rate (says 'changed' when nothing changed) and the power (says 'changed' when
it did), measured on scenarios where the truth is known.

Parameter recovery: fit many simulated samples with a known parameter and report
the bias (average error) and RMSE (typical size of the error).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class CalibrationBin:
    lo: float
    hi: float
    n: int
    mean_pred: float
    observed: float
    se: float


@dataclass(frozen=True)
class Calibration:
    n: int
    brier: float
    ece: float
    bins: list[CalibrationBin]


def calibration(p: Sequence[float], y: Sequence[bool], n_bins: int = 10) -> Calibration:
    p = np.asarray(p, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(p) == 0 or len(p) != len(y):
        raise ValueError("need matching, non-empty predictions and outcomes")
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, n_bins - 1)
    bins, ece = [], 0.0
    for k in range(n_bins):
        m = idx == k
        n = int(m.sum())
        if n == 0:
            continue
        mp, ob = float(p[m].mean()), float(y[m].mean())
        se = math.sqrt(max(ob * (1 - ob), 1e-12) / n)
        bins.append(CalibrationBin(float(edges[k]), float(edges[k + 1]), n, mp, ob, se))
        ece += n / len(p) * abs(mp - ob)
    return Calibration(len(p), float(np.mean((p - y) ** 2)), float(ece), bins)


def rate(flags: Sequence[bool]) -> tuple[float, float]:
    """(proportion, standard error)."""
    a = np.asarray(flags, dtype=float)
    q = float(a.mean())
    return q, math.sqrt(max(q * (1 - q), 1e-12) / len(a))


def recovery(estimates: Sequence[float], truth: float) -> dict:
    e = np.asarray([x for x in estimates if x is not None and math.isfinite(x)], dtype=float)
    if len(e) == 0:
        return {"n_fits": 0, "bias": None, "rmse": None}
    return {"n_fits": int(len(e)), "bias": float(e.mean() - truth),
            "rmse": float(math.sqrt(np.mean((e - truth) ** 2))),
            "p05": float(np.quantile(e, 0.05)), "p95": float(np.quantile(e, 0.95))}
