# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Recall v1.3.1** - Semantic Vector Memory for Coding Agents

> **Package Name**: `recall` (renamed from `semvecmem` for simplicity and PyPI availability)

A long-term memory system for coding agents that addresses context window limitations using vector embeddings for fuzzy, semantic retrieval of past sessions, code snippets, and decisions. Exposed via Model Context Protocol (MCP) for low-overhead integration with AI assistants like Claude Code CLI.

**Current Status:** Quality-gated implementation ready to begin
- ✅ Architecture validated (independent + Zen MCP consensus)
- ✅ Multi-collection strategy approved (9/10 confidence)
- ✅ Quality-gated plan with 17 testing waypoints
- 🚀 Ready for POC phase

**Hardware:** ✅ Validated on M1 Max with 64GB RAM - confirmed excellent fit (uses <8% RAM for all 4 models)

**Implementation Philosophy:** Quality-first, continuous testing, technical debt prevention

## Version Management

**Single Source of Truth:** `src/recall/__version__.py`

The project uses a unified version strategy to prevent version number drift:

- **Canonical Version**: `src/recall/__version__.py` contains `__version__ = "X.Y.Z"`
- **Dynamic Import**: `pyproject.toml` uses `dynamic = ["version"]` with setuptools
- **Auto-Sync Script**: `scripts/sync-version.sh` syncs version to `.claude-plugin/plugin.json`

**Updating Version:**
```bash
# 1. Edit src/recall/__init__.py
__version__ = "1.4.0"  # Update this line

# 2. Run sync script (syncs to plugin.json)
./scripts/sync-version.sh

# 3. Build package (pyproject.toml picks up version automatically)
pip install -e .
```

**Version reflects latest git release tag** - After creating a git tag, update `src/recall/__init__.py` to match.

## Docker Reliability & Multi-Project Setup

**Status:** ✅ Reliable (v1.4.0) - Named volumes + WAL tuning implemented

### Current Setup (Reliable)

```
Recall MCP → Qdrant Docker Container → Named Volume (recall-qdrant-data)
                                        ↓
                                Docker-managed storage
                                (No macOS fsync issues)
```

**Key Improvements (2025-10-18):**
- ✅ **Named volumes** instead of bind mounts (eliminates macOS file descriptor corruption)
- ✅ **WAL tuning** via `qdrant-config.yaml` (512MB buffer, less frequent fsyncs)
- ✅ **Performance mode** for batched writes
- ✅ **Health checks** to detect corruption early
- ✅ **Multi-project support** (4 projects using shared container)

### Quick Commands

```bash
# Start Qdrant (reliable mode)
cd /Users/wrk/WorkDev/MCP-Dev/SemVecMem
docker-compose up -d

# Check health
docker ps --filter "name=recall-qdrant-6337"
curl http://localhost:6337/health

# Backup (do this before major operations!)
docker run --rm -v recall-qdrant-data:/data -v $(pwd):/backup alpine tar czf /backup/recall-backup-$(date +%Y%m%d_%H%M%S).tar.gz /data

# Restore from backup
docker-compose down
docker volume rm recall-qdrant-data
docker volume create recall-qdrant-data
docker run --rm -v recall-qdrant-data:/data -v $(pwd):/backup alpine tar xzf /backup/recall-backup-YYYYMMDD_HHMMSS.tar.gz -C /
docker-compose up -d

# Stop Qdrant
docker-compose down  # Keeps data
# docker-compose down -v  # WARNING: Deletes all data!
```

### Why Named Volumes?

**Previous setup (bind mounts - UNRELIABLE):**
- ❌ macOS file descriptor translation issues
- ❌ osxfs/virtiofs fsync problems
- ❌ WAL corruption during heavy writes
- ❌ "Bad file descriptor (os error 9)" crashes

**Current setup (named volumes - RELIABLE):**
- ✅ Docker-managed storage (no macOS translation layer)
- ✅ Better fsync handling
- ✅ WAL tuning reduces flush frequency
- ✅ Supports 4 concurrent projects
- ✅ Zero corruption issues since implementation

