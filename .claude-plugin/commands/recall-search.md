# Search Recall Memory (Semantic Mode)

Search stored memories by meaning using semantic similarity.

**Instructions:**

1. **Get the search query** - Ask the user what they're looking for:
   - "What decisions about embeddings?"
   - "Architecture choices made last week"
   - "How did we solve the OAuth issue?"
   - "User preferences about coding style"

2. **Optional filters** - Ask if they want to narrow the search:
   - Session ID to filter by project/phase
   - Minimum similarity score (0-1, default: 0.0)
   - Event types to include
   - Number of results (default: 10)

3. **Perform semantic search** using `mcp__recall__recall_memory()`:

```python
mcp__recall__recall_memory(
    query="[search query by meaning]",
    top_k=10,
    session_id="[optional session filter]",
    min_score=0.5,  # Optional: similarity threshold
    retrieval_mode="semantic"
)
```

4. **Present results** - Show:
   - Number of matching memories found
   - Similarity scores (higher = more relevant)
   - Session IDs and timestamps
   - Event types (decision, discovery, etc.)
   - Content previews

5. **Suggest refinements** if needed:
   - Too many results? Increase min_score or add session_id filter
   - Too few results? Lower min_score or broaden query
   - Need time-based results? Use `/recall-timeline` instead

**Example queries:**
- "What embedding models did we evaluate?"
- "Debugging approaches that worked"
- "Performance optimization decisions"
- "User's preferred testing patterns"

**Note:** Semantic search finds memories by **meaning**, not exact keywords. It understands synonyms and related concepts.
