# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SemVecMem v1.3.1** - Semantic Vector Memory for Coding Agents

A long-term memory system for coding agents that addresses context window limitations using vector embeddings for fuzzy, semantic retrieval of past sessions, code snippets, and decisions. Exposed via Model Context Protocol (MCP) for low-overhead integration with AI assistants like Claude Code CLI.

**Current Status:** Quality-gated implementation ready to begin
- ✅ Architecture validated (independent + Zen MCP consensus)
- ✅ Multi-collection strategy approved (9/10 confidence)
- ✅ Quality-gated plan with 17 testing waypoints
- 🚀 Ready for POC phase

**Hardware:** ✅ Validated on M1 Max with 64GB RAM - confirmed excellent fit (uses <8% RAM for all 4 models)

**Implementation Philosophy:** Quality-first, continuous testing, technical debt prevention

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

### Planned Component Structure
When implemented, the project will follow this structure (mirrors CodeIndex patterns):
```
src/semvecmem/
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
radon cc src/semvecmem/ -n C      # Fail if any method CC > 10
radon mi src/semvecmem/ -n B      # Maintainability Index ≥ B
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
  semvecmem_384d:   # BGE + MiniLM (384 dimensions)
  semvecmem_768d:   # Nomic (768 dimensions)
  semvecmem_1024d:  # Arctic (1024 dimensions, default)
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

### MCP Interface (Planned Tools)
- `ingest_memory` - Store code/text chunks with metadata
- `recall_memory` - Semantic search with configurable top_k
- `prune_memory` - Clean low-usage vectors
- FastMCP framework (mirrors CodeIndex implementation patterns)

## Development Phase Commands

### Phase 1: Project Setup
**Not yet implemented.** When starting development:

1. Use the AI prompt in `semantic-memory-project-starter-v1.1.markdown` (section "Detailed Prompt for AI Coding Assistant")
2. Request: "Phase 1: Generate project skeleton"
3. Reference CodeIndex repo for structural patterns: `/Users/wrk/WorkDev/MCP-Dev/claude-codeindex`

### Future Commands (Once Implemented)
```bash
# Qdrant setup
semvecmem setup-qdrant              # Detect or launch Qdrant via Docker

# Ingestion
semvecmem ingest <file> --embedder bge-small-en-v1.5
semvecmem ingest --session-id abc123 --lang python

# Retrieval
semvecmem recall "query text" --top-k 10

# Testing (Pytest)
pytest tests/                       # Full test suite
pytest tests/test_embeddings.py     # Embedding benchmarks
pytest -k "test_chunker"            # Specific component

# MCP Server
# (Exact startup command TBD - likely via mcp.json config or direct Python invocation)
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
  # semvecmem_384d, semvecmem_768d, semvecmem_1024d created automatically

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
