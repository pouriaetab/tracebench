"""Scenarios with a known true answer.

Validation needs ground truth. Real market data never says what the true
volatility or tail shape was, so each model is first validated on data generated
from a process whose parameters are chosen here. If a model cannot recover a
truth it was built for, it will not recover one it was not told.

Every generator takes a seed, so every study is reproducible (REQ SYS-2).
"""
from __future__ import annotations

import numpy as np

from tracebench.bars import Bar

MS_PER_BAR = 60_000
T0_MS = 1_700_000_000_000


def price_bars(n_bars: int, sigma: float, substeps: int = 16, seed: int = 0,
               innovations: str = "normal", df: float = 3.0,
               garch: tuple[float, float, float] | None = None,
               start: float = 100.0, profile=None) -> list[Bar]:
    """Bars from a driftless log-price random walk observed `substeps` times per
    bar. The bar's high and low are the extremes of those observations, so a
    small `substeps` reproduces coarse monitoring.

    sigma is the per-bar volatility of log-price. innovations = "normal" or
    "t" (Student-t with `df` degrees of freedom, rescaled to the same variance:
    fat tails). garch = (omega, alpha, beta) switches on GARCH(1,1) volatility
    clustering at the bar level, scaled so the long-run per-bar variance is
    still sigma**2. profile, a sequence of variance multipliers with mean 1,
    applies an intraday volatility pattern bar by bar (bar i uses
    profile[i % len(profile)]).
    """
    rng = np.random.default_rng(seed)
    n = n_bars * substeps
    if innovations == "normal":
        z = rng.standard_normal(n)
    elif innovations == "t":
        z = rng.standard_t(df, n) / np.sqrt(df / (df - 2.0))
    else:
        raise ValueError(f"unknown innovations {innovations!r}")
    if garch is None:
        bar_sigma = np.full(n_bars, sigma)
    else:
        omega, alpha, beta = garch
        if alpha + beta >= 1:
            raise ValueError("GARCH needs alpha + beta < 1")
        long_run = omega / (1 - alpha - beta)
        scale = sigma ** 2 / long_run
        h = np.empty(n_bars)
        h[0] = long_run
        eps = rng.standard_normal(n_bars)
        for t in range(1, n_bars):
            h[t] = omega + alpha * (np.sqrt(h[t - 1]) * eps[t - 1]) ** 2 + beta * h[t - 1]
        bar_sigma = np.sqrt(h * scale)
    if profile is not None:
        prof = np.asarray(profile, dtype=float)
        bar_sigma = bar_sigma * np.sqrt(prof[np.arange(n_bars) % len(prof)])
    step_sigma = np.repeat(bar_sigma, substeps) / np.sqrt(substeps)
    log_path = np.log(start) + np.concatenate([[0.0], np.cumsum(z * step_sigma)])
    prices = np.exp(log_path)
    bars = []
    for i in range(n_bars):
        seg = prices[i * substeps: (i + 1) * substeps + 1]
        bars.append(Bar(T0_MS + i * MS_PER_BAR, float(seg[0]), float(seg.max()),
                        float(seg.min()), float(seg[-1]), 0.0))
    return bars


def break_sequences(n_tests: int, p_earlier: float, p_recent: float, reps: int,
                    seed: int = 0) -> np.ndarray:
    """reps rows of n_tests Bernoulli outcomes (1 = broke). The first half uses
    p_earlier, the second half p_recent: a level whose true strength is known."""
    rng = np.random.default_rng(seed)
    half = n_tests // 2
    a = rng.random((reps, half)) < p_earlier
    b = rng.random((reps, n_tests - half)) < p_recent
    return np.concatenate([a, b], axis=1).astype(int)


def gpd_sample(n: int, xi: float, sigma: float, seed: int = 0) -> np.ndarray:
    """n draws from GPD(xi, sigma) by inverse transform."""
    u = np.random.default_rng(seed).random(n)
    if abs(xi) < 1e-12:
        return -sigma * np.log1p(-u)
    return (sigma / xi) * ((1.0 - u) ** (-xi) - 1.0)


def u_shaped_profile(n: int = 390, open_mult: float = 4.0, close_mult: float = 1.5) -> np.ndarray:
    """A stylised intraday variance pattern: high at the open, low at midday,
    rising into the close, normalised to mean 1. Real sessions look like this
    (see docs/07-field-validation.md, where the measured open-to-midday ratio
    was about 6.5)."""
    x = np.linspace(0.0, 1.0, n)
    shape = 1.0 + (open_mult - 1.0) * np.exp(-x / 0.08) + (close_mult - 1.0) * np.exp(-(1.0 - x) / 0.08)
    return shape / shape.mean()
