import pytest

from tracebench import scenarios
from tracebench.bars import load_csv, write_csv


@pytest.mark.req("DATA-2")
def test_one_bad_row_does_not_fail_the_file(tmp_path):
    f = tmp_path / "bars.csv"
    f.write_text("timestamp_ms,open,high,low,close,volume\n"
                 "1000,10,11,9,10.5,1\n"
                 "2000,10,8,9,10.5,1\n"          # high below low
                 "3000,10.5,12,10,11,1\n"
                 "4000,oops,12,10,11,1\n"        # unparseable
                 "5000,11,11.5,10.8,11.2,1\n", encoding="utf-8")
    bars, rejects = load_csv(f)
    assert [b.timestamp_ms for b in bars] == [1000, 3000, 5000]
    assert [r.line for r in rejects] == [3, 5]


@pytest.mark.req("DATA-4")
def test_round_trip(tmp_path):
    bars = scenarios.price_bars(500, 0.002, seed=9)
    f = tmp_path / "b.csv"
    write_csv(f, bars)
    back, rejects = load_csv(f)
    assert rejects == [] and len(back) == len(bars)
    for a, b in zip(bars, back):
        assert b.timestamp_ms == a.timestamp_ms
        for field in ("open", "high", "low", "close"):
            assert getattr(b, field) == pytest.approx(getattr(a, field), abs=1e-6)
