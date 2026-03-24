"""Recall PreCompact hook: prompt Claude to save context before compression.

Fires before context compression. Reads milestone breadcrumbs and injects
an instruction for Claude to save important context to Recall.

Hook event: PreCompact
Input: {session_id}
Output: instruction text on stdout
"""

import json
import os
import sys

from recall.hooks.state import now_iso, read_breadcrumbs, read_state, write_state


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    session_id = data.get("session_id", "unknown")
    working_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # Read current state
    session_state = read_state(working_dir)
    events_since_save = session_state.get("events_since_last_save", 0)

    # Skip if nothing meaningful has happened since last save
    if events_since_save < 2:
        sys.exit(0)

    # Read recent breadcrumbs
    breadcrumbs = read_breadcrumbs(working_dir)

    # Build instruction
    parts = [
        "[Recall] Context compression is imminent. Save important context now.",
        "",
        "Call ingest_memory() for any of these that apply:",
        "  1. DECISIONS made this session (architecture, tool choices, approach changes)",
        "  2. DISCOVERIES or debugging findings (root causes, what worked/failed)",
        "  3. Current TASK STATUS and next steps",
        "",
        f'Use session_id: "{session_id}"',
        'Use tags: "pre-compact,auto-save" plus topic-specific tags',
    ]

    if breadcrumbs:
        parts.append("")
        parts.append(f"Recent milestones ({len(breadcrumbs)} events since last save):")
        for bc in breadcrumbs[-10:]:
            ts = bc.get("timestamp", "")
            detail = bc.get("detail", bc.get("type", "event"))
            time_part = f" ({ts[11:16]})" if len(ts) > 16 else ""
            parts.append(f"  - {detail}{time_part}")

    instruction = "\n".join(parts)

    # Update state
    session_state["compact_count"] = session_state.get("compact_count", 0) + 1
    session_state["last_compact_at"] = now_iso()
    write_state(working_dir, session_state)

    print(instruction)
    sys.exit(0)


if __name__ == "__main__":
    main()
