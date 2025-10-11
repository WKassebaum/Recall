# Store Memory in Recall

Store important events, decisions, or discoveries in your external memory.

## Usage

`/recall-store`

This command helps you store memories with proper event metadata.

## What It Does

Guides you through storing a memory by prompting for:

1. **Content**: What you want to remember
2. **Session ID**: Organizational grouping (e.g., "phase3", "feature-auth")
3. **Event Type**: One of:
   - `decision` - Architecture, tool selection, approach changes
   - `discovery` - Findings, insights, "what we learned"
   - `milestone` - Waypoint completions, phase transitions
   - `preference` - User preferences, coding style learned
   - `error` - Problems encountered, failure modes
   - `success` - Solutions that worked, validated approaches
4. **Tags**: Comma-separated topics (e.g., "architecture,embeddings,performance")
5. **Context**: Why this memory was created
6. **Outcome**: What happened or was decided

## Example

```
You: /recall-store

Claude: I'll help you store a memory. Please provide:

Content: "Selected Arctic embedder after benchmark showing 93.3% accuracy"
Session ID: "architecture_decisions"
Event Type: decision
Tags: "architecture,embeddings,performance"
Context: "Comparing 4 embedding models on accuracy benchmark"
Outcome: "Arctic selected as primary, MiniLM as fallback"

[Calls mcp__recall__ingest_memory with the provided information]

✅ Stored memory with event_type="decision" in session "architecture_decisions"
```

## When to Use

- **After making decisions** - Architecture, tools, approaches
- **When you discover something** - Bug root causes, insights
- **At milestones** - Waypoint completions, phase transitions
- **When context is filling up** - Offload details to Recall

## Tips

- Store immediately after the event (don't batch)
- Use descriptive session_ids for easy filtering
- Tag liberally for better discoverability
- Be specific in content (future you will thank you)
