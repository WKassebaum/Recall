"""Recall SessionStart hook: inject previous session context and recall instruction.

Reads the handoff file from the previous session and returns a systemMessage
instructing Claude to query Recall for relevant context.

Hook event: SessionStart
Input: {session_id, working_directory}
Output: {"systemMessage": "..."} on stdout
"""

import json
import os
import sys

from recall.hooks.state import now_iso, read_handoff, write_state


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    session_id = data.get("session_id", "unknown")
    working_dir = data.get("working_directory", os.getcwd())

    # Initialize new session state
    write_state(
        working_dir,
        {
            "session_id": session_id,
            "started_at": now_iso(),
            "events_since_last_save": 0,
            "total_milestones": 0,
            "total_recalls": 0,
            "total_ingests": 0,
            "compact_count": 0,
        },
    )

    # Read previous session handoff
    handoff = read_handoff(working_dir)

    # Build system message
    parts = ["[Recall Memory System]"]

    if handoff:
        prev_id = handoff.get("session_id", "unknown")
        ended_at = handoff.get("ended_at", "unknown")
        summary_tail = handoff.get("summary_tail", "")
        milestones = handoff.get("milestones", [])
        ingests = handoff.get("ingests_made", 0)

        parts.append(f"\nPrevious session ({prev_id}) ended {ended_at}:")
        if milestones:
            parts.append("Milestones:")
            for m in milestones[:10]:
                parts.append(f"  - {m}")
        if summary_tail:
            parts.append(f"\nLast context:\n{summary_tail}")
        events = handoff.get("events_logged", 0)
        if ingests > 0:
            parts.append(f"\n({ingests} memories were saved to Recall)")
        elif milestones or events:
            # Report the zero case too. Nothing in Recall ingests on its own -
            # the hooks only keep breadcrumbs and nudge - so a session that
            # never calls ingest_memory() leaves no semantic trace at all.
            # Staying silent here meant the one outcome worth flagging was
            # the one outcome never mentioned.
            parts.append(
                f"\n[!] The previous session logged {events} milestone(s) but "
                "saved 0 memories to Recall, so none of it is searchable. If "
                "anything above is worth keeping, ingest it now with "
                f"ingest_memory(session_id='{prev_id}') - use that id, not "
                "this session's, so the memory keeps its original date."
            )
    else:
        parts.append("\nNo previous session handoff found.")

    parts.append(
        "\n\nTo restore context from Recall, call: "
        "recall_memory(query='recent decisions and progress', top_k=5, min_score=0.5)"
    )
    parts.append(f"\nUse session_id '{session_id}' for any ingest_memory() calls this session.")

    message = "\n".join(parts)
    print(json.dumps({"systemMessage": message}))
    sys.exit(0)


if __name__ == "__main__":
    main()
