# Store Memory to Recall

Store important information to Recall's semantic memory for later retrieval.

**Instructions:**

1. **Identify what to store** - Ask the user what information they want to remember:
   - Important decisions and their rationale
   - Discoveries and insights
   - Milestone completions
   - User preferences learned
   - Problems encountered and solutions
   - Successful approaches that worked

2. **Gather metadata** - Ask for context:
   - Session ID (e.g., "phase3_architecture", "bug_investigation_2025-10")
   - Event type: `decision`, `discovery`, `milestone`, `preference`, `error`, or `success`
   - Tags (comma-separated topics)
   - Context (why is this being stored?)
   - Outcome (what happened or was decided?)

3. **Store the memory** using `mcp__recall__ingest_memory()`:

```python
mcp__recall__ingest_memory(
    content="[The content to remember]",
    session_id="[session identifier]",
    metadata={
        "event_type": "[decision|discovery|milestone|preference|error|success]",
        "tags": "topic1,topic2,topic3",
        "context": "Why this memory was created",
        "outcome": "What happened or was decided"
    }
)
```

4. **Confirm storage** - Report success with:
   - Number of chunks stored
   - Session ID used
   - Event type
   - Reminder that this can be retrieved later via `/recall-search` or `/recall-timeline`

**Example:**

"I stored your decision to use Arctic embedder (87% accuracy) in the 'architecture_decisions' session. You can retrieve this later with `/recall-search \"embedding model decisions\"`"
