"""Model M: how far can a move run after price tests a level? (tail size)

Peaks-over-threshold: take the post-test excursions, keep the part of each one
that exceeds a threshold u (here the sample median), and fit a Generalized
Pareto Distribution (GPD) to those excesses. The Pickands-Balkema-de Haan
theorem is why the GPD is the right family for excesses over a high threshold.

    P(Y > y) = (1 + xi * y / sigma) ** (-1 / xi)      y >= 0

xi is the tail shape: > 0 heavy tail, 0 exponential, < 0 bounded tail.

Fit by the method of moments (Hosking and Wallis, 1987), closed form, suited to
small samples:

    r = mean^2 / variance
    xi    = 0.5 * (1 - r)
    sigma = 0.5 * mean * (r + 1)

Defect TB-1 (found by VAL-M1, fixed here). The original code returned
0.5 * (r - 1): Hosking and Wallis write the GPD with k = -xi, and their k was
copied in as xi. Every heavy tail came out as a bounded tail. Unit tests on the
formula's own algebra could not see it; recovering a known xi from simulated
data did. tests/unit/test_magnitude.py keeps a regression test.

Known limit. Moments need a finite variance, so the method only works for
xi < 0.5, and it is badly biased well before that (VAL-M2).
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

import numpy as np

THRESHOLD_QUANTILE = 0.5
MIN_EXCEEDANCES = 5


def fit_moments(excesses: Sequence[float]) -> Optional[tuple[float, float]]:
    """(xi, sigma) or None when there are too few excesses or they are degenerate."""
    y = np.asarray(excesses, dtype=np.float64)
    if len(y) < MIN_EXCEEDANCES or not np.all(np.isfinite(y)) or np.any(y < 0):
        return None
    m, v = float(y.mean()), float(y.var(ddof=1))
    if m <= 0 or v <= 0:
        return None
    r = m * m / v
    xi = 0.5 * (1.0 - r)
    sigma = 0.5 * m * (r + 1.0)
    return (xi, sigma) if sigma > 0 else None


def fit_moments_original(excesses: Sequence[float]) -> Optional[tuple[float, float]]:
    """The inherited, defective estimator (sign of xi flipped). Kept only so
    the validation report can show what the defect did; never used otherwise."""
    fit = fit_moments(excesses)
    return None if fit is None else (-fit[0], fit[1])


def split_threshold(excursions: Sequence[float], q: float = THRESHOLD_QUANTILE
                    ) -> Optional[tuple[float, np.ndarray, float]]:
    """(threshold u, excesses over u, exceedance rate) for a sample of excursions."""
    x = np.asarray(excursions, dtype=np.float64)
    if len(x) == 0:
        return None
    u = float(np.quantile(x, q))
    exc = x[x > u] - u
    return u, exc, len(exc) / len(x)


def survival(y: float, xi: float, sigma: float) -> Optional[float]:
    """P(Y > y) for an excess y >= 0."""
    if sigma <= 0 or y < 0:
        return None
    if abs(xi) < 1e-9:
        return math.exp(-y / sigma)
    base = 1.0 + xi * y / sigma
    if base <= 0:
        return 0.0
    return base ** (-1.0 / xi)


def tail_probability(x: float, u: float, rate: float, xi: float, sigma: float) -> Optional[float]:
    """Unconditional P(X > x) for x >= u."""
    if x < u:
        return None
    s = survival(x - u, xi, sigma)
    return None if s is None else max(0.0, min(1.0, rate * s))


def quantile(p: float, u: float, rate: float, xi: float, sigma: float) -> Optional[float]:
    """The move size x with P(X > x) = p. Only defined inside the fitted tail
    (0 < p <= rate); returns None rather than extrapolating below u."""
    if not (0.0 < p <= rate) or sigma <= 0:
        return None
    ratio = p / rate
    y = -sigma * math.log(ratio) if abs(xi) < 1e-9 else (sigma / xi) * (ratio ** (-xi) - 1.0)
    return u + y if (y >= 0 and math.isfinite(y)) else None


def hyperparameters() -> dict:
    return {"threshold_quantile": THRESHOLD_QUANTILE, "min_exceedances": MIN_EXCEEDANCES}
