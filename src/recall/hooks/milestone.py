"""Recall PostToolUse milestone hook: log significant events as breadcrumbs.

Detects git commits, test runs, and recall ingests. Writes lightweight
breadcrumbs to a JSONL file consumed by PreCompact and SessionEnd hooks.

Hook event: PostToolUse
Matcher: Bash|mcp__recall__ingest_memory
Input: {tool_name, tool_input, session_id}
Output: stderr messages only (non-blocking)
"""

import json
import os
import re
import sys

from recall.hooks.state import append_breadcrumb, now_iso, read_state, write_state

GIT_COMMIT_RE = re.compile(r"\bgit\s+commit\b", re.IGNORECASE)
PYTEST_RE = re.compile(r"\bpytest\b|python\s+-m\s+pytest", re.IGNORECASE)


def detect_milestone(tool_name: str, tool_input: dict[str, str]) -> tuple[str | None, str | None]:
    """Detect if a tool call is a milestone event.

    Returns (milestone_type, detail) or (None, None).
    """
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if GIT_COMMIT_RE.search(command):
            msg_match = re.search(r'-m\s+["\']([^"\']+)["\']', command)
            msg = msg_match.group(1)[:80] if msg_match else "commit"
            return "git_commit", f"git commit: {msg}"
        if PYTEST_RE.search(command):
            return "pytest", "pytest run"

    elif tool_name == "mcp__recall__ingest_memory":
        return "recall_ingest", "memory saved to Recall"

    return None, None


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    session_id = data.get("session_id", "unknown")

    # Fast path: skip non-matching tools
    if tool_name not in ("Bash", "mcp__recall__ingest_memory"):
        sys.exit(0)

    milestone_type, detail = detect_milestone(tool_name, tool_input)
    if milestone_type is None:
        sys.exit(0)

    working_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # Update session state
    session_state = read_state(working_dir)

    if milestone_type == "recall_ingest":
        session_state["events_since_last_save"] = 0
        session_state["total_ingests"] = session_state.get("total_ingests", 0) + 1
        session_state["last_ingest_at"] = now_iso()
        write_state(working_dir, session_state)
        sys.exit(0)

    # Log breadcrumb for non-ingest milestones
    breadcrumb = {
        "timestamp": now_iso(),
        "type": milestone_type,
        "detail": detail,
        "session_id": session_id,
    }
    append_breadcrumb(working_dir, breadcrumb)

    session_state["events_since_last_save"] = session_state.get("events_since_last_save", 0) + 1
    session_state["total_milestones"] = session_state.get("total_milestones", 0) + 1
    write_state(working_dir, session_state)

    print(f"[recall] Milestone: {detail}", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
