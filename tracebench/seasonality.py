"""Intraday volatility seasonality: the change validated by the A/B test in
docs/07-field-validation.md (change CR-2).

The problem. Model R estimates volatility from the last bars and assumes the
next bars will be just as volatile. Within a trading day that is false in a
predictable way: volatility is highest at the open, lowest around midday and
rises into the close. At midday the trailing window still remembers the
morning, so the model over-predicts touches.

The fix. Learn the average shape of volatility across the session from past
sessions only, then rescale the trailing estimate by how volatile the coming
bars usually are compared with the bars it was measured on:

    sigma_adjusted = sigma * sqrt( mean(profile[future]) / mean(profile[past]) )

profile[m] is the average squared return at minute m of the session, each
session first normalised by its own average so busy days do not dominate.
"""
from __future__ import annotations

import math
from typing import Iterable, Sequence

import numpy as np

from tracebench.bars import Bar
from tracebench.models import reach
from tracebench.replay import replay


def estimate_profile(sessions: Iterable[Sequence[Bar]], length: int, smooth: int = 5) -> np.ndarray:
    """Average normalised squared 1-bar log return at each position in the
    session. Sessions must be aligned: bar i of every session is minute i."""
    acc = np.zeros(length)
    cnt = np.zeros(length)
    for s in sessions:
        c = np.array([b.close for b in s], dtype=float)
        if len(c) < 3 or np.any(c <= 0):
            continue
        r2 = np.diff(np.log(c)) ** 2
        m = r2.mean()
        if m <= 0:
            continue
        pos = np.arange(1, len(c))
        keep = pos < length
        np.add.at(acc, pos[keep], r2[keep] / m)
        np.add.at(cnt, pos[keep], 1)
    prof = acc / np.maximum(cnt, 1)
    prof[0] = prof[1] if length > 1 else 1.0
    if smooth > 1:
        prof = np.convolve(prof, np.ones(smooth) / smooth, mode="same")
    return prof / prof.mean()


def seasonal_factor(profile: np.ndarray, past: Sequence[int], future: Sequence[int]) -> float:
    past_v = float(np.mean(profile[list(past)]))
    fut_v = float(np.mean(profile[list(future)]))
    if past_v <= 0 or fut_v <= 0:
        return 1.0
    return math.sqrt(fut_v / past_v)


def replay_sessions(sessions: Sequence[Sequence[Bar]], profile: np.ndarray | None,
                    horizon: int = 30, every: int = 10, lookback: int = 120,
                    positions: Sequence[Sequence[int]] | None = None) -> list[tuple[int, float, float, bool]]:
    """Replay each session separately (nothing crosses the overnight gap).
    Returns (session index, baseline p, adjusted p, touched). positions[i][j]
    is the minute-of-session of bar j in session i; default is 0, 1, 2, ..."""
    out = []
    for si, s in enumerate(sessions):
        pos = list(positions[si]) if positions is not None else list(range(len(s)))
        for p in replay(list(s), horizon=horizon, every=every, warmup=lookback, lookback=lookback):
            adj = p.p
            if profile is not None:
                past = pos[max(0, p.t + 2 - lookback): p.t + 1]
                fut = pos[p.t + 1: p.t + 1 + horizon]
                f = seasonal_factor(profile, past, fut)
                adj = reach.touch_probability(p.price, p.level, p.sigma * f, p.horizon)
            out.append((si, p.p, adj, p.touched))
    return out


def paired_bootstrap(rows: Sequence[tuple[int, float, float, bool]], reps: int = 2000,
                     seed: int = 0) -> dict:
    """Difference in Brier score (B minus A) with a 95% interval, resampling
    whole sessions: predictions within a session are not independent, so the
    session is the unit of resampling (a cluster bootstrap)."""
    by = {}
    for si, a, b, y in rows:
        d = by.setdefault(si, [0.0, 0.0, 0])
        d[0] += (a - y) ** 2
        d[1] += (b - y) ** 2
        d[2] += 1
    keys = sorted(by)
    A = np.array([by[k][0] for k in keys])
    B = np.array([by[k][1] for k in keys])
    N = np.array([by[k][2] for k in keys])
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(reps):
        i = rng.integers(0, len(keys), len(keys))
        diffs.append((B[i].sum() - A[i].sum()) / N[i].sum())
    d = np.array(diffs)
    return {"sessions": len(keys), "predictions": int(N.sum()),
            "brier_a": float(A.sum() / N.sum()), "brier_b": float(B.sum() / N.sum()),
            "diff": float((B.sum() - A.sum()) / N.sum()),
            "ci_low": float(np.quantile(d, 0.025)), "ci_high": float(np.quantile(d, 0.975)),
            "share_b_better": float(np.mean(d < 0))}
