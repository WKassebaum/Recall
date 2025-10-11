# Testing Recall v1.3.3 - Plugin Installation Guide

> **Quick test guide for validating the Recall Claude Code plugin**

This guide walks you through testing Recall's plugin installation and core features. Expected time: **5-10 minutes** (includes first-time model download).

---

## ✅ Prerequisites Check

Before starting, verify you have:

- [ ] **Claude Code CLI** installed and working
  ```bash
  claude --version
  # Should show: Claude Code version X.X.X
  ```

- [ ] **Python 3.10+** installed
  ```bash
  python --version
  # Should show: Python 3.10.X or higher
  ```

- [ ] **Internet connection** (for downloading embedding model ~3.5GB)

- [ ] **~5GB free disk space** (for model cache)

---

## 🚀 Step-by-Step Test

### Step 1: Install Recall Plugin

**Open Claude Code** and run this command inside Claude Code:

```bash
/plugin install https://github.com/WKassebaum/Recall
```

**Expected output:**
```
Installing plugin from https://github.com/WKassebaum/Recall...
✅ Plugin 'recall' installed successfully
```

**⚠️ Important Notes:**
- This command must be run **inside Claude Code**, not in your terminal
- The `/` prefix indicates a Claude Code slash command
- Installation should complete in 2-5 seconds

**❌ If plugin install fails:**
- Check internet connection
- Verify GitHub URL is correct: `https://github.com/WKassebaum/Recall`
- Try direct install: `/plugin install WKassebaum/Recall`

---

### Step 2: Run Setup & Validation

**In Claude Code**, run:

```bash
/recall-setup
```

**Expected output:**

```
🔧 Recall Setup & Validation

✅ Qdrant initialized in embedded mode
⏳ Loading embedding model (first time: downloading ~3.5GB)...
   [This takes 30-60 seconds on first run]
✅ Embedding model loaded: snowflake-arctic-embed-m (768D)
✅ Collections initialized: recall_768d
✅ Test memory stored: chunk_test_abc123
✅ Test memory retrieved (score: 1.000)
✅ All systems operational

📊 Configuration:
- Embedder: snowflake-arctic-embed-m
- Dimension: 768D
- Active collection: recall_768d
- Total chunks: 1
- Qdrant: embedded (~/.recall/qdrant/)

⚡ Performance:
- Query latency: 17.5ms (target: <500ms)
- Embedding time: 35ms

🎉 Recall is ready to use!

Try:
- /recall-store - Store a memory
- /recall-search <query> - Search memories
- /recall-stats - View statistics
```

**⏱️ First-time setup timing:**
- Model download: 30-60 seconds (one-time only)
- Subsequent runs: <5 seconds

**❌ If setup fails:**

1. **Model download fails:**
   ```
   ❌ Failed to download embedding model
   ```
   **Fix:**
   - Check internet connection
   - Verify HuggingFace is accessible: `curl https://huggingface.co`
   - Check disk space: `df -h` (~5GB needed)
   - Try manual download in terminal:
     ```bash
     python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('Snowflake/snowflake-arctic-embed-m')"
     ```

2. **Permission errors:**
   ```
   ❌ Permission denied writing to ~/.cache/huggingface/
   ```
   **Fix:** Check cache directory permissions:
   ```bash
   mkdir -p ~/.cache/huggingface
   chmod 755 ~/.cache/huggingface
   ```

---

### Step 3: Test Core Features

Now test the main slash commands:

#### A. Store a Memory

**In Claude Code:**
```bash
/recall-store
```

Claude will prompt you for:
1. **Content:** "Testing Recall plugin installation"
2. **Session ID:** "test-session"
3. **Event Type:** decision
4. **Tags:** "testing,plugin"
5. **Context:** "Validating plugin installation"
6. **Outcome:** "Successfully stored test memory"

**Expected:** Confirmation message showing memory was stored

#### B. Search Memories

**In Claude Code:**
```bash
/recall-search testing
```

**Expected output:**
```
Found 1 relevant memories (SEMANTIC mode):

--- Memory 1 (Score: 0.892) [decision] ---
Session: test-session
Ingested: 2025-10-11T12:34:56+00:00
Content:
Testing Recall plugin installation
```

**✅ Success criteria:**
- Returns your test memory
- Score is > 0.8 (high relevance)
- Shows correct session and event type

#### C. View Timeline

**In Claude Code:**
```bash
/recall-timeline --session test-session
```

**Expected output:**
```
Found 1 relevant memories (CHRONOLOGICAL mode):

--- Memory 1 [decision] ---
Session: test-session
Ingested: 2025-10-11T12:34:56+00:00
Content:
Testing Recall plugin installation
```

