"""Tests for PostToolUse milestone hook."""

import json
import os
import subprocess
import sys

import pytest

from recall.hooks.state import read_breadcrumbs, read_state, write_state

HOOK_CMD = os.path.join(os.path.dirname(sys.executable), "recall-milestone-hook")


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


class TestMilestoneDetection:
    def test_git_commit_detected(self, tmp_path: str) -> None:
        write_state(str(tmp_path), {"session_id": "t1", "events_since_last_save": 0})
        code, _, stderr = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": 'git commit -m "fix: bug"'},
                "session_id": "t1",
            },
            str(tmp_path),
        )
        assert code == 0
        assert "[recall] Milestone" in stderr
        bcs = read_breadcrumbs(str(tmp_path))
        assert len(bcs) == 1
        assert bcs[0]["type"] == "git_commit"
        assert "fix: bug" in bcs[0]["detail"]

    def test_git_add_not_detected(self, tmp_path: str) -> None:
        write_state(str(tmp_path), {"session_id": "t2", "events_since_last_save": 0})
        run_hook(
            {"tool_name": "Bash", "tool_input": {"command": "git add ."}, "session_id": "t2"},
            str(tmp_path),
        )
        assert read_breadcrumbs(str(tmp_path)) == []

    def test_git_status_not_detected(self, tmp_path: str) -> None:
        write_state(str(tmp_path), {"session_id": "t3", "events_since_last_save": 0})
        run_hook(
            {"tool_name": "Bash", "tool_input": {"command": "git status"}, "session_id": "t3"},
            str(tmp_path),
        )
        assert read_breadcrumbs(str(tmp_path)) == []

    def test_pytest_detected(self, tmp_path: str) -> None:
        write_state(str(tmp_path), {"session_id": "t4", "events_since_last_save": 0})
        run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "./venv/bin/pytest tests/"},
                "session_id": "t4",
            },
            str(tmp_path),
        )
        bcs = read_breadcrumbs(str(tmp_path))
        assert len(bcs) == 1
        assert bcs[0]["type"] == "pytest"

    def test_python_m_pytest_detected(self, tmp_path: str) -> None:
        write_state(str(tmp_path), {"session_id": "t5", "events_since_last_save": 0})
        run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "python -m pytest -x"},
                "session_id": "t5",
            },
            str(tmp_path),
        )
        assert read_breadcrumbs(str(tmp_path))[0]["type"] == "pytest"


class TestRecallIngestTracking:
    def test_ingest_resets_counter(self, tmp_path: str) -> None:
        write_state(
            str(tmp_path), {"session_id": "t6", "events_since_last_save": 5, "total_ingests": 1}
        )
        run_hook(
            {"tool_name": "mcp__recall__ingest_memory", "tool_input": {}, "session_id": "t6"},
            str(tmp_path),
        )
        s = read_state(str(tmp_path))
        assert s["events_since_last_save"] == 0
        assert s["total_ingests"] == 2


class TestEventCounters:
    def test_increments_events_since_last_save(self, tmp_path: str) -> None:
        write_state(
            str(tmp_path), {"session_id": "t7", "events_since_last_save": 2, "total_milestones": 5}
        )
        run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": 'git commit -m "test"'},
                "session_id": "t7",
            },
            str(tmp_path),
        )
        s = read_state(str(tmp_path))
        assert s["events_since_last_save"] == 3
        assert s["total_milestones"] == 6


class TestFastPath:
    def test_non_bash_exits_immediately(self, tmp_path: str) -> None:
        import time

        start = time.monotonic()
        code, _, _ = run_hook(
            {"tool_name": "Write", "tool_input": {}, "session_id": "fast"}, str(tmp_path)
        )
        assert code == 0
        assert time.monotonic() - start < 0.5

    def test_invalid_stdin(self) -> None:
        result = subprocess.run(
            [HOOK_CMD], input="not json", capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0