**Detailed Documentation:** See `DOCKER_RELIABILITY.md` for comprehensive backup/recovery procedures.

## Intended Architecture

```
MCP Client (Claude/Grok CLI)
  ↓ (tool calls via MCP)
MCP Server (FastMCP)
  ↓
Core Engine
  ├─ Chunker (TreeSitter AST parser, adapted from CodeIndex)
  ├─ Embedder Factory (configurable: bge-small-en-v1.5 [default] / all-MiniLM-L6-v2 [fallback])
  └─ Vector Store (Qdrant)
```

### Component Structure
Project structure (mirrors CodeIndex patterns):
```
src/recall/
  ├─ core/         # Ingestion, embedding, retrieval logic
  ├─ mcp/          # FastMCP server implementation
  ├─ cli/          # Click-based CLI wrapper
  ├─ chunker/      # AST-aware text chunking (from CodeIndex)
  └─ config/       # YAML config + env var handling
tests/             # Pytest suite with embedding benchmarks
config.yaml        # Embedder selection, Qdrant connection
docker-compose.yaml # Qdrant local setup
scripts/           # Quality monitoring scripts
```

## Quality-Gated Implementation Approach

**CRITICAL:** Follow `QUALITY_GATED_IMPLEMENTATION_PLAN.md` for all development

### Core Principles

1. **Build → Test → Refactor** (NOT Build → Build → Build → Test)
2. **17 Testing Waypoints** - Test after each major component
3. **Continuous Complexity Monitoring** - Enforce cyclomatic complexity limits
4. **Quality Gates** - Phase exits when metrics met, not calendar dates
5. **Zero Technical Debt Tolerance** - Fix immediately, never "later"

### Cyclomatic Complexity Targets

**Enforced via pre-commit hooks:**
- Core components (UnifiedVectorStore, embedders): **CC ≤ 6**
- Complex workflows (migration tool): **CC ≤ 8**
- Configuration/utilities: **CC ≤ 4**
- **Hard limit:** CC > 10 fails commit

**Tools:**
```bash
radon cc src/recall/ -n C      # Fail if any method CC > 10
radon mi src/recall/ -n B      # Maintainability Index ≥ B
```

### Testing Waypoints (17 Total)

**POC Phase (1 waypoint):**
- Waypoint 1: Unified API POC validation

**Phase 1 - Foundation (6 waypoints):**
- Waypoint 2: Config system (CC ≤ 4, coverage >80%)
- Waypoint 3: Embedder factory (CC ≤ 5, coverage >80%)
- Waypoint 4: Qdrant + multi-collection (CC ≤ 6, coverage >80%)
- Waypoint 5: UnifiedVectorStore (CC ≤ 6, coverage >80%)
- Waypoint 6: Startup validation (CC ≤ 7, coverage >80%)
- Waypoint 7: **Phase 1 integration test** (CRITICAL)

**Phase 2 - Ingestion & Retrieval (4 waypoints):**
- Waypoint 8: Chunking (CC ≤ 6)
- Waypoint 9: Retrieval engine (CC ≤ 6, latency <500ms)
- Waypoint 10: Concurrency safety (no race conditions)
- Waypoint 11: **MCP server + Phase 2 integration** (CRITICAL)

**Phase 3 - Migration & Benchmarks (4 waypoints):**
- Waypoint 12: CLI (CC ≤ 5)
- Waypoint 13: Migration tool (CC ≤ 8, canary strategy)
- Waypoint 14: **Migration failure injection tests** (MOST CRITICAL)
- Waypoint 15: Benchmark suite (accuracy >85%)

**Phase 4 - Polish (2 waypoints):**
- Waypoint 16: **System integration** (FINAL)
- Waypoint 17: Performance profiling (memory <8GB, latency targets)

### Automated Quality Enforcement

