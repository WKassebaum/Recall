# Recall MCP Integration Test Plan

**Status:** Ready for testing after Claude Code restart
**Version:** v1.3.1
**Date:** 2025-10-10

---

## Overview

The Recall MCP server has been integrated into Claude Code's MCP configuration. After restarting Claude Code, you'll have access to three new tools for semantic memory management:

- `mcp__recall__ingest_memory` - Store content in vector memory
- `mcp__recall__recall_memory` - Search stored memories semantically
- `mcp__recall__memory_stats` - Get system statistics

This enables **dogfooding** - using Recall to remember our own development sessions!

---

## Prerequisites

✅ Recall MCP server configured in `~/.config/claude-code/settings.json`
✅ Qdrant running on `localhost:6333`
✅ Arctic embedder model configured in `config.yaml`
✅ All 139 tests passing
✅ Performance validated (17.5ms queries)

---

## Test Scenarios

### Test 1: Basic Ingestion and Retrieval

**Objective:** Verify end-to-end pipeline works

**Steps:**

1. **Restart Claude Code** to load Recall MCP server

2. **Ingest test content:**
   ```
   Use mcp__recall__ingest_memory with:
   - content: "Phase 3 completed with 93.3% accuracy on Arctic model. Query latency 17.5ms, 28x faster than target. All 17 waypoints passing."
   - session_id: "semvecmem_phase3"
   - content_type: "prose"
   ```

3. **Verify ingestion:**
   ```
   Use mcp__recall__memory_stats
   Expected: Shows 1+ chunks, recall_768d collection, Arctic embedder
   ```

4. **Test semantic retrieval:**
   ```
   Use mcp__recall__recall_memory with:
   - query: "What were the Phase 3 benchmark results?"
   - session_id: "semvecmem_phase3"
   - top_k: 5
   ```

   **Expected Result:**
   - Should return the ingested content with high similarity score (>0.7)
   - Should mention "93.3% accuracy" and "Arctic model"

---

### Test 2: Multi-Content Type Ingestion

**Objective:** Validate chunking strategies work via MCP

**Steps:**

1. **Ingest Python code:**
   ```
   Use mcp__recall__ingest_memory with:
   - content: [A Python function from our codebase, e.g., UnifiedVectorStore.search()]
   - session_id: "code_snippets"
   - content_type: "python"
   ```

2. **Ingest Markdown:**
   ```
   Use mcp__recall__ingest_memory with:
   - content: [Section from PHASE_3_COMPLETION_SUMMARY.md]
   - session_id: "documentation"
   - content_type: "markdown"
   ```

3. **Ingest JSON:**
   ```
   Use mcp__recall__ingest_memory with:
   - content: [Sample from performance_report.json]
   - session_id: "metrics"
   - content_type: "json"
   ```

4. **Verify auto-detection works:**
   ```
   Use mcp__recall__ingest_memory with:
   - content: [Some code without specifying content_type]
   - session_id: "auto_detect_test"
   - content_type: null (omit this parameter)
   ```

**Expected Results:**
- Each ingestion should report appropriate chunk counts
- Python code should be chunked by functions/classes
- Markdown should be chunked by sections
- JSON should preserve structure
- Auto-detection should work correctly

---

### Test 3: Session-Based Filtering

**Objective:** Verify metadata filtering works

**Steps:**

1. **Ingest content with different session IDs:**
   ```
   Session A: "Frontend work on React components"
   Session B: "Backend API development with FastAPI"
   Session C: "Database optimization with Qdrant"
   ```

2. **Query with session filter:**
   ```
   Use mcp__recall__recall_memory with:
   - query: "development"
   - session_id: "session_b"
   - top_k: 10
   ```

**Expected Result:**
- Should only return content from Session B
- Should not return content from Sessions A or C

---

### Test 4: Score Threshold Filtering

**Objective:** Validate min_score parameter works

**Steps:**

1. **Search with low threshold:**
   ```
   Use mcp__recall__recall_memory with:
   - query: "performance metrics"
   - min_score: 0.3
   - top_k: 10
   ```

2. **Search with high threshold:**
   ```
   Use mcp__recall__recall_memory with:
   - query: "performance metrics"
   - min_score: 0.7
   - top_k: 10
   ```

**Expected Results:**
- Low threshold: More results (including less relevant ones)
- High threshold: Fewer results (only highly relevant ones)
- All returned results should meet minimum score requirement

---

### Test 5: Real-World Dogfooding

**Objective:** Use Recall to remember actual development sessions

**Scenario:** Store and retrieve knowledge from this Phase 3 work

**Steps:**

1. **Ingest Phase 3 summary:**
   ```
   Use mcp__recall__ingest_memory with:
   - content: [Contents of PHASE_3_COMPLETION_SUMMARY.md]
   - session_id: "semvecmem_development"
   - content_type: "markdown"
   ```

2. **Ingest key code snippets:**
   ```
   - UnifiedVectorStore implementation
   - MCP server tools
   - Benchmark results
   - Performance profiler results
   ```

