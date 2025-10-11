# Recall v1.3.2 - Semantic Vector Memory for Coding Agents

[![Status](https://img.shields.io/badge/status-production--ready-brightgreen)](https://github.com/WKassebaum/Recall)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-compatible-orange)](https://modelcontextprotocol.io)

> **External working memory for AI coding assistants**

Recall is a long-term semantic memory system that addresses context window limitations in AI coding assistants like Claude Code. It provides dual-mode retrieval (semantic + episodic) through vector embeddings, enabling persistent memory across sessions without cloud dependencies.

---

## 🎯 Why Recall?

**The Problem:** AI coding assistants have limited context windows (typically 200k tokens). Important decisions, discoveries, and technical details get lost when context fills up or sessions restart.

**The Solution:** Recall acts as **external working memory** - store important events immediately, retrieve them on-demand by meaning OR time, and maintain continuity across sessions.

### Key Benefits

✅ **Session Continuity** - Resume work after restart without re-explaining context
✅ **Context Pressure Relief** - Offload details to Recall, keep active reasoning lightweight
✅ **Timeline Reconstruction** - Query "What happened on October 10th?" chronologically
✅ **Decision Consistency** - Reference past architectural decisions for consistency
✅ **Zero Cloud Dependencies** - Fully local, no API keys required

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Docker Desktop (for Qdrant vector database)
- Claude Code CLI or compatible MCP client

### Installation

```bash
# Clone repository
git clone https://github.com/WKassebaum/Recall.git
cd Recall

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start Qdrant (vector database)
docker run -d -p 6333:6333 qdrant/qdrant
```

### MCP Server Setup

Add Recall to your Claude Code configuration:

```bash
claude mcp add-json --scope user recall '{
  "command": "/path/to/Recall/venv/bin/python",
  "args": ["-m", "recall.mcp.server"],
  "env": {
    "PYTHONPATH": "/path/to/Recall/src"
  }
}'
```

**Restart Claude Code** to load the Recall MCP server.

### Verify Installation

```bash
# In Claude Code, use the Recall tools
mcp__recall__memory_stats()
# Should show: Embedder: snowflake-arctic-embed-m, Collection: recall_768d
```

---

## 💡 Usage

### Storing Memories

Store important events with structured metadata:

```python
mcp__recall__ingest_memory(
    content="Selected Arctic embedder after benchmark showing 93.3% accuracy",
    session_id="architecture_decisions",
    metadata={
        "event_type": "decision",
        "tags": "architecture,embeddings,performance",
        "context": "Comparing 4 embedding models",
        "outcome": "Arctic selected as primary"
    }
)
```

**Event Types:** `decision`, `discovery`, `milestone`, `preference`, `error`, `success`

### Retrieving Memories

**Semantic Search (by meaning):**
```python
mcp__recall__recall_memory(
    query="embedding model decisions",
    top_k=5,
    session_id="architecture_decisions"
)
# Returns: Most semantically relevant memories
```

**Chronological Timeline (by time):**
```python
mcp__recall__recall_memory(
    retrieval_mode="chronological",
    session_id="phase3",
    time_range="2025-10-08,2025-10-11"
)
# Returns: Memories in time order (oldest → newest)
```

**Hybrid (semantic + temporal + event filters):**
```python
mcp__recall__recall_memory(
    query="debugging attempts",
    retrieval_mode="hybrid",
    time_range="2025-10-10,",  # Since Oct 10
    event_types="discovery,error,success",
    top_k=10
)
# Returns: Relevant debugging events from time range
```

---

## 🎨 Features

### Dual-Mode Memory System (v1.3.2)

**Semantic Mode** - Search by meaning using vector similarity
- Query: "What architecture decisions did we make?"
- Result: Top matches ranked by relevance score

**Chronological Mode** - Search by time range and filters
- Query: "Show me Phase 3 timeline"
- Result: Events in time order (oldest to newest)

**Hybrid Mode** - Combine semantic + temporal + event filtering
- Query: "Recent MCP debugging discoveries"
- Result: Semantically relevant events within time range

### Event-Based Structure

Organize memories by type for targeted retrieval:

| Event Type | Use Case | Example |
|------------|----------|---------|
| `decision` | Architecture, tool selection | "Chose multi-collection strategy for dimension isolation" |
| `discovery` | Bug findings, insights | "Found stdout contamination corrupting JSON-RPC" |
| `milestone` | Waypoint completions | "Completed Phase 3 with 91.94% test coverage" |
| `preference` | User patterns, coding style | "User prefers async/await over callbacks" |
| `error` | Problems encountered | "Migration failed: dimension mismatch" |
| `success` | Solutions that worked | "Fixed timezone bug with datetime.max.replace()" |

### High-Performance Retrieval

- **Semantic search:** ~17.5ms average (28x faster than 500ms target)
- **Chronological search:** ~20-30ms (no embedding generation)
- **Hybrid search:** ~25-40ms (embedding + filtering)

### Embedding Models

**Primary (default):**
- `snowflake/arctic-embed-m` - 87% accuracy, 1024D, ~3.5GB
  - Purpose-built for retrieval tasks
  - SOTA performance, excellent on M1 Max (~35ms/query)

**Fallback:**
- `all-MiniLM-L6-v2` - 78.1% accuracy, 384D, ~1.2GB
  - Smallest, most reliable fallback (~14.7ms/query)
  - Auto-activates if Arctic fails to load

**User-selectable (via config.yaml):**
- `nomic-embed-text-v1.5` - 86.2% accuracy, 768D, supports 8K token context
- `bge-small-en-v1.5` - 84.7% accuracy, 384D, balanced performance

All models run excellently on M1 Max (use <8% of 64GB RAM).

---

## 📊 Production Quality

### Validation Status (v1.3.2)

✅ **All Core Features Validated**
- Event metadata storage ✅
- Semantic mode ✅
- Chronological mode ✅
- Event type filtering ✅
- Hybrid mode ✅
- Time range filtering ✅

✅ **Quality Gates Passed**
- Test coverage: 91.94% (target: >80%)
- Cyclomatic complexity: ≤8 (target: ≤10)
- Type safety: mypy strict passing
- Code quality: ruff passing
- Zero breaking changes

✅ **Performance Validated**
- Query latency: <500ms target met (17.5ms average)
- Memory usage: <8GB on M1 Max
- Throughput: 32.4 chunks/sec

### Testing

Comprehensive test suite with 17 quality waypoints:

```bash
# Run full test suite
pytest tests/

# Run with coverage
pytest --cov=src/recall --cov-report=html tests/

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/benchmark/
```

---

## 📚 Documentation

### User Guides
- **[CLAUDE.md](CLAUDE.md)** - Comprehensive usage guide for Claude Code (350+ lines)
  - Auto-trigger patterns
  - Event metadata best practices
  - Workflow integration patterns
  - Context management strategy

### Developer Documentation
- **[docs/architecture/](docs/architecture/)** - Architecture and technical analysis
- **[docs/development/](docs/development/)** - Development plans, testing, quality gates
- **[docs/planning/](docs/planning/)** - PRD, executive summaries, Zen validation
- **[docs/validation/](docs/validation/)** - Test reports and validation results

### Release Information
- **[docs/releases/RELEASE_NOTES_v1.3.2.md](docs/releases/RELEASE_NOTES_v1.3.2.md)** - v1.3.2 feature overview
- **[docs/validation/VALIDATION_REPORT_v1.3.2.md](docs/validation/VALIDATION_REPORT_v1.3.2.md)** - Comprehensive validation report

---

## 🏗️ Architecture

```
MCP Client (Claude Code CLI)
  ↓ (tool calls via MCP)
MCP Server (FastMCP)
  ↓
Core Engine
  ├─ Chunker (TreeSitter AST parser for 39+ languages)
  ├─ Embedder Factory (Arctic with MiniLM fallback)
  └─ UnifiedVectorStore
       ↓
Qdrant Vector Database
  ├─ recall_384d (384-dimension collection)
  ├─ recall_768d (768-dimension collection)
  └─ recall_1024d (1024-dimension collection)
```

**Key Design Decisions:**
- **Multi-collection strategy** - Separate collections per embedding dimension (prevents dimension mismatch errors)
- **Unified API** - Automatic routing to correct collection based on active embedder
- **2-tier fallback** - Arctic (primary) → MiniLM (fallback) for reliability
- **Hybrid architecture** - Single storage (vector DB), dual retrieval (semantic OR temporal)

---

## 🔧 Configuration

Edit `config.yaml` to customize:

```yaml
# PRIMARY MODEL (default)
embedder: snowflake/arctic-embed-m

# 2-TIER FALLBACK
fallback:
  enabled: true
  model: all-MiniLM-L6-v2

# QDRANT CONFIGURATION
qdrant:
  host: localhost
  port: 6333
  # api_key: optional

# MULTI-COLLECTION (auto-managed)
collections:
  auto_create: true
  # recall_384d, recall_768d, recall_1024d created automatically

# MONITORING
monitoring:
  alert_on_fallback: true
  log_dimension_mismatches: true
```

Override via environment variables:
```bash
export EMBEDDER_MODEL=snowflake/arctic-embed-m
export QDRANT_HOST=localhost
export FALLBACK_ENABLED=true
```

---

## 🤝 Contributing

We welcome contributions! Please see:
- [Development Setup](docs/development/)
- [Quality Gates](docs/development/QUALITY_GATES.md)
- [Architecture Overview](docs/architecture/ARCHITECTURE_REVIEW.md)

### Development Workflow

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run quality checks
./scripts/quality_check.sh

# Run tests with coverage
pytest --cov=src/recall --cov-fail-under=80 tests/

# Check cyclomatic complexity
radon cc src/recall/ -n C -s

# Type checking
mypy src/recall --strict
```

---

## 🗺️ Roadmap

### v1.4.0 (Planned)
- Automatic summarization of old memories
- Smart mode selection based on query patterns
- Memory clustering by topic
- Context size monitoring with offload alerts
- Performance profiling dashboard

### v1.5.0 (Future)
- Multi-user support
- Distributed Qdrant setup
- Advanced query DSL
- Memory importance scoring
- Cross-project memory sharing

---

## 📄 License

Apache 2.0

---

## 🙏 Acknowledgments

- **CodeIndex** - AST chunking patterns and TreeSitter integration
- **Qdrant** - High-performance vector database
- **FastMCP** - MCP server framework
- **Snowflake, Nomic AI, BAAI** - Embedding models
- **Claude Code** - Dogfooding and validation

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/WKassebaum/Recall/issues)
- **Documentation:** [docs/](docs/)
- **Discussions:** [GitHub Discussions](https://github.com/WKassebaum/Recall/discussions)

---

**Version:** v1.3.2 | **Status:** Production-ready | **Last Updated:** 2025-10-11
