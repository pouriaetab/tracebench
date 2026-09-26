"""What 'touch' means. Every outcome in this repository is graded with these
two functions, so the definition lives in exactly one place.

A level ABOVE the current price (resistance) is touched when a bar's high
reaches it. A level BELOW (support) is touched when a bar's low reaches it.
The two cases mirror each other exactly (REQ SYS-4).
"""
from __future__ import annotations

from typing import Sequence

from tracebench.bars import Bar


def side(price: float, level: float) -> str:
    return "resistance" if level >= price else "support"


def touched(bars: Sequence[Bar], price: float, level: float) -> bool:
    """True if any bar in `bars` reaches `level`, judged from `price`."""
    if level >= price:
        return any(b.high >= level for b in bars)
    return any(b.low <= level for b in bars)


def first_touch_index(bars: Sequence[Bar], price: float, level: float) -> int | None:
    up = level >= price
    for i, b in enumerate(bars):
        if (up and b.high >= level) or (not up and b.low <= level):
            return i
    return None
