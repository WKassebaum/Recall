"""Tests for SessionStart hook."""

import json
import os
import subprocess
import sys

import pytest

from recall.hooks.state import read_state, write_handoff, HANDOFF_FILE

HOOK_CMD = os.path.join(os.path.dirname(sys.executable), "recall-session-start")


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


class TestSessionStartHook:
    def test_first_session_no_handoff(self, tmp_path: str) -> None:
        code, stdout, _ = run_hook(
            {"session_id": "first", "working_directory": str(tmp_path)}, str(tmp_path)
        )
        assert code == 0
        output = json.loads(stdout)
        assert "No previous session handoff found" in output["systemMessage"]
        assert "recall_memory" in output["systemMessage"]
        assert "first" in output["systemMessage"]

    def test_with_previous_handoff(self, tmp_path: str) -> None:
        write_handoff(
            str(tmp_path),
            {
                "session_id": "prev",
                "ended_at": "2026-03-24T10:00:00Z",
                "summary_tail": "Fixed the MCP logging issue",
                "milestones": ["git commit: fix logging"],
                "ingests_made": 3,
            },
        )
        code, stdout, _ = run_hook(
            {"session_id": "new", "working_directory": str(tmp_path)}, str(tmp_path)
        )
        assert code == 0
        msg = json.loads(stdout)["systemMessage"]
        assert "prev" in msg
        assert "Fixed the MCP logging issue" in msg
        assert "git commit: fix logging" in msg
        assert "3 memories were saved" in msg

    def test_initializes_state_file(self, tmp_path: str) -> None:
        run_hook({"session_id": "init", "working_directory": str(tmp_path)}, str(tmp_path))
        state = read_state(str(tmp_path))
        assert state["session_id"] == "init"
        assert state["events_since_last_save"] == 0

    def test_corrupted_handoff_graceful(self, tmp_path: str) -> None:
        with open(os.path.join(str(tmp_path), HANDOFF_FILE), "w") as f:
            f.write("corrupt{{{")
        code, stdout, _ = run_hook(
            {"session_id": "recover", "working_directory": str(tmp_path)}, str(tmp_path)
        )
        assert code == 0
        assert "systemMessage" in json.loads(stdout)

    def test_invalid_stdin_graceful(self) -> None:
        result = subprocess.run(
            [HOOK_CMD], input="not json", capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0

    def test_execution_time(self, tmp_path: str) -> None:
        import time

        start = time.monotonic()
        run_hook({"session_id": "speed", "working_directory": str(tmp_path)}, str(tmp_path))
        assert time.monotonic() - start < 0.5
