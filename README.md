# Recall v1.4.1 - Semantic Vector Memory for Coding Agents

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

## 🏆 Why Recall?

### Economically Sustainable Memory

Unlike "shadow agent" approaches that spawn secondary AI instances to observe your sessions, Recall uses an **O(1) cost model** - you only pay for tokens when you explicitly store or retrieve memories.

| Approach | Token Cost | Session Impact |
|----------|------------|----------------|
| **Recall (Explicit)** | O(1) - per tool call | Zero overhead during work |
| **Shadow Agent (Automatic)** | O(N) - re-reads entire context | 2-3x session cost |

**Result:** Recall is economically viable for heavy daily use. Shadow agent approaches can double or triple your token consumption.

### High Signal-to-Noise Ratio

Recall captures **outcomes, not process**:

```
❌ Automatic capture: "Tried fix A... failed. Tried fix B... failed. Tried fix C... worked."
✅ Recall explicit: "Fixed race condition in auth module by adding mutex lock"
```

When you retrieve memories later, you get actionable solutions - not debugging noise.

### Production-Ready Architecture

| Feature | Recall | Complex Alternatives |
|---------|--------|---------------------|
| **Dependencies** | Python + FastMCP + Qdrant | TypeScript + Bun + PM2 + SQLite + Chroma |
| **Client Portability** | Any MCP client (CLI, Desktop, IDEs) | Often CLI-only (hook dependencies) |
| **Stability** | Pure MCP (stable protocol) | Hook chains (version-sensitive) |
| **Maintenance** | Single Python codebase | Multi-language stack |

### Privacy by Design

You control exactly what gets stored. No automatic surveillance of your coding sessions:

- ✅ Store only what matters (decisions, discoveries, milestones)
- ✅ Skip sensitive work with `<private>` tags
- ✅ No background processes watching your context
- ✅ Full audit trail of what you've stored

### Multi-Model Safety

Recall's **multi-collection routing** prevents dimension mismatch errors when switching embedding models:

```
384d collection ← all-MiniLM-L6-v2, bge-small-en-v1.5
768d collection ← snowflake-arctic-embed-m, nomic-embed-text-v1.5
```

