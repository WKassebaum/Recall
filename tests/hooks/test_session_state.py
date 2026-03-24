"""Tests for shared session state utilities."""

import json
import os
import tempfile

import pytest

from recall.hooks.state import (
    append_breadcrumb,
    clear_breadcrumbs,
    now_iso,
    read_breadcrumbs,
    read_handoff,
    read_state,
    write_handoff,
    write_state,
    BREADCRUMBS_FILE,
    STATE_FILE,
)


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestReadWriteState:
    def test_write_and_read(self, tmp_dir: str) -> None:
        data = {"session_id": "test-123", "events_since_last_save": 3}
        write_state(tmp_dir, data)
        assert read_state(tmp_dir) == data

    def test_read_missing_file(self, tmp_dir: str) -> None:
        assert read_state(tmp_dir) == {}

    def test_read_corrupted_file(self, tmp_dir: str) -> None:
        with open(os.path.join(tmp_dir, STATE_FILE), "w") as f:
            f.write("not json{{{")
        assert read_state(tmp_dir) == {}

    def test_atomic_write_overwrites(self, tmp_dir: str) -> None:
        write_state(tmp_dir, {"a": 1})
        write_state(tmp_dir, {"b": 2})
        assert read_state(tmp_dir) == {"b": 2}


class TestHandoff:
    def test_write_and_read(self, tmp_dir: str) -> None:
        data = {"session_id": "s1", "summary_tail": "did stuff"}
        write_handoff(tmp_dir, data)
        assert read_handoff(tmp_dir) == data

    def test_read_missing(self, tmp_dir: str) -> None:
        assert read_handoff(tmp_dir) == {}


class TestBreadcrumbs:
    def test_append_and_read(self, tmp_dir: str) -> None:
        append_breadcrumb(tmp_dir, {"type": "git_commit", "detail": "fix bug"})
        append_breadcrumb(tmp_dir, {"type": "pytest", "detail": "42 passed"})
        result = read_breadcrumbs(tmp_dir)
        assert len(result) == 2
        assert result[0]["type"] == "git_commit"
        assert result[1]["detail"] == "42 passed"

    def test_read_empty(self, tmp_dir: str) -> None:
        assert read_breadcrumbs(tmp_dir) == []

    def test_clear(self, tmp_dir: str) -> None:
        append_breadcrumb(tmp_dir, {"type": "test"})
        clear_breadcrumbs(tmp_dir)
        assert read_breadcrumbs(tmp_dir) == []

    def test_handles_corrupted_lines(self, tmp_dir: str) -> None:
        path = os.path.join(tmp_dir, BREADCRUMBS_FILE)
        with open(path, "w") as f:
            f.write('{"good": true}\n')
            f.write("bad json line\n")
            f.write('{"also_good": true}\n')
        assert len(read_breadcrumbs(tmp_dir)) == 2


class TestNowIso:
    def test_returns_string(self) -> None:
        result = now_iso()
        assert isinstance(result, str)
        assert "T" in result
