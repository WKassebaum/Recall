# Recall v1.3.3 - Semantic Vector Memory for Coding Agents

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
- Claude Code CLI or compatible MCP client

### Installation via Plugin (Recommended) ⭐

**Two-step installation** - works from anywhere:

```bash
# 1. Add Recall as a plugin marketplace
/plugin marketplace add WKassebaum/Recall

# 2. Install the Recall plugin
/plugin install recall@Recall

# 3. Verify installation
/recall-setup
```

**Note:** While the repository includes `.claude/settings.json` for automatic installation when trusted, the Claude Code trust mechanism can be inconsistent. Manual installation above is more reliable and works regardless of repository trust status.

---

**What you get with either option:**
- ✅ Automatic MCP server configuration
- ✅ Helpful slash commands: `/recall-store`, `/recall-search`, `/recall-timeline`, `/recall-stats`, `/recall-setup`
- ✅ Zero-setup embedded Qdrant
- ✅ All data stored locally at `~/.recall/qdrant/`

**First Launch Note:** On first use, sentence-transformers will automatically download the Arctic embedding model (~3.5GB) from HuggingFace to `~/.cache/huggingface/`. This takes 30-60 seconds on a good connection. Subsequent launches are instant.

---

### Manual Installation (Alternative)

If you prefer manual setup or want to contribute:

```bash
# Clone repository
git clone https://github.com/WKassebaum/Recall.git
cd Recall

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**First Launch Note:** On first use, sentence-transformers will automatically download the Arctic embedding model (~3.5GB) from HuggingFace to `~/.cache/huggingface/`. This takes 30-60 seconds on a good connection. Subsequent launches are instant.

**Optional - Pre-download model to avoid delays:**
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('Snowflake/snowflake-arctic-embed-m')"
```

### MCP Server Setup (Manual)

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
- `snowflake/arctic-embed-m` - 87% accuracy, 768D, ~3.5GB
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
  ├─ recall_384d (384-dimension: all-MiniLM-L6-v2, bge-small-en-v1.5)
  └─ recall_768d (768-dimension: snowflake-arctic-embed-m, nomic-embed-text-v1.5)
```

**Key Design Decisions:**
- **Embedded Qdrant** - Zero-setup vector database stored at `~/.recall/qdrant/` (no Docker required)
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
  # recall_384d (384D models), recall_768d (768D models) created automatically

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

### v1.4.0 (Next Release)
**Focus: Context Management & User Experience**

1. **Context Size Monitoring & Alerts** ⭐ *Highest Priority*
   - Real-time context window usage tracking
   - Smart alerts when context reaches 70%+ capacity
   - Automatic suggestions for memories to offload
   - Integration with Claude Code status bar

2. **Smart Mode Selection**
   - Automatic mode detection (semantic vs chronological vs hybrid)
   - Query pattern analysis for optimal retrieval
   - User preference learning

3. **Memory Importance Scoring**
   - Automatic importance calculation based on access patterns
   - User-adjustable importance ratings
   - Priority-based retrieval ranking
   - Intelligent memory pruning suggestions

4. **Cross-Project Memory Sharing**
   - Share memories across multiple projects
   - Global vs project-scoped memory management
   - Shared decision/preference memory pools

5. **Memory Export/Import**
   - JSON/YAML export formats
   - Backup and restore functionality
   - Team knowledge sharing capabilities
   - Migration between instances

### v1.5.0 (Future)
**Focus: Automation & Intelligence**

1. **Auto-Ingestion Hooks**
   - Automatic memory capture at key events
   - Git commit integration (capture commit context)
   - Test failure auto-logging
   - Configurable trigger patterns

2. **Smart Suggestions**
   - Proactive memory recommendations during coding
   - "You worked on similar code last week" notifications
   - Related decision surfacing
   - Pattern-based insight generation

3. **Natural Language Queries**
   - Conversational query interface
   - Query intent understanding
   - Multi-step query refinement

4. **Performance Dashboard**
   - Real-time system metrics visualization
   - Query latency trends
   - Storage usage analytics
   - Retrieval accuracy reporting

5. **Session Recap** (formerly "Summarization")
   - Conversational timeline queries: "What did we do last week?"
   - Decision history: "When did we move to version x?"
   - Rationale retrieval: "Why did we switch to Apache 2.0?"
   - Intelligent event grouping and presentation
   - No data compression - full context preserved

### v2.0+ (Long-term Vision)
**Focus: Enterprise & Scale**

- Multi-user support with permissions
- Distributed Qdrant deployment
- Advanced query DSL for power users
- Memory analytics and insights
- API for third-party integrations

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

**Version:** v1.3.3 | **Status:** Production-ready | **Last Updated:** 2025-10-11
