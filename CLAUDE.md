# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SemVecMem v1.1** - Semantic Vector Memory for Coding Agents

A long-term memory system for coding agents that addresses context window limitations using vector embeddings for fuzzy, semantic retrieval of past sessions, code snippets, and decisions. Exposed via Model Context Protocol (MCP) for low-overhead integration with AI assistants like Claude Code CLI.

**Current Status:** Project starter phase - codebase not yet implemented. The `semantic-memory-project-starter-v1.1.markdown` document contains the complete PRD and implementation guide.

**Hardware:** ✅ Validated on M1 Max with 64GB RAM - confirmed excellent fit (uses ~3% RAM)

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
```

## Key Technical Decisions (from PRD)

### Vector Database
- **Qdrant** via qdrant-client
- Collection: `semvecmem` with HNSW index (ef_construct=100, m=16)
- Auto-detect running instance at `localhost:6333` or guide Docker setup
- Metadata fields: `chunk_id`, `timestamp`, `session_id`, `lang`, `user_intent`, `embedding_model`

### Embedding Models (Configurable) ✅ EXPANDED EVALUATION

**Research-validated choices (2024 MTEB benchmarks):**

**Tier 1: Accuracy-First (Exceeds 85% Target)**
- **Default:** `snowflake/arctic-embed-m` (87% accuracy, 1024 dims, ~3.5GB)
  - Purpose-built for retrieval tasks
  - Highest accuracy, SOTA performance
  - Excellent on M1 Max with MPS (~35ms/query, 5.5% RAM)

- **Long Context:** `nomic-embed-text-v1.5` (86.2% accuracy, 768 dims, ~4.8GB)
  - Supports 8K token context (vs standard 512)
  - Great for long code blocks
  - M1 Max friendly (~41.9ms/query, 7.5% RAM)

**Tier 2: Balanced (Near Target)**
- **Proven:** `bge-small-en-v1.5` (84.7% accuracy, 384 dims, ~2.1GB)
  - Well-tested, efficient
  - Fast on M1 Max (~22.5ms/query, 3.3% RAM)

**Tier 3: Speed-Critical (Edge/Constrained)**
- **Ultra-Fast:** `all-MiniLM-L6-v2` (78.1% accuracy, 384 dims, ~1.2GB)
  - Fastest option (~14.7ms/query, 1.9% RAM)
  - Use when speed > accuracy

**Removed:** `text-embedding-3-small` (62.3% accuracy - fails requirements by 27%)

**All models run excellently on M1 Max (use <8% of 64GB RAM)**

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
# DEFAULT: Arctic-embed-m (87% accuracy, exceeds target)
embedder: snowflake/arctic-embed-m

# Intelligent fallback chain
fallback_chain:
  - nomic-embed-text-v1.5   # 86.2% - long context
  - bge-small-en-v1.5       # 84.7% - balanced
  - all-MiniLM-L6-v2        # 78.1% - speed

# Qdrant configuration
qdrant:
  host: localhost
  port: 6333
  # api_key: optional

# Context-aware selection (optional)
use_case_priority:
  accuracy: snowflake/arctic-embed-m
  long_context: nomic-embed-text-v1.5
  balanced: bge-small-en-v1.5
  speed: all-MiniLM-L6-v2
```

Override via environment variables:
```bash
export EMBEDDER_MODEL=snowflake/arctic-embed-m  # or nomic-embed-text-v1.5, etc.
export QDRANT_HOST=localhost
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

## Phased Development Plan

1. **Skeleton** - Project structure, config.yaml, docker-compose.yaml
2. **Config & Embedder** - Factory pattern supporting 4 models (Arctic, Nomic, BGE, MiniLM) with intelligent fallback
3. **Chunker** - Adapt from CodeIndex
4. **Core** - Ingest/embed/store/query with Qdrant
5. **MCP Server** - FastMCP tool handlers
6. **CLI** - Click commands including Qdrant setup
7. **Tests & Docs** - Pytest suite, embedding benchmarks, README

## Non-Goals
- Full RAG UI
- Real-time collaboration features
- Non-coding domain applications
- Distributed database architecture (v1.1 scope)

## References
- Project spec: `semantic-memory-project-starter-v1.1.markdown`
- Qdrant: https://qdrant.tech/documentation/
- FastMCP: https://github.com/modelcontextprotocol/fastmcp
- CodeIndex: https://github.com/WKassebaum/codeindex
- sentence-transformers: https://huggingface.co/sentence-transformers
