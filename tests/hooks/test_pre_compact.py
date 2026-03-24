"""Tests for PreCompact hook."""

import json
import os
import subprocess
import sys

import pytest

from recall.hooks.state import append_breadcrumb, read_state, write_state

HOOK_CMD = os.path.join(os.path.dirname(sys.executable), "recall-pre-compact")


def run_hook(input_data: dict, working_dir: str) -> tuple:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = working_dir
    result = subprocess.run(
        [HOOK_CMD],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )
    return result.returncode, result.stdout, result.stderr


class TestPreCompactHook:
    def test_fires_when_events_above_threshold(self, tmp_path: str) -> None:
        write_state(str(tmp_path), {"session_id": "pc1", "events_since_last_save": 5})
        append_breadcrumb(
            str(tmp_path),
            {"type": "git_commit", "detail": "fix: bug", "timestamp": "2026-03-24T14:23:00Z"},
        )

        code, stdout, _ = run_hook({"session_id": "pc1"}, str(tmp_path))
        assert code == 0
        assert "Context compression is imminent" in stdout
        assert "ingest_memory" in stdout
        assert "fix: bug" in stdout

    def test_skips_when_below_threshold(self, tmp_path: str) -> None:
        write_state(str(tmp_path), {"session_id": "pc2", "events_since_last_save": 1})
        code, stdout, _ = run_hook({"session_id": "pc2"}, str(tmp_path))
        assert code == 0
        assert stdout == ""

    def test_skips_when_zero_events(self, tmp_path: str) -> None:
        write_state(str(tmp_path), {"session_id": "pc3", "events_since_last_save": 0})
        code, stdout, _ = run_hook({"session_id": "pc3"}, str(tmp_path))
        assert code == 0
        assert stdout == ""

    def test_no_breadcrumbs_still_fires(self, tmp_path: str) -> None:
        write_state(str(tmp_path), {"session_id": "pc4", "events_since_last_save": 3})
        code, stdout, _ = run_hook({"session_id": "pc4"}, str(tmp_path))
        assert code == 0
        assert "Context compression is imminent" in stdout

    def test_limits_breadcrumbs_to_10(self, tmp_path: str) -> None:
        write_state(str(tmp_path), {"session_id": "pc5", "events_since_last_save": 15})
        for i in range(15):
            append_breadcrumb(
                str(tmp_path),
                {
                    "type": "event",
                    "detail": f"event-{i}",
                    "timestamp": f"2026-03-24T{i:02d}:00:00Z",
                },
            )

        code, stdout, _ = run_hook({"session_id": "pc5"}, str(tmp_path))
        assert "event-14" in stdout
        assert "event-5" in stdout
        assert "event-0" not in stdout

    def test_updates_compact_count(self, tmp_path: str) -> None:
        write_state(
            str(tmp_path), {"session_id": "pc6", "events_since_last_save": 5, "compact_count": 2}
        )
        run_hook({"session_id": "pc6"}, str(tmp_path))
        s = read_state(str(tmp_path))
        assert s["compact_count"] == 3
        assert "last_compact_at" in s

    def test_output_under_2kb(self, tmp_path: str) -> None:
        write_state(str(tmp_path), {"session_id": "pc7", "events_since_last_save": 10})
        for i in range(10):
            append_breadcrumb(
                str(tmp_path),
                {
                    "type": "git_commit",
                    "detail": f"commit message {i}" * 5,
                    "timestamp": "2026-03-24T14:00:00Z",
                },
            )
        code, stdout, _ = run_hook({"session_id": "pc7"}, str(tmp_path))
        assert len(stdout.encode()) < 2048

    def test_execution_time(self, tmp_path: str) -> None:
        import time

        write_state(str(tmp_path), {"session_id": "speed", "events_since_last_save": 5})
        start = time.monotonic()
        run_hook({"session_id": "speed"}, str(tmp_path))
        assert time.monotonic() - start < 0.5