Switch models freely - Recall routes automatically to the correct collection.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- **Virtual environment** (REQUIRED for modern Python - see [INSTALLATION.md](INSTALLATION.md#troubleshooting) for PEP 668 details)
- Claude Code CLI or compatible MCP client
- Docker (optional, required for network mode multi-project support)

> **📖 Detailed Installation Guide:** See [INSTALLATION.md](INSTALLATION.md) for platform-specific instructions, troubleshooting, and common issues.
>
> **🤖 AI Agents:** If you're Claude or another AI assistant asked to install Recall, see the [AI Agent Installation Guide](INSTALLATION.md#ai-agent-installation-guide) for step-by-step instructions including user action prompts.

### Installation via Plugin (Recommended) ⭐

> ⚠️ **Known Issue:** Claude Code's plugin system may not automatically configure the MCP server. If you encounter "Failed to reconnect to plugin:recall:recall" after installation, see the comprehensive [Plugin Installation Troubleshooting](INSTALLATION.md#plugin-installation-troubleshooting) guide for manual configuration steps.

**Four-step installation** - works from anywhere:

```bash
# 1. Add Recall as a plugin marketplace
/plugin marketplace add WKassebaum/Recall

# 2. Install the Recall plugin
/plugin install recall@Recall

# 3. Configure storage and verify
# If automatic setup succeeds, verify with:
/mcp  # Should show: plugin:recall:recall with 3 tools

# If you see "Failed to reconnect":
# See INSTALLATION.md for manual configuration
```

**If Plugin Installation Fails:**

The plugin system may not automatically:
- Create virtual environment
- Install dependencies
- Register MCP server in `~/.claude.json`

**Manual Configuration Required:**
1. Create virtual environment and install dependencies
2. Add MCP server configuration to `~/.claude.json` with namespace `plugin:recall:recall`
3. Use absolute paths (not template variables)

**Detailed Guide:** See [INSTALLATION.md - Plugin Installation Troubleshooting](INSTALLATION.md#plugin-installation-troubleshooting) for step-by-step instructions.

---

**After Successful Installation:**

```bash
# Configure Qdrant storage mode
recall setup  # Choose embedded or network mode

# Restart Claude Code
# Cmd/Ctrl + Q, then relaunch

# Verify installation
/mcp  # Should show: plugin:recall:recall with 3 tools
```

**What you get (when working):**
- ✅ MCP server with 3 tools (ingest_memory, recall_memory, memory_stats)
- ✅ Choice of storage modes (embedded or network Docker)
- ✅ Multi-project support (network mode)
- ✅ All data stored locally (no cloud dependencies)

**First Launch Note:** On first use, sentence-transformers will automatically download the Arctic embedding model (~3.5GB) from HuggingFace to `~/.cache/huggingface/`. This takes 30-60 seconds on a good connection. Subsequent launches are instant.

---

### Installation via PyPI (Simplest)

```bash
# Create a virtual environment
python -m venv ~/recall-venv
source ~/recall-venv/bin/activate  # On Windows: ~/recall-venv\Scripts\activate

# Install from PyPI
pip install semantic-recall

# Find your Python path for MCP configuration
which python  # e.g., /Users/username/recall-venv/bin/python
```

Then add to Claude Code:
```bash
claude mcp add recall -s user -- /path/to/recall-venv/bin/python -m recall.mcp.server
```

---

### Manual Installation (From Source)

If you prefer source installation or want to contribute:

> **Note for developers:** If you plan to run Claude Code from within the Recall source directory, install the plugin globally first via the plugin method above. The source repo does not include project-level Claude settings to avoid schema compatibility issues.

```bash
# Clone repository
git clone https://github.com/WKassebaum/Recall.git
cd Recall

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install from source
pip install -e .
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

## 🔀 Multi-Project Support

**Important Decision:** Recall supports two storage modes with different capabilities:

### Mode Comparison

| Feature | Embedded (Local) | Network (Docker) |
|---------|------------------|------------------|
| **Multi-project** | ❌ ONE AT A TIME | ✅ Unlimited concurrent |
| **Multi-window** | ❌ File locking issues | ✅ Thread-safe |
| **Setup** | ✅ Zero-config | ⚠️ Requires Docker |
| **Performance** | ✅ Slightly faster | ✅ Fast enough (<20ms) |
| **Data location** | `~/.recall/qdrant/` | Docker volume |
| **Recommended for** | Single-project testing | **Production use** |

### Quick Decision Guide

**Choose Embedded Mode if:**
- ✅ You only work on ONE project at a time
- ✅ You never open multiple Claude Code windows simultaneously
- ✅ You want zero-setup simplicity

**Choose Network Mode (Docker) if:**
- ✅ You work on multiple projects concurrently
- ✅ You open multiple Claude Code windows
- ✅ You want thread-safe, scalable storage
- ✅ **Recommended for normal usage**

### Interactive Setup Wizard

Run the setup wizard to configure your preferred mode:

```bash
recall setup
```

The wizard will:
1. ✅ Detect your system (Python, Docker, existing Qdrant)
2. ✅ Explain mode limitations and benefits
3. ✅ Help you choose the right mode
4. ✅ Create Docker Qdrant instance (network mode)
5. ✅ Test connection before saving
6. ✅ Generate configuration at `~/.recall/.env`

**Reconfigure anytime:**
```bash
recall setup --reconfigure
```

### Quick Fix for Existing Users

If you're already using Recall in embedded mode and want multi-project support immediately:

**See:** [QUICK_FIX_MULTI_PROJECT.md](QUICK_FIX_MULTI_PROJECT.md) for step-by-step workaround

**TL;DR:**
1. Start Docker Qdrant: `docker run -d --name recall-qdrant -p 6333:6333 qdrant/qdrant:latest`
2. Create `~/.recall/.env` with `RECALL_QDRANT_MODE=network`
3. Restart Claude Code

### Migration Between Modes

**Safe migration script available:** Use `scripts/migrate-to-named-volumes.sh` to safely transfer data from bind mounts to named volumes without data loss. See [TEAM_ROLLOUT_GUIDE.md](TEAM_ROLLOUT_GUIDE.md) for details.

---

## 🛡️ Docker Reliability & Automated Backups (v1.4.0)

### Production-Ready Stability

Recall v1.4.0 eliminates Docker corruption issues on macOS and provides automated backup/recovery:

**✅ Docker Reliability Improvements:**
- **Named volumes** - Docker-managed storage eliminates macOS file descriptor translation issues
- **WAL tuning** - Optimized for batched writes (512MB buffer, 30s flush intervals)
- **Health checks** - Automatic corruption detection
- **Multi-project validated** - Stable with 4+ concurrent projects
- **Zero corruption** - No data loss since implementation

**✅ Automated Backup System (macOS):**
- **Every 6 hours** - Automated backups via launchd
- **Intelligent rotation** - 4 recent (24hrs), 7 daily, 4 weekly
- **Auto-cleanup** - Old backups automatically pruned
- **6-hour maximum data loss** - Down from total loss before

**✅ Auto-Recovery System:**
```bash
# One-command health check and recovery
recall recover

# Force recovery from latest backup
recall recover --force

# Recover from specific backup
recall recover --backup backups/recall-backup-20251018.tar.gz
```

**Recovery time:** 2-3 minutes (fully automated)

### Quick Setup (macOS)

**1. Install automated backups:**
```bash
./scripts/setup-auto-backup.sh
```

**2. Verify service:**
```bash
launchctl list | grep recall.backup
# Expected: -   0   com.recall.backup
```

**3. Test recovery:**
```bash
recall recover
# Should show: ✅ All health checks passed!
```

### Cross-Platform Support

- **macOS:** ✅ Fully automated (launchd)
- **Linux:** ✅ Easy (cron, 10 min setup) - See [CROSS_PLATFORM_BACKUP_GUIDE.md](CROSS_PLATFORM_BACKUP_GUIDE.md)
- **Windows:** ✅ WSL2 recommended (use Linux approach)

### Documentation

- **[DOCKER_RELIABILITY.md](DOCKER_RELIABILITY.md)** - Comprehensive troubleshooting and root cause analysis
- **[AUTOMATED_BACKUP_RECOVERY_GUIDE.md](AUTOMATED_BACKUP_RECOVERY_GUIDE.md)** - Complete user guide
- **[CROSS_PLATFORM_BACKUP_GUIDE.md](CROSS_PLATFORM_BACKUP_GUIDE.md)** - Linux/Windows setup
- **[TEAM_ROLLOUT_GUIDE.md](TEAM_ROLLOUT_GUIDE.md)** - Migration strategy (NO data wipe needed)

---

## 🧠 Memory Persistence Hooks (Auto-Save/Retrieve)

Recall includes optional Claude Code hooks that automate memory save and retrieve across sessions. When enabled:

- **SessionStart**: Injects previous session context and prompts Claude to query Recall
- **PreCompact**: Fires before context compression, prompting Claude to save important context
- **SessionEnd**: Captures session summary for the next session
- **Milestones**: Automatically logs git commits and test runs as breadcrumbs

### Quick Setup

```bash
# After installing Recall (pip install or plugin), run:
./scripts/setup-hooks.sh

# Restart Claude Code to activate
```

### How It Works

Hooks are thin coordination signals (<500ms, stdlib only). They inject instructions — Claude decides what to save using its judgment, then calls `ingest_memory()` and `recall_memory()` via MCP.

State files (`.recall-session-handoff.json`, `.recall-breadcrumbs.jsonl`, `.recall-session-state.json`) are per-project and gitignored.

### Uninstall

```bash
./scripts/setup-hooks.sh --uninstall
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

## 🎓 Claude Skills Integration (v1.4.0)

**Progressive Disclosure Teaching System** - Recall now includes Claude Skills support for enhanced discoverability and guided usage.

### What are Skills?

Skills are teaching documentation that help Claude understand when and how to use tools effectively. Instead of loading full documentation into every conversation (~500+ tokens), Skills use progressive disclosure:

- **Idle state:** ~20 tokens (metadata only)
- **When needed:** Full SKILL.md loaded on-demand
- **Additional context:** Real examples from production use

### Installed Skill

After installing Recall, you automatically get:

📁 `~/.claude/skills/recall-memory-skill/`
- `SKILL.md` - Comprehensive 400+ line usage guide
  - When to Use Recall (auto-trigger patterns)
  - Available MCP Tools documentation
  - Event Types and Search Strategies
  - Context Management workflows
  - Integration patterns
- `examples.md` - Real usage examples
  - 8 comprehensive examples (debugging timelines, decision tracking, performance optimization)
  - Anti-patterns to avoid
  - Token efficiency analysis

### Key Learning Topics

The skill teaches Claude:
- **Auto-trigger scenarios** - When to proactively use Recall (context >70%, milestones, bugs, decisions)
- **Event type selection** - Choose correct type (decision, discovery, milestone, success, error, preference)
- **Search strategies** - Semantic vs chronological vs hybrid modes
- **Context management** - When to offload details to free working memory
- **Workflow patterns** - Session continuity, debugging timelines, decision tracking

### Benefits

✅ **Better Claude understanding** - Claude knows when/how to use Recall without explicit reminders
✅ **Token efficiency** - ~97% reduction (20 tokens idle vs 500+ always-loaded)
✅ **Progressive disclosure** - Detailed docs loaded only when needed
✅ **Real examples** - Learn from actual Recall development patterns

### Manual Skill Installation

If using manual installation (not plugin), create the skill directory:

```bash
mkdir -p ~/.claude/skills/recall-memory-skill/
cp .claude-plugin/skills/* ~/.claude/skills/recall-memory-skill/
```

Claude Code will automatically discover and load the skill on next launch.

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
- Test coverage: 80.03% (target: >80%)
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
- **Dual Storage Modes** - Embedded (simple, single-project) or Network (Docker, multi-project)
- **Multi-collection strategy** - Separate collections per embedding dimension (prevents dimension mismatch errors)
- **Unified API** - Automatic routing to correct collection based on active embedder
- **2-tier fallback** - Arctic (primary) → MiniLM (fallback) for reliability
- **Hybrid architecture** - Single storage (vector DB), dual retrieval (semantic OR temporal)
- **Environment-first config** - `.env` files take precedence for flexible deployment

---

## 🔧 Configuration

### Environment Configuration (Recommended)

Recall uses `~/.recall/.env` for runtime configuration (automatically created by `recall setup`):

```env
# Qdrant Storage Mode
RECALL_QDRANT_MODE=network  # or "embedded"

# Network Mode Settings (Docker)
RECALL_QDRANT_HOST=localhost
RECALL_QDRANT_PORT=6333
# RECALL_QDRANT_API_KEY=  # Optional for Qdrant Cloud

# Embedded Mode Settings
# RECALL_QDRANT_PATH=~/.recall/qdrant/

# Embedder Settings
RECALL_EMBEDDER_MODEL=Snowflake/snowflake-arctic-embed-m
RECALL_FALLBACK_ENABLED=true
RECALL_FALLBACK_MODEL=all-MiniLM-L6-v2
```

**Reconfigure:** Run `recall setup --reconfigure` to update settings interactively.

**Manual editing:** Edit `~/.recall/.env` directly, then restart Claude Code.

---

### Project Configuration (config.yaml)

For advanced customization, edit `config.yaml`:

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

**Note:** Environment variables in `~/.recall/.env` take precedence over `config.yaml`.

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

### v1.4.1 (Current Release) ✅
**Focus: Test Quality & PyPI Publishing**

1. ✅ **Test Coverage Improvements**
   - Expanded test suite from 54.77% to 80.03% coverage
   - 236 total tests covering all core modules
   - CLI modules fully tested (cleanup, doctor, recover, setup)
   - Core modules tested (store, embedders, backends)
   - Integration tests stabilized with proper database isolation

2. ✅ **PyPI Package Preparation**
   - Package builds verified (wheel + sdist)
   - Version synchronization across all files
   - Ready for PyPI publishing

### v1.5.0 (Next Release)
**Focus: Context Management & User Experience**

1. **Context Size Monitoring & Alerts** ⭐ *High Priority*
   - Real-time context window usage tracking
   - Smart alerts when context reaches 70%+ capacity
   - Automatic suggestions for memories to offload
   - Integration with Claude Code status bar

3. **Memory Importance Scoring**
   - Automatic importance calculation based on access patterns
   - User-adjustable importance ratings
   - Priority-based retrieval ranking
   - Intelligent memory pruning suggestions

4. **Cross-Project Memory Sharing**
   - Share memories across multiple projects
   - Global vs project-scoped memory management
   - Shared decision/preference memory pools

5. **Smart Mode Selection**
   - Automatic mode detection (semantic vs chronological vs hybrid)
   - Query pattern analysis for optimal retrieval
   - User preference learning

6. **Memory Export/Import**
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

**Version:** v1.4.1 | **Status:** Production-ready | **Last Updated:** 2025-12-07
