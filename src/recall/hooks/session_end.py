"""Recall SessionEnd hook: capture session summary for next session handoff.

Writes a handoff file containing the session's last message, milestones,
and stats for the next SessionStart hook to read.

Hook event: SessionEnd
Input: {session_id, last_assistant_message}
Output: writes .recall-session-handoff.json
"""

import json
import os
import sys

from recall.hooks.state import (
    clear_breadcrumbs,
    now_iso,
    read_breadcrumbs,
    read_state,
    write_handoff,
)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    session_id = data.get("session_id", "unknown")
    last_message = data.get("last_assistant_message", "")

    working_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # Read current session state
    session_state = read_state(working_dir)

    # Read breadcrumbs from this session
    breadcrumbs = read_breadcrumbs(working_dir)
    milestone_summaries = []
    for bc in breadcrumbs:
        detail = bc.get("detail", bc.get("type", "event"))
        milestone_summaries.append(detail)

    # Capture last 500 chars of final message as summary tail
    summary_tail = last_message[-500:] if last_message else ""

    # Write handoff for next session
    handoff = {
        "session_id": session_id,
        "ended_at": now_iso(),
        "summary_tail": summary_tail,
        "milestones": milestone_summaries[:20],
        "events_logged": session_state.get("total_milestones", 0),
        "ingests_made": session_state.get("total_ingests", 0),
    }
    write_handoff(working_dir, handoff)

    # Clear breadcrumbs for next session
    clear_breadcrumbs(working_dir)

    sys.exit(0)


if __name__ == "__main__":
    main()
