# Recall Setup Verification

Verify that Recall is properly installed and configured.

**Tasks to perform:**

1. **Check if Python dependencies are installed first:**
   ```bash
   # Find plugin directory
   PLUGIN_DIR=$(find ~/.claude/plugins -type d -name "recall@*" 2>/dev/null | head -1)

   if [ -n "$PLUGIN_DIR" ]; then
       cd "$PLUGIN_DIR"
       # Quick dependency check
       python -c "import mcp, qdrant_client, sentence_transformers" 2>/dev/null
       if [ $? -ne 0 ]; then
           echo "❌ Python dependencies not installed"
           echo ""
           echo "Please run: /recall-install"
           echo "Then restart Claude Code and try again"
           exit 1
       fi
   fi
   ```

2. **Check if Recall MCP tools are available** by calling `mcp__recall__memory_stats()`

3. **Verify the response shows:**
   - Active embedder model (should be `snowflake-arctic-embed-m` or fallback)
   - Collection name (e.g., `recall_768d`)
   - Qdrant mode: `embedded (~/.recall/qdrant)` ✅
   - Total chunks count

4. **Report the setup status clearly:**
   - ✅ **Recall is working properly** - embedded Qdrant at ~/.recall/qdrant
   - ⚠️  **First launch note**: If this is your first time, sentence-transformers will download the Arctic embedding model (~3.5GB) from HuggingFace. This takes 30-60 seconds on a good connection.
   - ❌ **Dependencies not installed** - run `/recall-install` first
   - ❌ **Other installation issues detected** - provide error details

**Zero database setup required:** Recall uses embedded Qdrant that stores data locally at `~/.recall/qdrant/`. No external database setup needed.
