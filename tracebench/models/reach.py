"""Model R: the probability that price touches a level within a horizon.

Method. If log-price moves like a driftless Brownian motion with per-bar
volatility sigma, the chance that it touches a barrier at log-distance d within
T bars has a closed form from the reflection principle:

    P(touch) = 2 * Phi( -d / (sigma * sqrt(T)) )

sigma is estimated from recent bars (realized volatility: the standard deviation
of log-returns over a trailing window). Drift is fixed at zero because a drift
estimated from a few hundred bars is mostly noise at these horizons.

Blend. When a level has a history of real touches, the empirical touch rate is
better evidence than the formula. The two are combined with an empirical-Bayes
weight w = n / (n + k): pure model with no history, mostly empirical once n is
well above k.

Assumptions, and what breaks them:
  1. Continuous monitoring. The formula watches every instant; bars only record
     the high and low. With coarse bars the formula overstates touches
     (discrete monitoring bias). See VAL-R2.
  2. Constant volatility. Real volatility clusters. See VAL-R3.
  3. Normal returns. Real returns have fat tails. The two assumption checks
     below measure 2 and 3 on the data actually used, so a report can say when
     the formula is being used outside its assumptions (REQ R-6).
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

import numpy as np

from tracebench.bars import Bar

VOL_LOOKBACK_BARS = 300
MIN_BARS_FOR_VOL = 20
SHRINKAGE_K = 15.0


def log_returns(bars: Sequence[Bar], lookback: int = VOL_LOOKBACK_BARS) -> Optional[np.ndarray]:
    window = bars[-lookback:] if len(bars) > lookback else bars
    if len(window) < MIN_BARS_FOR_VOL:
        return None
    closes = np.fromiter((b.close for b in window), dtype=np.float64, count=len(window))
    if np.any(closes <= 0):
        return None
    r = np.diff(np.log(closes))
    return r if len(r) >= 2 else None


def estimate_volatility(bars: Sequence[Bar], lookback: int = VOL_LOOKBACK_BARS) -> Optional[float]:
    """Realized volatility per bar, or None when there is not enough history.
    None is an answer: 'insufficient evidence', never a guessed number (R-1)."""
    r = log_returns(bars, lookback)
    if r is None:
        return None
    s = float(r.std(ddof=1))
    return s if s > 0 else None


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def touch_probability(price: float, level: float, sigma: Optional[float],
                      horizon_bars: int) -> Optional[float]:
    """P(touch within horizon) as a fraction in [0, 1], or None for unusable
    inputs. A level at the current price has probability 1."""
    if sigma is None or not math.isfinite(sigma) or sigma <= 0:
        return None
    if price <= 0 or level <= 0 or horizon_bars <= 0:
        return None
    d = abs(math.log(level / price))
    p = 2.0 * norm_cdf(-d / (sigma * math.sqrt(horizon_bars)))
    return min(max(p, 0.0), 1.0)


def shrinkage_weight(n: int, k: float = SHRINKAGE_K) -> float:
    return 0.0 if n <= 0 else n / (n + k)


def blend(empirical: Optional[float], n: int, model: Optional[float],
          k: float = SHRINKAGE_K) -> tuple[Optional[float], float]:
    """(blended probability, weight on the empirical side). Falls back to
    whichever side has a number; returns (None, 0) when neither does."""
    if model is None:
        return empirical, (1.0 if empirical is not None else 0.0)
    if empirical is None:
        return model, 0.0
    w = shrinkage_weight(n, k)
    return w * empirical + (1 - w) * model, w


def excess_kurtosis(bars: Sequence[Bar], lookback: int = VOL_LOOKBACK_BARS) -> Optional[float]:
    """Assumption check for normal returns: ~0 for normal data, > 0 for fat tails."""
    r = log_returns(bars, lookback)
    if r is None or r.std() == 0:
        return None
    z = r - r.mean()
    return float((z ** 4).mean() / r.var() ** 2 - 3.0)


def volatility_clustering(bars: Sequence[Bar], lookback: int = VOL_LOOKBACK_BARS) -> Optional[float]:
    """Assumption check for constant volatility: lag-1 autocorrelation of squared
    returns (an ARCH-effect proxy). ~0 when volatility is constant."""
    r = log_returns(bars, lookback)
    if r is None or len(r) < 3:
        return None
    sq = r ** 2
    a, b = sq[:-1], sq[1:]
    if a.std() == 0 or b.std() == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def hyperparameters() -> dict:
    return {"vol_lookback_bars": VOL_LOOKBACK_BARS, "min_bars_for_vol": MIN_BARS_FOR_VOL,
            "shrinkage_k": SHRINKAGE_K}


# Flag levels for the two assumption checks, set from validation (VAL-R4): on
# 8 seeds of 5,000 normal constant-volatility bars, |kurtosis| stayed under 0.2
# and |clustering| under 0.05, while fat-tailed data gave kurtosis above 5 and
# clustered data gave clustering above 0.1.
KURTOSIS_FLAG = 1.0
CLUSTERING_FLAG = 0.08


def assumption_report(bars: Sequence[Bar], lookback: int = VOL_LOOKBACK_BARS) -> dict:
    """What the data says about the model's assumptions, with a flag for each
    one that looks violated. None means there was not enough data to check."""
    k = excess_kurtosis(bars, lookback)
    c = volatility_clustering(bars, lookback)
    return {"excess_kurtosis": k, "fat_tails": None if k is None else k > KURTOSIS_FLAG,
            "vol_clustering": c, "clustered_volatility": None if c is None else c > CLUSTERING_FLAG}
