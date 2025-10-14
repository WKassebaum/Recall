# Recall System Statistics

View Recall system health and memory statistics.

**Instructions:**

1. **Get current statistics** using `mcp__recall__memory_stats()`

2. **Present the statistics clearly:**
   - 📊 **Total chunks stored** - How many memory chunks exist
   - 🗂️ **Active collection** - Which Qdrant collection is being used (e.g., `recall_768d`)
   - 🧠 **Embedder model** - Active embedding model (e.g., `snowflake-arctic-embed-m`)
   - 📏 **Dimension** - Embedding dimension (384D, 768D, or 1024D)
   - 💾 **Qdrant mode** - Should show `embedded (~/.recall/qdrant)` ✅
   - 💽 **Storage location** - Where memories are stored on disk

3. **Interpret the stats**:
   - If total chunks = 0: "No memories stored yet. Use `/recall-store` to start building your memory."
   - If embedder is fallback (all-MiniLM-L6-v2): "⚠️ Using fallback model - Arctic may have failed to load"
   - If collection dimension mismatches: Explain multi-collection strategy

4. **Suggest next actions**:
   - Low chunk count: "Start storing important decisions with `/recall-store`"
   - Good chunk count: "Use `/recall-search` or `/recall-timeline` to explore your memories"
   - First time user: "Your memory system is ready! Try `/recall-setup` to verify installation"

**What these stats tell you:**
- **System health** - Is Recall configured correctly?
- **Memory usage** - How much you've stored
- **Configuration** - Which models and settings are active
- **Storage backend** - Embedded (local) or network mode

**Note:** Embedded Qdrant stores data at `~/.recall/qdrant/` - completely local, no cloud dependencies.