**✅ Success criteria:**
- Shows memories in time order
- No similarity scores (chronological doesn't use them)

#### D. Check Statistics

**In Claude Code:**
```bash
/recall-stats
```

**Expected output:**
```
📊 Recall Statistics:
Total chunks: 1
Active collection: recall_768d
Embedder: Snowflake/snowflake-arctic-embed-m
Dimension: 768D
Qdrant: embedded (~/.recall/qdrant/)
```

**✅ Success criteria:**
- Shows at least 1 chunk (from test)
- Active collection is recall_768d
- Embedder is Snowflake/snowflake-arctic-embed-m

---

## 🎯 Test Completion Checklist

After completing all steps, verify:

- [x] Plugin installed successfully (`/plugin install`)
- [x] Setup passed all checks (`/recall-setup`)
- [x] Embedded Qdrant initialized (`~/.recall/qdrant/` created)
- [x] Stored a test memory (`/recall-store`)
- [x] Searched and found memory (`/recall-search`)
- [x] Timeline shows memories (`/recall-timeline`)
- [x] Stats show correct config (`/recall-stats`)

**If all checks pass:** ✅ **Plugin is working correctly!**

---

## 🐛 Common Issues & Solutions

### Issue 1: "Command not found: /recall-setup"

**Cause:** Plugin not installed or Claude Code not restarted

**Fix:**
1. Verify plugin installed: Run `/plugin list` in Claude Code
2. Should see "recall" in the list
3. If not listed, retry: `/plugin install https://github.com/WKassebaum/Recall`

---

### Issue 2: "No matching memories found" after storing

**Cause:** Wrong collection or session mismatch

**Fix:**
1. Check stats: `/recall-stats`
2. Verify active collection matches storage
3. Use same session ID for search: `/recall-search testing --session test-session`

---

### Issue 3: Slow first-time model download

**Cause:** Large embedding model (3.5GB)

**Not a bug:** This is expected behavior
- First run: 30-60 seconds
- Subsequent runs: <5 seconds
- Model cached permanently to `~/.cache/huggingface/`

**Speed up next time:**
Pre-download model outside Claude Code:
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('Snowflake/snowflake-arctic-embed-m')"
```

---

## 📊 Expected Performance

After successful setup, you should see:

**Query Performance:**
- Semantic search: ~17ms average
- Chronological search: ~20-30ms
- Hybrid search: ~25-40ms

**Memory Usage:**
- Arctic model: ~3.5GB disk (cached)
- Runtime RAM: <1GB typical
- Qdrant: ~200MB RAM

**Accuracy:**
- Semantic relevance: 87% (Arctic model)
- Exact match: 100% (chunk ID lookup)

---

## 🔍 Advanced Testing (Optional)

If basic tests pass, try these advanced scenarios:

### Test 1: Multiple Sessions

Store memories in different sessions and verify isolation:

```bash
/recall-store
# Session: session-a, Content: "Memory from session A"

/recall-store
# Session: session-b, Content: "Memory from session B"

/recall-search "memory" --session session-a
# Should only return session-a memories
```

### Test 2: Event Type Filtering

```bash
/recall-timeline --session test-session --events decision,milestone
# Should only show decision and milestone events
```

### Test 3: Time Range Queries

```bash
/recall-timeline --from 2025-10-11 --to 2025-10-12
# Should show memories from that date range
```

### Test 4: Hybrid Mode

```bash
# Store more memories first, then:
/recall-search "debugging" --mode hybrid --from 2025-10-10
# Should combine semantic relevance + time filtering
```

---

## 📞 Reporting Issues

If you encounter problems:

1. **Check this guide first** - Most issues have solutions above
2. **Collect diagnostic info:**
   ```bash
   # System info
   claude --version
   python --version

   # Recall stats
   /recall-stats  # In Claude Code

   # Check embedded Qdrant
   ls -la ~/.recall/qdrant/
   ```

3. **Report issue on GitHub:**
   - Go to: https://github.com/WKassebaum/Recall/issues
   - Include: Steps to reproduce, error messages, diagnostic info
   - Label: `bug`, `plugin`, `testing`

---

## ✅ Success!

If all tests pass, congratulations! You've successfully:

✅ Installed Recall as a Claude Code plugin
✅ Initialized embedded vector database in ~/.recall/qdrant/
✅ Downloaded the Arctic embedding model (768D)
✅ Stored and retrieved memories
✅ Used slash commands for common operations

**Next Steps:**
- Try using Recall in real coding sessions
- Store important decisions and discoveries
- Use `/recall-search` to find past context
- Check out [CLAUDE.md](CLAUDE.md) for advanced usage patterns

---

**Test Duration:** 5-10 minutes (first time), 2-3 minutes (subsequent runs)

**Plugin Version:** v1.3.3
**Last Updated:** 2025-10-11
