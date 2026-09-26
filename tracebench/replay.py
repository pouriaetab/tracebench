"""Replay: run a model over recorded bars exactly as it would have run live.

At each decision point t the model may use bars[0..t] and nothing after. The
outcome (did price touch the level in the next H bars?) is graded afterwards
from bars[t+1..t+H]. Keeping those two apart is the whole point: a replay that
lets the future leak into a prediction reports skill that does not exist
(REQ SYS-1, tested by changing the future and checking no past prediction moves).

Every record carries all of its inputs, so any prediction can be recomputed
from the record alone (REQ SYS-3).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

from tracebench.bars import Bar
from tracebench.levels import side, touched
from tracebench.models import reach

DEFAULT_Z = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5)


@dataclass(frozen=True)
class Prediction:
    t: int
    timestamp_ms: int
    price: float
    level: float
    side: str
    sigma: float
    horizon: int
    p: float
    touched: bool


def replay(bars: Sequence[Bar], horizon: int = 30, every: int = 25,
           z_levels: Iterable[float] = DEFAULT_Z, warmup: int = reach.VOL_LOOKBACK_BARS,
           lookback: int = reach.VOL_LOOKBACK_BARS) -> list[Prediction]:
    """Levels are placed at z * sigma_hat * sqrt(horizon) above and below the
    close, so every run spans the full range of probabilities."""
    out: list[Prediction] = []
    last = len(bars) - horizon - 1
    for t in range(max(warmup, reach.MIN_BARS_FOR_VOL), last + 1, every):
        past = bars[max(0, t + 1 - lookback): t + 1]
        sigma = reach.estimate_volatility(past, lookback)
        if sigma is None:
            continue
        price = bars[t].close
        future = bars[t + 1: t + 1 + horizon]
        for z in z_levels:
            for sign in (1, -1):
                level = price * math.exp(sign * z * sigma * math.sqrt(horizon))
                p = reach.touch_probability(price, level, sigma, horizon)
                if p is None:
                    continue
                out.append(Prediction(t, bars[t].timestamp_ms, price, level, side(price, level),
                                      sigma, horizon, p, touched(future, price, level)))
    return out


def as_rows(preds: Iterable[Prediction]) -> list[dict]:
    return [asdict(p) for p in preds]