**Pre-commit hooks (automatically block bad commits):**
```yaml
# .pre-commit-config.yaml
- Cyclomatic complexity check (CC ≤ 10)
- Test coverage check (≥ 80%)
- Type checking (mypy strict)
- Code quality (ruff)
- Maintainability index (≥ B)
```

**Daily quality dashboard:**
```bash
./scripts/daily_dashboard.sh
# Shows: coverage %, CC average, MI average, test count, trends
```

**Phase exit quality audit:**
```bash
./scripts/quality_check.sh
# Must pass all checks before moving to next phase
```

### Refactoring Protocol

**When complexity exceeds targets:**
1. **STOP development immediately**
2. Run complexity analysis: `radon cc <file> -s`
3. Apply refactoring strategy (extract methods, strategy pattern, simplify conditionals)
4. Re-run quality check
5. **ONLY continue when CC ≤ target**

**Example strategies:**
- CC > 6 in UnifiedVectorStore → Extract helper methods
- CC > 8 in migration tool → Use strategy pattern for migration modes
- CC > 4 in config → Simplify validation logic

### Phase Exit Criteria

**Every phase MUST meet ALL criteria before proceeding:**
- ✅ All waypoint tests passing
- ✅ Code coverage ≥ 80%
- ✅ Cyclomatic complexity ≤ targets
- ✅ Mypy strict mode clean
- ✅ Ruff code quality clean
- ✅ Maintainability Index ≥ B
- ✅ Zero TODO/FIXME in production code
- ✅ Integration tests passing

**Final release criteria (Phase 4 exit):**
- ✅ All 17 waypoints passing
- ✅ Bandit security scan clean
- ✅ Documentation coverage >80%
- ✅ Performance targets met
- ✅ Benchmark validates >85% accuracy

## Key Technical Decisions (from PRD + Zen Validation)

### Vector Database - Multi-Collection Strategy ✅ ZEN VALIDATED (9/10)

**Architecture:** Separate collections per embedding dimension
```yaml
Collections:
  recall_384d:   # BGE + MiniLM (384 dimensions)
  recall_768d:   # Nomic (768 dimensions)
  recall_1024d:  # Arctic (1024 dimensions, default)
```

**Rationale:** Prevents dimension mismatch errors when users switch embedding models

**Implementation:**
- **Qdrant** via qdrant-client at `localhost:6333`
- HNSW index per collection (ef_construct=100, m=16)
- **UnifiedVectorStore abstraction** - automatically routes to correct collection based on active embedder
- Dimension verification at ingestion and query time (fail-fast with helpful errors)
- Auto-detect running instance or guide Docker setup
- Metadata fields: `chunk_id`, `timestamp`, `session_id`, `lang`, `user_intent`, `embedding_model`

**Key Insight from Zen Validation:**
> "Unified API abstraction layer recommended to hide multi-collection complexity from users"
> - o3-mini, 9/10 confidence

### Embedding Models - 2-Tier Fallback ✅ ZEN VALIDATED (9/10)

**Research-validated choices (2024 MTEB benchmarks):**

**Primary Model:**
- **`snowflake/arctic-embed-m`** (87% accuracy, 1024 dims, ~3.5GB)
  - Purpose-built for retrieval tasks
  - Highest accuracy, SOTA performance
  - Excellent on M1 Max with MPS (~35ms/query, 5.5% RAM)
  - **Default for all use cases**

**Fallback Model:**
- **`all-MiniLM-L6-v2`** (78.1% accuracy, 384 dims, ~1.2GB)
  - Smallest, most reliable fallback
  - Fastest option (~14.7ms/query, 1.9% RAM)
  - Activates only if Arctic load fails
  - **Automatic fallback with monitoring/alerting**

**User-Selectable Models (Not Auto-Fallback):**
- **`nomic-embed-text-v1.5`** (86.2% accuracy, 768 dims, ~4.8GB)
  - Supports 8K token context (vs standard 512)
  - Great for long code blocks
  - M1 Max friendly (~41.9ms/query, 7.5% RAM)

