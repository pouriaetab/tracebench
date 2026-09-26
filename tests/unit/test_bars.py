import math

import pytest

from tracebench.bars import Bar, parse_rows, validate_bar

GOOD = {"timestamp_ms": "1000", "open": "10", "high": "11", "low": "9", "close": "10.5", "volume": "5"}


def row(**kw):
    return {**GOOD, **kw}


@pytest.mark.req("DATA-1")
@pytest.mark.parametrize("bad, reason", [
    (dict(open="nan"), "non-finite price"),
    (dict(low="0"), "non-positive price"),
    (dict(high="8"), "high below low"),
    (dict(close="11.5"), "open/close outside the high-low range"),
    (dict(volume="-1"), "negative volume"),
    (dict(close=""), "unparseable: missing close"),
    (dict(open="ten"), "unparseable"),
])
def test_bad_row_is_rejected_with_its_reason(bad, reason):
    bars, rejects = parse_rows([row(**bad)])
    assert bars == []
    assert len(rejects) == 1 and rejects[0].reason.startswith(reason)
    assert rejects[0].line == 2  # header is line 1


@pytest.mark.req("DATA-1")
def test_valid_bar_has_no_complaint():
    assert validate_bar(Bar(1, 10, 11, 9, 10.5, 0)) is None


@pytest.mark.req("DATA-3")
@pytest.mark.parametrize("ts", ["1000", "999"])
def test_repeated_or_backward_timestamp_is_rejected_not_resorted(ts):
    bars, rejects = parse_rows([row(), row(timestamp_ms=ts), row(timestamp_ms="2000")])
    assert [b.timestamp_ms for b in bars] == [1000, 2000]
    assert [r.reason for r in rejects] == ["timestamp not after the previous row"]
