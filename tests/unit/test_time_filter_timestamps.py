"""Chunks with missing or naive ``ingested_at`` must not break time-filtered or
chronological retrieval (regression for the 2026-09-10 restore, where 1,389 of
1,509 chunks had no timestamp and every time_range query raised TypeError)."""

from datetime import datetime, timezone
from types import SimpleNamespace

from recall.core.store import UnifiedVectorStore, _parse_ts


def _chunk(ts):
    md = {} if ts is None else {"ingested_at": ts}
    return SimpleNamespace(id="x", content="c", metadata=md)


def test_parse_ts_variants():
    assert _parse_ts(None) is None
    assert _parse_ts("") is None
    assert _parse_ts("not a date") is None
    aware = _parse_ts("2026-09-09T20:52:21.825345+00:00")
    naive = _parse_ts("2026-09-09T20:52:21")
    zulu = _parse_ts("2026-09-09T20:52:21Z")
    assert aware.tzinfo is not None and naive.tzinfo is not None and zulu.tzinfo is not None
    assert naive == datetime(2026, 9, 9, 20, 52, 21, tzinfo=timezone.utc)
    assert zulu == naive


def test_time_filter_skips_missing_and_accepts_naive():
    store = UnifiedVectorStore.__new__(UnifiedVectorStore)  # no backend needed for the filter
    chunks = [
        _chunk(None),
        _chunk("2026-09-09T20:52:21+00:00"),
        _chunk("2026-08-01T12:00:00"),  # naive, treated as UTC
        _chunk("garbage"),
    ]
    got = store._apply_time_filter(chunks, ("2026-09-09", None))
    assert [c.metadata.get("ingested_at") for c in got] == ["2026-09-09T20:52:21+00:00"]
    got = store._apply_time_filter(chunks, ("2026-07-01", "2026-12-31"))
    assert len(got) == 2


def test_chronological_sort_tolerates_missing():
    store = UnifiedVectorStore.__new__(UnifiedVectorStore)
    chunks = [_chunk("2026-09-09T00:00:00+00:00"), _chunk(None), _chunk("2026-01-01T00:00:00")]
    results = store._sort_chronologically(chunks, top_k=10)
    assert [r.content for r in results] == ["c", "c", "c"]
    # missing timestamp sorts first (epoch), then Jan, then Sep
    assert results[1].metadata.get("ingested_at") == "2026-01-01T00:00:00"
    assert results[2].metadata.get("ingested_at") == "2026-09-09T00:00:00+00:00"