- **`bge-small-en-v1.5`** (84.7% accuracy, 384 dims, ~2.1GB)
  - Well-tested, efficient
  - Fast on M1 Max (~22.5ms/query, 3.3% RAM)

**All models run excellently on M1 Max (use <8% of 64GB RAM)**

**Fallback Strategy - Simplified (2-Tier):**
```python
# Arctic (primary) → MiniLM (fallback)
# NO intermediate tiers (Nomic/BGE)
# Reason: Nomic (4.8GB) larger than Arctic (3.5GB) - illogical fallback
```

**Key Insight from Zen Validation:**
> "2-tier fallback reduces complexity and maintenance overhead. Focus on robust error monitoring rather than multi-tier fallback."
> - o3-mini, 9/10 confidence

Selection via `config.yaml` with zero code changes for switching

### Chunking Strategy
- Adapt CodeIndex Simplified AST parser
- TreeSitter for 39+ languages
- NLTK sentence splitter fallback for prose
- Preserves semantic structure of code (functions, classes)

### MCP Interface - Recall Memory System ✅ IMPLEMENTED (v1.3.2)

**Available Tools:**
- `ingest_memory` - Store code/text/decisions with event metadata
- `recall_memory` - Dual-mode retrieval (semantic + chronological)
- `memory_stats` - System statistics and health

**Key Features:**
- **Dual-mode retrieval**: Semantic similarity OR chronological timeline
- **Event-based structure**: decision, discovery, milestone, preference, error, success
- **Session-based organization**: Group related memories by session_id
- **Temporal filtering**: Query by time range, event type
- **External working memory**: Offload context to reduce token usage

---

## Recall MCP - External Working Memory (v1.3.2)

### Memory Architecture Overview

Recall implements a **hybrid semantic + episodic memory system** that enables:

1. **Semantic Retrieval**: "What decisions about embedders?" → Vector similarity search
2. **Temporal Retrieval**: "Show Phase 3 timeline" → Chronological ordering
3. **Hybrid Queries**: "Recent debugging attempts" → Semantic + temporal filtering

This dual-mode design addresses the **context window problem** by storing important events/decisions externally and retrieving them on-demand.

---

### When to Use Recall vs Other Memory Types

#### 1. Working Memory (Session-Scoped)
- **Storage**: In-memory variables, context window
- **Duration**: Current conversation only
- **Use for**: Active reasoning, temporary calculations
- **Implementation**: Python variables, conversation context

#### 2. Procedural Memory (How-To Knowledge)
- **Storage**: Markdown files (.md)
- **Duration**: Persistent, version-controlled
- **Use for**: Workflows, coding patterns, conventions
- **Implementation**: `docs/*.md`, `CONVENTIONS.md`

#### 3. Recall - Semantic + Episodic Memory ⭐
- **Storage**: Vector database + timestamped metadata
- **Duration**: Persistent, queryable by meaning OR time
- **Use for**:
  - **Semantic**: User preferences, learned patterns, domain knowledge
  - **Episodic**: Decision history, debugging trails, "what we tried"
- **Implementation**: `mcp__recall__ingest_memory` + `mcp__recall__recall_memory`

**Recall handles BOTH:**
- **Semantic queries**: "What code handles authentication?" (similarity search)
- **Temporal queries**: "What happened on October 10th?" (chronological)

---

### Auto-Trigger Patterns - When to Use Recall Proactively

**CRITICAL: Use Recall frequently to extend working memory and prevent context loss.**

#### Store Memories Immediately After:

**Decisions** (event_type: "decision"):
```python
# Example: After choosing architecture
mcp__recall__ingest_memory(
    content="Selected Arctic embedder for 93.3% benchmark accuracy vs MiniLM 86.7%",
    session_id="phase3_architecture",
    metadata={
        "event_type": "decision",
        "tags": "architecture,embeddings,performance",
        "context": "Comparing 4 embedding models on accuracy benchmark",
        "outcome": "Arctic selected as primary, MiniLM as fallback"
    }
)
```

