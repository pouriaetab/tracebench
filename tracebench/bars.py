"""Price bars and the CSV loader.

A bar is one time interval of prices: open, high, low, close. The loader is the
system's front door, so it is where bad input must be caught. It follows one
rule: a bad row never fails the whole file. It is set aside ("quarantined") with
the reason, and every good row still flows (requirements DATA-1 to DATA-4).
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

COLUMNS = ("timestamp_ms", "open", "high", "low", "close")


@dataclass(frozen=True)
class Bar:
    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(frozen=True)
class Rejected:
    line: int
    reason: str
    raw: dict


def validate_bar(b: Bar) -> Optional[str]:
    """Return the reason a bar is unusable, or None if it is fine."""
    vals = (b.open, b.high, b.low, b.close)
    if any(not math.isfinite(v) for v in vals):
        return "non-finite price"
    if any(v <= 0 for v in vals):
        return "non-positive price"
    if b.high < b.low:
        return "high below low"
    if b.high < max(b.open, b.close) or b.low > min(b.open, b.close):
        return "open/close outside the high-low range"
    if b.volume < 0:
        return "negative volume"
    return None


def parse_rows(rows: Iterable[dict], first_line: int = 2) -> tuple[list[Bar], list[Rejected]]:
    """Turn raw CSV rows into bars. Rows are checked one at a time; a failure
    quarantines that row only. Timestamps must strictly increase: a row that
    goes back in time (or repeats a timestamp) is rejected, never re-sorted,
    because silently reordering data hides the upstream fault."""
    bars: list[Bar] = []
    rejects: list[Rejected] = []
    last_ts: Optional[int] = None
    for i, row in enumerate(rows, start=first_line):
        try:
            missing = [c for c in COLUMNS if row.get(c) in (None, "")]
            if missing:
                raise ValueError(f"missing {', '.join(missing)}")
            b = Bar(int(float(row["timestamp_ms"])), float(row["open"]), float(row["high"]),
                    float(row["low"]), float(row["close"]), float(row.get("volume") or 0.0))
        except (ValueError, TypeError) as e:
            rejects.append(Rejected(i, f"unparseable: {e}", dict(row)))
            continue
        why = validate_bar(b)
        if why is None and last_ts is not None and b.timestamp_ms <= last_ts:
            why = "timestamp not after the previous row"
        if why:
            rejects.append(Rejected(i, why, dict(row)))
            continue
        bars.append(b)
        last_ts = b.timestamp_ms
    return bars, rejects


def load_csv(path: str | Path) -> tuple[list[Bar], list[Rejected]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return parse_rows(csv.DictReader(fh))


def write_csv(path: str | Path, bars: Iterable[Bar]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS + ("volume",))
        for b in bars:
            w.writerow([b.timestamp_ms, f"{b.open:.6f}", f"{b.high:.6f}", f"{b.low:.6f}",
                        f"{b.close:.6f}", f"{b.volume:.0f}"])
