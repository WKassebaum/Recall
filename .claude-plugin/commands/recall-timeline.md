# View Recall Timeline (Chronological Mode)

Retrieve memories in chronological order, showing what happened when.

**Instructions:**

1. **Identify the timeline scope** - Ask the user:
   - Session ID to view (e.g., "phase3", "bug_investigation_2025-10")
   - Time range (optional):
     - Specific range: "2025-10-08,2025-10-11"
     - Open-ended: "2025-10-10," (since Oct 10)
     - All time: Leave blank
   - Event types to include (optional): decision, discovery, milestone, preference, error, success

2. **Retrieve chronological timeline** using `mcp__recall__recall_memory()`:

```python
mcp__recall__recall_memory(
    retrieval_mode="chronological",
    session_id="[session identifier]",
    time_range="[start_date,end_date]",  # Optional
    event_types="decision,discovery,milestone",  # Optional
    top_k=20  # Adjust for timeline length
)
```

3. **Present timeline** - Show events in order (oldest → newest):
   - Timestamps
   - Event types
   - Content summaries
   - Session IDs
   - Highlight key milestones

4. **Suggest follow-up actions**:
   - Want more details on specific memory? Use `/recall-search` with specific query
   - Need to find related content? Use semantic search
   - Want to see decisions only? Filter by event_type="decision"

**Example uses:**
- "Show me the Phase 3 timeline"
- "What happened on October 10th?"
- "Timeline of debugging attempts this week"
- "All architectural decisions made last month"

**Note:** Chronological mode returns memories in **time order**, not by relevance. Perfect for reconstructing "what we did and when."