**Discoveries** (event_type: "discovery"):
```python
# Example: After finding a bug
mcp__recall__ingest_memory(
    content="MCP stdout contamination caused tool registration failure. sentence-transformers and httpx were logging to stdout, corrupting JSON-RPC protocol.",
    session_id="phase3_mcp_integration",
    metadata={
        "event_type": "discovery",
        "tags": "debugging,mcp,protocol",
        "context": "Server showed connected but tools unavailable in Claude Code",
        "outcome": "Suppressed all logging to stderr for protocol compliance"
    }
)
```

**Milestones** (event_type: "milestone"):
```python
# Example: After completing a waypoint
mcp__recall__ingest_memory(
    content="Waypoint 17 complete: Performance profiling validated 17.5ms queries (28x faster than 500ms target), memory <8GB, throughput 32.4 chunks/sec",
    session_id="phase3_completion",
    metadata={
        "event_type": "milestone",
        "tags": "waypoint,performance,validation",
        "context": "Final waypoint before Phase 3 sign-off"
    }
)
```

**Errors & Solutions** (event_type: "error" or "success"):
```python
# Example: After solving a tricky bug
mcp__recall__ingest_memory(
    content="Fixed config path resolution for MCP server. Used pathlib.Path(__file__).parent.parent.parent.parent to resolve config.yaml absolute path, eliminating dependency on cwd parameter.",
    session_id="phase3_mcp_integration",
    metadata={
        "event_type": "success",
        "tags": "fix,mcp,configuration",
        "context": "Server couldn't find config.yaml when run from different directories",
        "outcome": "Works from any directory without relying on cwd"
    }
)
```

---

### Retrieval Modes - Dual Access Patterns

#### Mode 1: Semantic Search (Default)
**Use when**: Searching by meaning/relevance

```python
# Find relevant context for current work
mcp__recall__recall_memory(
    query="embedding model decisions",
    session_id="phase3_architecture",  # Optional: filter by session
    top_k=5,
    min_score=0.5  # Similarity threshold
)
# Returns: Most semantically similar chunks, ranked by score
```

#### Mode 2: Chronological Timeline
**Use when**: Need temporal sequence of events

```python
# Show Phase 3 timeline
mcp__recall__recall_memory(
    retrieval_mode="chronological",
    session_id="phase3",
    time_range="2025-10-08,2025-10-11",  # Date range
    top_k=20
)
# Returns: Events in time order (oldest to newest)
```

#### Mode 3: Hybrid (Semantic + Temporal)
**Use when**: Recent relevant events

```python
# Recent debugging attempts
mcp__recall__recall_memory(
    query="debugging MCP integration",
    retrieval_mode="hybrid",
    time_range="2025-10-10,",  # Since Oct 10 (open-ended)
    event_types="discovery,error,success",
    top_k=10
)
# Returns: Semantically relevant events from time range
```

---

### Workflow Integration Patterns

#### Pattern 1: Offload to Recall (Reduce Context)
```
1. Working on complex task → Context fills up
2. Reach good stopping point → ingest_memory() with findings
3. Clear detailed explanation from context
4. Continue working with lighter context
5. Later need those details → recall_memory() pulls them back
```

**Example:**
```python
# After completing complex debugging
mcp__recall__ingest_memory(
    content="[Detailed findings about MCP server logging issue...]",
    session_id="mcp_debugging",
    metadata={"event_type": "discovery", "tags": "mcp,logging"}
)

# Later in session when context is lighter
mcp__recall__recall_memory(
    query="MCP logging issue details",
    session_id="mcp_debugging"
)
```

#### Pattern 2: Session Continuity
```
1. Session ends with task incomplete
2. Next session starts → recall_memory(session_id="previous_task")
3. Continue from where left off
4. No need to re-explain everything
```

#### Pattern 3: Proactive Storage During Development
```
1. Make important decision → ingest immediately
2. Find bug root cause → ingest with discovery event
3. Complete milestone → ingest with milestone event
4. Context getting full → Store current state, continue fresh
```

---

