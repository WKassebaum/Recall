# Recall Setup Verification

Verify that Recall is properly installed and configured.

**Tasks to perform:**

1. Check if Recall MCP tools are available by calling `mcp__recall__memory_stats()`
2. Verify the response shows:
   - Active embedder model (should be `snowflake-arctic-embed-m` or fallback)
   - Collection name (e.g., `recall_768d`)
   - Qdrant mode: `embedded (~/.recall/qdrant)` ✅
   - Total chunks count
3. Report the setup status clearly:
   - ✅ **Recall is working properly** - embedded Qdrant at ~/.recall/qdrant
   - ⚠️  **First launch note**: If this is your first time, sentence-transformers will download the Arctic embedding model (~3.5GB) from HuggingFace. This takes 30-60 seconds on a good connection.
   - ❌ **Installation issues detected** - provide error details

**Zero setup required:** Recall uses embedded Qdrant that stores data locally at `~/.recall/qdrant/`. No external database setup needed.