3. **Test retrieval with real questions:**
   - "How did we implement multi-collection routing?"
   - "What were the accuracy benchmarks?"
   - "What performance targets did we achieve?"
   - "What chunking strategies are supported?"

**Expected Results:**
- Should retrieve relevant context for each question
- Should demonstrate practical utility for development memory
- Should show fast query times (<100ms)

---

### Test 6: Performance Validation

**Objective:** Verify performance matches expectations

**Metrics to Monitor:**

1. **Query Latency:**
   - Target: <500ms
   - Expected: ~17-25ms (based on performance profiling)
   - Measure: Time from tool call to response

2. **Ingestion Latency:**
   - Target: <100ms per chunk
   - Expected: ~30-80ms per chunk
   - Measure: Time reported in ingestion response

3. **Memory Usage:**
   - Target: <8GB total
   - Monitor: System memory during operations

4. **Result Quality:**
   - Target: Relevant results in top 5
   - Expected: High similarity scores (>0.6) for relevant content
   - Validate: Manually review search results

---

### Test 7: Error Handling

**Objective:** Verify graceful error handling

**Test Cases:**

1. **Empty content:**
   ```
   Use mcp__recall__ingest_memory with:
   - content: ""
   - session_id: "error_test"
   ```
   Expected: Should handle gracefully with helpful message

2. **No results query:**
   ```
   Use mcp__recall__recall_memory with:
   - query: "zzzzzz_nonexistent_content_zzzzzz"
   - top_k: 10
   ```
   Expected: "No matching memories found."

3. **Invalid session filter:**
   ```
   Use mcp__recall__recall_memory with:
   - query: "test"
   - session_id: "nonexistent_session_12345"
   ```
   Expected: Should return empty results gracefully

---

## Success Criteria

✅ **All MCP tools accessible** after restart
✅ **Ingestion works** with all content types (Python, Markdown, JSON, prose)
✅ **Auto-detection** correctly identifies content types
✅ **Semantic search** returns relevant results with high scores
✅ **Session filtering** isolates results by session_id
✅ **Score thresholding** filters low-relevance results
✅ **Performance targets met** (<500ms queries, <8GB memory)
✅ **Error handling** graceful and informative
✅ **Real-world utility** demonstrated via dogfooding

---

## Troubleshooting

### Server Not Available After Restart

**Check:**
```bash
# Verify settings.json is valid JSON
cat ~/.config/claude-code/settings.json | python -m json.tool

# Test server manually
PYTHONPATH=/Users/wrk/WorkDev/MCP-Dev/SemVecMem/src \
  /Users/wrk/WorkDev/MCP-Dev/SemVecMem/venv/bin/python \
  -m recall.mcp.server
```

**Common Issues:**
- PYTHONPATH not set correctly
- Qdrant not running (`docker ps | grep qdrant`)
- Config file missing (`config.yaml` in project root)
- Virtual environment corrupted

### Low-Quality Search Results

**Check:**
- Embedder model loaded correctly (Arctic preferred)
- Sufficient content ingested (need multiple chunks)
- Query is specific enough (avoid single-word queries)
- Similarity scores reasonable (>0.5 for relevant content)

### Slow Query Performance

**Check:**
- Qdrant running locally (not remote)
- Collection size reasonable (<100k chunks for testing)
- Embedder using MPS acceleration (M1 Max)
- Network latency to Qdrant

---

## Post-Test Documentation

After completing tests, document:

1. **What worked well:**
   - Tool responsiveness
   - Result quality
   - Performance metrics

2. **Issues encountered:**
   - Bugs or unexpected behavior
   - Performance bottlenecks
   - Usability concerns

3. **Real-world insights:**
   - Practical utility for development memory
   - Integration with existing workflow
   - Feature requests or improvements

4. **Performance comparison:**
   - Actual vs. expected latency
   - Memory usage patterns
   - Scaling observations

---

## Next Steps After Testing

### If All Tests Pass ✅

1. Update documentation with real-world examples
2. Add MCP integration to README
3. Create user guide for Claude Code integration
4. Tag v1.3.1 release
5. Push to remote repository

### If Issues Found ⚠️

1. Document specific failures
2. Create issue tickets for bugs
3. Fix critical issues before release
4. Re-run affected test scenarios
5. Update test plan based on findings

---

## Testing Checklist

- [ ] Claude Code restarted
- [ ] Qdrant running on localhost:6333
- [ ] Test 1: Basic ingestion and retrieval ✅
- [ ] Test 2: Multi-content type ingestion ✅
- [ ] Test 3: Session-based filtering ✅
- [ ] Test 4: Score threshold filtering ✅
- [ ] Test 5: Real-world dogfooding ✅
- [ ] Test 6: Performance validation ✅
- [ ] Test 7: Error handling ✅
- [ ] Success criteria met ✅
- [ ] Issues documented (if any)
- [ ] Performance metrics recorded
- [ ] User feedback captured

---

**Ready to test!** Restart Claude Code and begin validation. 🚀

**Generated:** 2025-10-10
**Test Plan Version:** 1.0
**Author:** Claude Code (Phase 3 completion)