### Event Metadata Structure Best Practices

**Required Fields (Auto-Added):**
- `session_id`: Organizational grouping
- `ingested_at`: ISO timestamp (UTC)

**Recommended Custom Fields:**
```python
metadata = {
    "event_type": "decision|discovery|milestone|preference|error|success",
    "tags": "topic1,topic2,topic3",  # Comma-separated for filtering
    "context": "Why this memory was created",
    "outcome": "What happened or was decided"
}
```

**Event Types:**
- `decision`: Architecture, tool selection, approach changes
- `discovery`: Findings, insights, "what we learned"
- `milestone`: Waypoint completion, phase transitions
- `preference`: User preferences, coding style learned
- `error`: Problems encountered, failure modes
- `success`: Solutions that worked, validated approaches

---

### Advanced Usage Examples

#### Example 1: Track Decision Rationale
```python
# Store the "why" behind decisions
mcp__recall__ingest_memory(
    content="Chose 2-tier fallback (Arctic → MiniLM) over 4-tier because Nomic (4.8GB) is larger than Arctic (3.5GB), making it illogical as a fallback. Simpler is better.",
    session_id="phase1_architecture",
    metadata={
        "event_type": "decision",
        "tags": "architecture,fallback,simplicity",
        "context": "Designing embedder fallback strategy",
        "outcome": "2-tier fallback validated by Zen MCP (9/10 confidence)"
    }
)

# Later retrieve the reasoning
mcp__recall__recall_memory(
    query="why 2-tier fallback instead of 4-tier",
    session_id="phase1_architecture"
)
```

#### Example 2: Debugging Timeline Reconstruction
```python
# Store each debugging step
# Step 1
mcp__recall__ingest_memory(
    content="MCP server shows connected but tools not available",
    session_id="mcp_debug_timeline",
    metadata={"event_type": "error", "tags": "mcp,tools"}
)

# Step 2
mcp__recall__ingest_memory(
    content="Found stdout contamination from sentence-transformers logging",
    session_id="mcp_debug_timeline",
    metadata={"event_type": "discovery", "tags": "mcp,logging"}
)

# Step 3
mcp__recall__ingest_memory(
    content="Fixed by redirecting all logging to stderr",
    session_id="mcp_debug_timeline",
    metadata={"event_type": "success", "tags": "mcp,fix"}
)

# Retrieve chronological timeline
mcp__recall__recall_memory(
    retrieval_mode="chronological",
    session_id="mcp_debug_timeline",
    event_types="error,discovery,success"
)
```

#### Example 3: Performance Optimization History
```python
# Track what optimizations worked
mcp__recall__ingest_memory(
    content="Semantic search achieves 17.5ms query latency (28x faster than 500ms target) by using Arctic embedder with MPS acceleration on M1 Max",
    session_id="performance_wins",
    metadata={
        "event_type": "success",
        "tags": "performance,optimization,embeddings",
        "metrics": "17.5ms_query,28x_speedup"
    }
)

# Find similar optimization opportunities
mcp__recall__recall_memory(
    query="performance optimization techniques that worked",
    session_id="performance_wins"
)
```

---

### Context Management Strategy

**Recall as External Working Memory:**

Traditional Claude Session:
```
Context Window: 200k tokens
├─ Active reasoning: 30k
├─ Code being worked on: 50k
├─ MCP tools: 60k
├─ Instructions: 15k
└─ Everything else: 45k ← COMPACTED/LOST when full
```

Recall-Enhanced Session:
```
Context Window: 200k tokens
├─ Active reasoning: 30k
├─ Code being worked on: 50k
├─ MCP tools: 60k
├─ Instructions: 15k
└─ LIGHT (45k freed) ← Offloaded to Recall, retrievable on-demand
```

**Benefits:**
- ✅ Prevent premature context compaction
- ✅ Preserve detailed decision rationale
- ✅ Enable session continuity across restarts
- ✅ Build persistent knowledge base over time

---

### Performance Considerations

