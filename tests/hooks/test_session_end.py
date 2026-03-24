"""Tests for SessionEnd hook."""

import json
import os
import subprocess
import sys

import pytest

from recall.hooks.state import (
    append_breadcrumb,
    read_breadcrumbs,
    read_handoff,
    write_state,
)

HOOK_CMD = os.path.join(os.path.dirname(sys.executable), "recall-session-end")


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


class TestSessionEndHook:
    def test_creates_handoff_file(self, tmp_path: str) -> None:
        write_state(str(tmp_path), {"session_id": "end", "total_milestones": 3, "total_ingests": 2})
        append_breadcrumb(
            str(tmp_path), {"type": "git_commit", "detail": "git commit: feat: add search"}
        )

        code, _, _ = run_hook(
            {"session_id": "end", "last_assistant_message": "All done."}, str(tmp_path)
        )
        assert code == 0
        handoff = read_handoff(str(tmp_path))
        assert handoff["session_id"] == "end"
        assert "All done." in handoff["summary_tail"]
        assert "git commit: feat: add search" in handoff["milestones"]
        assert handoff["ingests_made"] == 2

    def test_truncates_long_message(self, tmp_path: str) -> None:
        write_state(str(tmp_path), {"session_id": "trunc"})
        run_hook({"session_id": "trunc", "last_assistant_message": "x" * 1000}, str(tmp_path))
        assert len(read_handoff(str(tmp_path))["summary_tail"]) == 500

    def test_clears_breadcrumbs(self, tmp_path: str) -> None:
        write_state(str(tmp_path), {"session_id": "clear"})
        append_breadcrumb(str(tmp_path), {"type": "test"})
        run_hook({"session_id": "clear", "last_assistant_message": "done"}, str(tmp_path))
        assert read_breadcrumbs(str(tmp_path)) == []

    def test_no_state_file_graceful(self, tmp_path: str) -> None:
        code, _, _ = run_hook(
            {"session_id": "no-state", "last_assistant_message": "bye"}, str(tmp_path)
        )
        assert code == 0
        assert read_handoff(str(tmp_path))["session_id"] == "no-state"

    def test_empty_message(self, tmp_path: str) -> None:
        write_state(str(tmp_path), {"session_id": "empty"})
        run_hook({"session_id": "empty", "last_assistant_message": ""}, str(tmp_path))
        assert read_handoff(str(tmp_path))["summary_tail"] == ""

    def test_execution_time(self, tmp_path: str) -> None:
        import time

        write_state(str(tmp_path), {"session_id": "speed"})
        start = time.monotonic()
        run_hook({"session_id": "speed", "last_assistant_message": "done"}, str(tmp_path))
        assert time.monotonic() - start < 0.5
