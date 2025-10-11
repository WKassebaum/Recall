# View Recall Timeline (Chronological)

View memories in chronological order - see "what happened when".

## Usage

`/recall-timeline [--session <session-id>] [--from <date>] [--to <date>] [--events <types>]`

## What It Does

Retrieves memories in time order (oldest to newest) instead of by relevance. Perfect for reconstructing "what happened during Phase 3".

## Examples

**All memories from a session:**
```
/recall-timeline --session phase3
```

**Memories from date range:**
```
/recall-timeline --from 2025-10-08 --to 2025-10-11
```

**Recent events (open-ended):**
```
/recall-timeline --from 2025-10-10 --session debugging
```

**Specific event types only:**
```
/recall-timeline --session phase3 --events discovery,error,success
```

## Parameters

- `--session <session-id>`: Filter to specific session (recommended)
- `--from <date>`: Start date (YYYY-MM-DD or ISO format)
- `--to <date>`: End date (optional - omit for "since date")
- `--events <types>`: Comma-separated event types to include

## Event Types

- `decision` - Architecture decisions
- `discovery` - Findings and insights
- `milestone` - Waypoint completions
- `preference` - User preferences learned
- `error` - Problems encountered
- `success` - Solutions that worked

## When to Use

- **"What happened during Phase 3?"** - Reconstruct timeline
- **"Show debugging session"** - See problem-solving sequence
- **"Recent changes this week"** - Catch up after time away
- **"How did we get here?"** - Understand evolution of decisions

## Tips

- Always specify `--session` for focused results
- Use open-ended dates: `--from 2025-10-10` (no --to)
- Filter by event types to reduce noise
- Results show ingestion timestamp for chronological ordering

## Related Commands

- `/recall-search` - Search by meaning instead of time
- `/recall-hybrid` - Combine semantic + temporal search