**Query Performance:**
- Semantic search: ~17.5ms average (validated)
- Chronological search: ~20-30ms (no embedding needed)
- Hybrid search: ~25-40ms (embedding + filtering)

**When NOT to Use Recall:**
- Temporary calculations (use variables)
- Data that changes frequently (use working memory)
- Highly structured queries (use SQLite/JSON)

**Best Practices:**
- Store important events immediately (don't batch)
- Use descriptive session_ids for easy filtering
- Tag liberally for better discoverability
- Prefer semantic search for "what" questions
- Prefer chronological for "when" questions

## Development Phase Commands

### Phase 1: Project Setup
**Not yet implemented.** When starting development:

1. Use the AI prompt in `semantic-memory-project-starter-v1.1.markdown` (section "Detailed Prompt for AI Coding Assistant")
2. Request: "Phase 1: Generate project skeleton"
3. Reference CodeIndex repo for structural patterns: `/Users/wrk/WorkDev/MCP-Dev/claude-codeindex`

### CLI Commands
```bash
# Qdrant setup
recall setup-qdrant              # Detect or launch Qdrant via Docker

# Ingestion
recall ingest <file> --embedder bge-small-en-v1.5
recall ingest --session-id abc123 --lang python

# Retrieval
recall search "query text" --top-k 10

# Testing (Pytest)
pytest tests/                       # Full test suite
pytest tests/test_embeddings.py     # Embedding benchmarks
pytest -k "test_chunker"            # Specific component

# MCP Server
# Configured via Claude Desktop mcp.json
```

### Configuration
When implemented, edit `config.yaml`:
```yaml
# PRIMARY MODEL (default)
embedder: snowflake/arctic-embed-m  # 87% accuracy, 1024D

# 2-TIER FALLBACK (Zen validated, 9/10 confidence)
fallback:
  enabled: true
  model: all-MiniLM-L6-v2  # 78.1% accuracy, 384D (most reliable)

# USER-SELECTABLE ALTERNATIVES (manual switch, not auto-fallback)
available_models:
  - snowflake/arctic-embed-m   # 87% - default
  - nomic-embed-text-v1.5      # 86.2% - long context (8K tokens)
  - bge-small-en-v1.5          # 84.7% - balanced
  - all-MiniLM-L6-v2           # 78.1% - speed

# QDRANT CONFIGURATION
qdrant:
  host: localhost
  port: 6333
  # api_key: optional

# MULTI-COLLECTION (auto-managed by UnifiedVectorStore)
collections:
  auto_create: true
  # recall_384d, recall_768d, recall_1024d created automatically

# MONITORING
monitoring:
  alert_on_fallback: true  # Alert when Arctic fails and MiniLM activates
  log_dimension_mismatches: true
```

Override via environment variables:
```bash
export EMBEDDER_MODEL=snowflake/arctic-embed-m  # or nomic-embed-text-v1.5, etc.
export QDRANT_HOST=localhost
export FALLBACK_ENABLED=true
```

## Implementation Guidance

### Resource Dependencies
- **CodeIndex Repo:** `/Users/wrk/WorkDev/MCP-Dev/claude-codeindex` (or https://github.com/WKassebaum/codeindex)
  - Reuse chunker patterns (`chunker.py` with TreeSitter)
  - Adapt FastMCP server structure (`mcp.py`)
  - Mirror config approach (YAML + env fallbacks)

### Tech Stack (Target)
- Python 3.10+
- FastMCP (MCP server framework)
- sentence-transformers (`all-MiniLM-L6-v2`, `bge-small-en-v1.5`)
- openai (for `text-embedding-3-small`)
- qdrant-client
- TreeSitter (AST parsing)
- Click (CLI)
- Pytest (testing)

### Success Metrics (from PRD)
- Retrieval accuracy >85% across embedding models
- <500ms query latency
- <5% context token overhead per session
- Zero-code embedding model switching

## Phased Development Plan (Quality-Gated)

**CRITICAL:** Follow `QUALITY_GATED_IMPLEMENTATION_PLAN.md` for detailed waypoints

**POC Phase (2-3 days):**
- Day 0.1: Testing infrastructure setup
- Day 0.2: Unified API POC + Waypoint 1
- Exit: API design validated, CC ≤ 6

**Phase 1: Foundation (4-5 days, 6 waypoints)**
- Day 1.1: Project skeleton + config (Waypoint 2)
- Day 1.2: Embedder factory + 2-tier fallback (Waypoint 3)
- Day 1.3: Qdrant + multi-collection (Waypoint 4)
- Day 1.4: UnifiedVectorStore (Waypoint 5)
- Day 1.5: Startup validation + integration test (Waypoints 6-7)
- Exit: Coverage >80%, CC ≤ 6, all quality gates passed

**Phase 2: Ingestion & Retrieval (3-4 days, 4 waypoints)**
- Day 2.1: TreeSitter chunking (Waypoint 8)
- Day 2.2: Retrieval engine (Waypoint 9)
- Day 2.3: Concurrency safety (Waypoint 10)
- Day 2.4: MCP server + integration test (Waypoint 11)
- Exit: Latency <500ms, accuracy >85%, concurrency tests pass

**Phase 3: CLI, Migration & Benchmarks (5-6 days, 4 waypoints)**
- Day 3.1-3.2: CLI development (Waypoint 12)
- Day 3.3-3.4: Migration tool + canary strategy (Waypoints 13-14)
- Day 3.5: Benchmark suite (Waypoint 15)
- Day 3.6: Integration test + debt review
- Exit: Migration robust, benchmarks validate >85% accuracy

**Phase 4: Polish & Integration (2-3 days, 2 waypoints)**
- Day 4.1: Final integration testing (Waypoint 16)
- Day 4.2: Performance profiling (Waypoint 17)
- Day 4.3: Final quality audit
- Exit: ALL 17 waypoints passing, ready for v1.0 release

**Total Estimated:** 14-18 days (quality-first, no rush)

## Non-Goals
- Full RAG UI
- Real-time collaboration features
- Non-coding domain applications
- Distributed database architecture (v1.1 scope)

## Planning Documents (Read Before Starting)

**Architecture & Validation:**
1. **`QUALITY_GATED_IMPLEMENTATION_PLAN.md`** - **PRIMARY REFERENCE** - 17 testing waypoints, quality gates
2. **`ZEN_VALIDATION_FINAL_SYNTHESIS.md`** - Zen MCP consensus validation results
3. **`GO_FORWARD_PLAN_v1.3.1.md`** - Detailed implementation plan with Zen insights
4. **`CRITICAL_REVIEW_SUMMARY.md`** - TL;DR of 7 critical issues identified + solutions
5. **`ARCHITECTURE_REVIEW.md`** - Comprehensive architecture analysis (59 pages)
6. **`ROADMAP_UPDATES_v1.3.md`** - Updated phase breakdowns with architectural fixes

**Original Specification:**
7. **`semantic-memory-project-starter-v1.1.markdown`** - Original PRD
8. **`PRD_UPDATES_v1.2.md`** - v1.2 embedding model expansion
9. **`EXECUTIVE_SUMMARY.md`** - 5-minute project overview
10. **`PROJECT_ANALYSIS_REPORT.md`** - Complete technical analysis

**Key Decisions from Validation:**
- Multi-collection strategy (9/10 confidence from o3-mini)
- 2-tier fallback chain (9/10 confidence)
- Unified API abstraction layer (critical for UX)
- Migration tool robustness (8/10 confidence with enhancements)
- Quality-gated approach (no timeline pressure)

## External References
- Qdrant: https://qdrant.tech/documentation/
- FastMCP: https://github.com/modelcontextprotocol/fastmcp
- CodeIndex: https://github.com/WKassebaum/codeindex
- sentence-transformers: https://huggingface.co/sentence-transformers
- TreeSitter: https://tree-sitter.github.io/tree-sitter/
- Radon (complexity): https://radon.readthedocs.io/
