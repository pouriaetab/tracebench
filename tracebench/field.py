"""Field validation: run model R on real one minute bars and A/B test the
seasonality adjustment (CR-2) on held out months.

    python -m tracebench.field DATA_DIR --split-month 6 [--tz America/New_York]

DATA_DIR holds one file per symbol per month, CSV (the loader's columns) or
Parquet (needs pyarrow). The symbol is the file name, so DATA_DIR/2026/01/SPY.csv
and DATA_DIR/SPY_2026-01.parquet both work as long as the stem starts with the
symbol followed by '.', '_' or nothing else.

What it does:
  1. Loads every file through the same quarantining loader as the rest of the
     project and counts what was rejected and why.
  2. Keeps the regular session (09:30 to 16:00 in --tz) and splits it into one
     series per symbol per day, so no prediction spans an overnight gap.
  3. Baseline calibration over every full session (A).
  4. Learns the intraday volatility profile from sessions up to --split-month
     and compares A with the adjusted model (B) on the later sessions only,
     with a session-level paired bootstrap.
Nothing here needs the raw data to be public: the output is aggregate.
"""
from __future__ import annotations

import argparse
import collections
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from tracebench import evaluate
from tracebench.bars import Bar, load_csv, validate_bar
from tracebench.seasonality import estimate_profile, paired_bootstrap, replay_sessions

SESSION_OPEN, SESSION_CLOSE, SESSION_LEN = 570, 960, 390   # minutes after midnight
MIN_SESSION_BARS = 360


def _read(path: Path) -> tuple[list[Bar], collections.Counter]:
    rejects: collections.Counter = collections.Counter()
    if path.suffix == ".csv":
        bars, rej = load_csv(path)
        for r in rej:
            rejects[r.reason] += 1
        return bars, rejects
    import pyarrow.parquet as pq  # optional dependency, only for Parquet input
    t = pq.read_table(path, columns=["timestamp_ms", "open", "high", "low", "close", "volume"]).to_pydict()
    bars = []
    for i in range(len(t["timestamp_ms"])):
        b = Bar(int(t["timestamp_ms"][i]), float(t["open"][i]), float(t["high"][i]), float(t["low"][i]),
                float(t["close"][i]), float(t["volume"][i] or 0.0))
        why = validate_bar(b)
        if why:
            rejects[why] += 1
        else:
            bars.append(b)
    return bars, rejects


def load_sessions(data_dir: Path, tz: str):
    zone = ZoneInfo(tz)
    per_symbol = collections.defaultdict(dict)
    stats = {"files": 0, "rows": 0, "rejected": collections.Counter(), "duplicates": 0}
    for f in sorted(list(data_dir.rglob("*.csv")) + list(data_dir.rglob("*.parquet"))):
        sym = f.stem.split("_")[0].split(".")[0]
        bars, rej = _read(f)
        stats["files"] += 1
        stats["rows"] += len(bars) + sum(rej.values())
        stats["rejected"] += rej
        for b in bars:
            if b.timestamp_ms in per_symbol[sym]:
                stats["duplicates"] += 1
            per_symbol[sym][b.timestamp_ms] = b
    sessions = collections.defaultdict(list)
    for sym, d in per_symbol.items():
        for ts in sorted(d):
            dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).astimezone(zone)
            m = dt.hour * 60 + dt.minute
            if SESSION_OPEN <= m < SESSION_CLOSE:
                sessions[(sym, dt.date())].append((m - SESSION_OPEN, d[ts]))
    stats["symbols"] = len(per_symbol)
    stats["session_bars"] = sum(len(v) for v in sessions.values())
    full = {k: v for k, v in sessions.items() if len(v) >= MIN_SESSION_BARS}
    stats["sessions"], stats["full_sessions"] = len(sessions), len(full)
    return full, stats


def run(data_dir: Path, split_month: int, tz: str) -> str:
    full, st = load_sessions(data_dir, tz)
    keys = sorted(full)
    bars = [[b for _, b in full[k]] for k in keys]
    pos = [[m for m, _ in full[k]] for k in keys]
    rows = replay_sessions(bars, None, positions=pos)
    p = np.array([r[1] for r in rows]); y = np.array([r[3] for r in rows])
    cal = evaluate.calibration(p, y)
    tr = [i for i, k in enumerate(keys) if k[1].month <= split_month]
    te = [i for i, k in enumerate(keys) if k[1].month > split_month]
    prof = estimate_profile([bars[i] for i in tr], SESSION_LEN)
    ab = replay_sessions([bars[i] for i in te], prof, positions=[pos[i] for i in te])
    boot = paired_bootstrap(ab)
    pa = np.array([r[1] for r in ab]); pb = np.array([r[2] for r in ab]); ya = np.array([r[3] for r in ab])
    ca, cb = evaluate.calibration(pa, ya), evaluate.calibration(pb, ya)
    L = [f"files {st['files']} · symbols {st['symbols']} · rows {st['rows']:,} · rejected "
         f"{sum(st['rejected'].values())} · duplicate timestamps {st['duplicates']}",
         f"regular session bars {st['session_bars']:,} · sessions {st['sessions']:,} · "
         f"full sessions (>= {MIN_SESSION_BARS} bars) {st['full_sessions']:,}",
         "", f"Baseline (A) on all full sessions: {cal.n:,} predictions · ECE {cal.ece:.4f} · "
         f"Brier {cal.brier:.4f} · mean overprediction {100 * (p.mean() - y.mean()):+.1f} pts", "",
         "| Predicted bin | n | Mean predicted | Observed |", "|:--|--:|--:|--:|"]
    L += [f"| {b.lo:.1f} to {b.hi:.1f} | {b.n:,} | {b.mean_pred:.3f} | {b.observed:.3f} |" for b in cal.bins]
    L += ["", f"Intraday profile learned from {len(tr)} sessions (months <= {split_month}): "
          f"first 30 min {prof[:30].mean():.2f}, midday {prof[150:240].mean():.2f}, last 30 min "
          f"{prof[-30:].mean():.2f} (1.00 = session average)", "",
          f"A/B on {boot['sessions']} held out sessions, {boot['predictions']:,} predictions:", "",
          "| Variant | ECE | Brier | Mean overprediction |", "|:--|--:|--:|--:|",
          f"| A baseline | {ca.ece:.4f} | {boot['brier_a']:.5f} | {100 * (pa.mean() - ya.mean()):+.1f} pts |",
          f"| B seasonality adjusted | {cb.ece:.4f} | {boot['brier_b']:.5f} | {100 * (pb.mean() - ya.mean()):+.1f} pts |",
          "", f"Brier B minus A: {boot['diff']:+.5f}, 95% session bootstrap interval "
          f"[{boot['ci_low']:+.5f}, {boot['ci_high']:+.5f}]; B better in {100 * boot['share_b_better']:.1f}% "
          "of 2,000 resamples."]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tracebench.field")
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("--split-month", type=int, default=6)
    ap.add_argument("--tz", default="America/New_York")
    a = ap.parse_args(argv)
    print(run(a.data_dir, a.split_month, a.tz))
    return 0


if __name__ == "__main__":
    sys.exit(main())
