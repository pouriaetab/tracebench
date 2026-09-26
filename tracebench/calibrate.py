"""Validate the touch model on your own bars.

    python -m tracebench.calibrate path/to/bars.csv [--horizon 30] [--every 25]

CSV columns: timestamp_ms, open, high, low, close[, volume]. Prints the rows the
loader rejected and why, the assumption checks on your data, and the calibration
table: whether the model's probabilities match how often price actually touched.
"""
from __future__ import annotations

import argparse
import sys

from tracebench import evaluate, replay
from tracebench.bars import load_csv
from tracebench.models import reach


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tracebench.calibrate")
    ap.add_argument("csv")
    ap.add_argument("--horizon", type=int, default=30)
    ap.add_argument("--every", type=int, default=25)
    a = ap.parse_args(argv)
    bars, rejects = load_csv(a.csv)
    print(f"loaded {len(bars)} bars, rejected {len(rejects)}")
    for r in rejects[:20]:
        print(f"  line {r.line}: {r.reason}")
    if len(bars) < reach.VOL_LOOKBACK_BARS + a.horizon + 1:
        print(f"not enough bars: need at least {reach.VOL_LOOKBACK_BARS + a.horizon + 1}")
        return 2
    checks = reach.assumption_report(bars, lookback=len(bars))
    print(f"excess kurtosis {checks['excess_kurtosis']:.2f}"
          f"{'  <- fat tails: expect some miscalibration' if checks['fat_tails'] else ''}")
    print(f"volatility clustering {checks['vol_clustering']:.3f}"
          f"{'  <- clustered: expect over-prediction' if checks['clustered_volatility'] else ''}")
    preds = replay.replay(bars, horizon=a.horizon, every=a.every)
    c = evaluate.calibration([p.p for p in preds], [p.touched for p in preds])
    print(f"\n{c.n} predictions   Brier {c.brier:.4f}   ECE {c.ece:.4f}\n")
    print(f"{'bin':>11} {'n':>7} {'predicted':>10} {'observed':>9}")
    for b in c.bins:
        print(f"{b.lo:4.1f} to {b.hi:3.1f} {b.n:7d} {b.mean_pred:10.3f} {b.observed:9.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
