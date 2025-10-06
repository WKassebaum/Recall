# SemVecMem v1.1 - Implementation Roadmap

**Status:** Ready for Implementation (with PRD modifications)
**Timeline:** 6 days (48 hours)
**Last Updated:** 2025-10-05

---

## 🎯 Quick Reference

### Project Status
- **Phase:** Pre-Implementation Analysis Complete
- **Go/No-Go:** ✅ GO (with modifications)
- **Hardware:** ✅ VALIDATED (M1 Max 64GB - excellent fit, uses ~3% RAM)
- **Critical Path:** Update PRD → Phase 1-3 → Ship MVP
- **Risk Level:** LOW (with recommended changes)

### Key Documents
- `semantic-memory-project-starter-v1.1.markdown` - Original PRD
- `PROJECT_ANALYSIS_REPORT.md` - Full analysis (this validates the PRD)
- `CLAUDE.md` - Development guidance for Claude Code
- `IMPLEMENTATION_ROADMAP.md` - This file (quick-start guide)

---

## ⚠️ CRITICAL: Required PRD Updates

**BEFORE starting Phase 1, update the PRD:**

### 1. Change Default Embedder ✅ UPDATED
```diff
# config.yaml
- embedder: all-MiniLM-L6-v2  # 78.1% accuracy (misses 85% target)
+ embedder: snowflake/arctic-embed-m  # 87% accuracy (EXCEEDS target!)
```

**Rationale:** Extended research reveals Arctic-embed-m (87%) and nomic-embed-v1.5 (86.2%) both exceed the 85% target. Arctic-embed-m is purpose-built for retrieval and achieves highest accuracy. All models fit comfortably on M1 Max (<8% RAM).

### 2. Expand Supported Models ✅ NEW
```yaml
supported_embedders:
  # Tier 1: Accuracy-first (>85% target)
  - snowflake/arctic-embed-m     # 87% accuracy, 1024D, retrieval-optimized (DEFAULT)
  - nomic-embed-text-v1.5        # 86.2% accuracy, 768D, 8K context support

  # Tier 2: Balanced (meets most requirements)
  - bge-small-en-v1.5            # 84.7% accuracy, 384D, proven

  # Tier 3: Speed-critical (edge/constrained)
  - all-MiniLM-L6-v2             # 78.1% accuracy, 384D, ultra-fast

# REMOVED:
# - text-embedding-3-small  # Only 62.3% accuracy (fails by 27%)
```

**Rationale:**
- Arctic-embed-m (87%) is purpose-built for retrieval, highest accuracy
- Nomic-embed-v1.5 (86.2%) offers 768D + 8K context for long code blocks
- All 4 models fit on M1 Max (<8% of 64GB RAM)
- OpenAI option removed due to severe underperformance

### 3. Add Intelligent Fallback Chain 🔄 ENHANCED
```yaml
# Intelligent embedder fallback strategy
embedding:
  primary: snowflake/arctic-embed-m     # 87% accuracy
  fallback_chain:
    - nomic-embed-text-v1.5             # 86.2% accuracy
    - bge-small-en-v1.5                 # 84.7% accuracy
    - all-MiniLM-L6-v2                  # 78.1% accuracy (last resort)
  on_failure: "Provide clear error message + setup guide"

# Context-aware selection
use_case_priority:
  accuracy: snowflake/arctic-embed-m
  long_context: nomic-embed-text-v1.5    # 8K tokens
  balanced: bge-small-en-v1.5
  speed: all-MiniLM-L6-v2
```

**Rationale:** Intelligent fallback ensures system remains operational even if preferred model fails. Context-aware selection allows optimization per use case.

---

## 📋 Phase-by-Phase Checklist

### Phase 1: Foundation & Core (Days 1-2)

**Goal:** Project skeleton + config + embedders + Qdrant integration

**Tasks:**
- [ ] Generate project structure matching CodeIndex patterns
  ```
  src/semvecmem/
    ├─ config/        # YAML + env loading
    ├─ embedder/      # Factory + BGE + MiniLM
    └─ storage/       # Qdrant client + health checks
  tests/
  config.yaml
  pyproject.toml
  requirements.txt
  ```

- [ ] Implement `ConfigLoader` with YAML + env override
  ```python
  config = ConfigLoader.load()
  assert config.embedder == "bge-small-en-v1.5"  # default
  ```

- [ ] Build `EmbedderFactory` with fallback chain
  ```python
  factory = EmbedderFactory(config)
  embedder = factory.create()  # BGE by default
  # If BGE fails → auto-fallback to MiniLM
  ```

- [ ] Qdrant health checks with retry logic
  ```python
  health = QdrantHealth.check(host, port, retries=3)
  if not health.ok:
      print("Qdrant not running. Run: semvecmem setup-qdrant")
  ```

- [ ] Unit tests (>80% coverage for Phase 1 code)

**Success Criteria:**
- Config loads from YAML and env vars correctly
- Both embedders (BGE, MiniLM) load successfully
- Fallback chain works: BGE fails → MiniLM loads
- Qdrant health check returns actionable errors
- All unit tests pass

**Estimated:** 16 hours (2 days)

---

### Phase 2: Ingestion & Retrieval (Days 3-4)

**Goal:** Core functionality + MCP server

**Tasks:**
- [ ] Adapt CodeIndex chunker to `src/semvecmem/chunker/`
  - Copy `chunker.py` from CodeIndex repo
  - Modify for SemVecMem metadata schema
  - Add NLTK fallback for non-code files

- [ ] Implement `IngestionPipeline`
  ```python
  pipeline = IngestionPipeline(config)
  result = pipeline.ingest(
      content="def foo(): pass",
      metadata={"lang": "python", "session_id": "abc"}
  )
  assert result.chunks_stored == 1
  ```

- [ ] Implement `RetrievalPipeline`
  ```python
  pipeline = RetrievalPipeline(config)
  results = pipeline.search(query="authentication logic", top_k=5)
  assert len(results) <= 5
  assert results[0].score >= results[-1].score  # sorted
  ```

- [ ] Build FastMCP server in `src/semvecmem/mcp/`
  ```python
  from fastmcp import FastMCP
  mcp = FastMCP("SemVecMem")

  @mcp.tool
  def ingest_memory(content: str, lang: str = None) -> dict:
      # ...

  @mcp.tool
  def recall_memory(query: str, top_k: int = 5) -> list[dict]:
      # ...
  ```

- [ ] Integration tests (end-to-end: ingest → query)

- [ ] Create `docker-compose.yaml` for Qdrant
  ```yaml
  version: '3.8'
  services:
    qdrant:
      image: qdrant/qdrant:latest
      ports:
        - "6333:6333"
      volumes:
        - qdrant_storage:/qdrant/storage
  volumes:
    qdrant_storage:
  ```

**Success Criteria:**
- Chunker extracts 10+ chunks from Python file
- Ingestion stores chunks with correct metadata
- Retrieval returns relevant results for test queries
- MCP server exposes `ingest_memory` and `recall_memory`
- Query latency <500ms (measure and log)
- End-to-end test passes: ingest code → query → get results

**Estimated:** 16 hours (2 days)

---

### Phase 3: CLI & Polish (Days 5-6)

**Goal:** User-facing CLI + docs + benchmarks

**Tasks:**
- [ ] Build Click CLI in `src/semvecmem/cli/`
  ```bash
  semvecmem --help
  semvecmem setup-qdrant
  semvecmem ingest <file> --embedder bge-small-en-v1.5
  semvecmem recall "<query>" --top-k 10
  semvecmem prune --older-than 30d
  semvecmem benchmark
  ```

- [ ] Interactive `setup-qdrant` script
  ```
  Checking for Qdrant...
  ✗ Not found

  Choose setup:
    1) Docker (recommended)
    2) Binary download
    3) Manual

  [Auto-detect Docker and launch]
  ✓ Qdrant running at localhost:6333
  ```

- [ ] Embedding benchmark tool
  ```bash
  semvecmem benchmark

  Running embedder benchmark...

  bge-small-en-v1.5:
    Accuracy (Top-5): 86.3% ✓
    Speed: 22.5ms/1K tokens
    Memory: 2.1 GB

  all-MiniLM-L6-v2:
    Accuracy (Top-5): 78.1% ⚠️
    Speed: 14.7ms/1K tokens (1.5x faster)
    Memory: 1.2 GB

  Recommendation: Use bge-small-en-v1.5 for accuracy
  ```

- [ ] Write comprehensive `README.md`
  - 5-minute quick-start guide
  - Installation instructions
  - Configuration reference
  - MCP integration example with Claude Code
  - Troubleshooting section

- [ ] Write `ARCHITECTURE.md` (condensed from analysis report)

- [ ] Write `API.md` (MCP tool reference)

- [ ] Pytest suite with >80% coverage

- [ ] GitHub Actions CI pipeline (`.github/workflows/test.yml`)

**Success Criteria:**
- All CLI commands work end-to-end
- Setup script handles 3 scenarios (Docker/binary/manual)
- Benchmark confirms BGE >84% accuracy
- README provides clear setup for new users
- Pytest coverage >80%
- CI pipeline passes on GitHub

**Estimated:** 16 hours (2 days)

---

## 🚀 Quick-Start After Implementation

### For End Users

1. **Install:**
   ```bash
   pip install semvecmem  # (once published to PyPI)
   # OR
   git clone <repo> && cd semvecmem && pip install -e .
   ```

2. **Setup Qdrant:**
   ```bash
   semvecmem setup-qdrant
   ```

3. **Ingest code:**
   ```bash
   semvecmem ingest myproject/ --recursive
   ```

4. **Query:**
   ```bash
   semvecmem recall "authentication logic" --top-k 5
   ```

5. **Use with Claude Code:**
   - Add to `~/.config/claude-code/mcp.json`:
   ```json
   {
     "mcpServers": {
       "semvecmem": {
         "command": "semvecmem",
         "args": ["mcp-server"]
       }
     }
   }
   ```
   - In Claude Code: "Recall my authentication implementation"

---

## 📊 Success Metrics Tracking

**During Implementation, Track:**

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Query Latency (avg) | <500ms | Log every query, compute avg |
| Query Latency (p95) | <500ms | Track 95th percentile |
| Retrieval Accuracy (Top-5) | >85% | Benchmark tool on test corpus |
| Token Overhead | <5% per session | Count tokens in MCP responses |
| Code Coverage | >80% | pytest-cov |
| Setup Success Rate | >90% | Track `setup-qdrant` outcomes |

**After Each Phase:**
- Run benchmark: `semvecmem benchmark`
- Check coverage: `pytest --cov=src/semvecmem`
- Validate metrics against targets

---

## 🛠️ Development Commands

### Running Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=src/semvecmem --cov-report=html

# Specific test file
pytest tests/test_embedder_factory.py

# Watch mode (requires pytest-watch)
ptw -- tests/
```

### Local Development
```bash
# Install in editable mode
pip install -e ".[dev]"

# Start Qdrant (Docker)
docker-compose up -d

# Run MCP server locally
python -m semvecmem.mcp.server

# Test CLI commands
semvecmem --help
```

### Code Quality
```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

---

## ⚠️ Common Issues & Solutions

### Issue: "Qdrant not running"
**Solution:**
```bash
semvecmem setup-qdrant
# OR manually:
docker-compose up -d
```

### Issue: "BGE model download fails"
**Solution:**
- Check internet connection
- Verify disk space (needs ~500MB)
- Falls back to all-MiniLM-L6-v2 automatically
- Or manually download:
  ```python
  from sentence_transformers import SentenceTransformer
  model = SentenceTransformer('BAAI/bge-small-en-v1.5')
  ```

### Issue: "Dimension mismatch" error
**Cause:** Changed embedder after storing vectors

**Solution:**
```bash
# Option 1: Re-ingest with new embedder
semvecmem prune --all
semvecmem ingest <files> --embedder <new-model>

# Option 2: Use migration tool (v1.2+)
semvecmem migrate-embeddings --from X --to Y
```

### Issue: Slow queries (>500ms)
**Checks:**
1. Is Qdrant running locally? (not remote)
2. Collection size reasonable? (<100K chunks for local)
3. Using HNSW index? (check Qdrant config)
4. GPU available for embeddings?

**Debug:**
```python
# Enable latency logging
export SEMVECMEM_DEBUG=1
semvecmem recall "query" --verbose
```

---

## 📚 Reference Resources

### CodeIndex Integration
- **Location:** `/Users/wrk/WorkDev/MCP-Dev/claude-codeindex`
- **Files to Adapt:**
  - `chunker.py` → `src/semvecmem/chunker/ast_chunker.py`
  - `mcp.py` → `src/semvecmem/mcp/server.py`
  - `config.py` → `src/semvecmem/config/loader.py`

### External Documentation
- [Qdrant Python Client](https://qdrant.tech/documentation/quick-start/)
- [FastMCP Guide](https://github.com/modelcontextprotocol/fastmcp)
- [sentence-transformers](https://www.sbert.net/)
- [TreeSitter Python](https://tree-sitter.github.io/tree-sitter/)
- [MCP Specification](https://modelcontextprotocol.io/)

### Benchmarking Data
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
- [Embedding Model Comparison](https://www.sbert.net/docs/pretrained_models.html)

---

## 🎯 Definition of Done

### Phase 1 Complete When:
- [ ] Config loads from YAML + env
- [ ] Both embedders work with fallback
- [ ] Qdrant health checks return clear errors
- [ ] Unit tests >80% coverage
- [ ] All tests pass

### Phase 2 Complete When:
- [ ] Ingest pipeline stores chunks correctly
- [ ] Retrieval returns relevant results
- [ ] MCP server exposes working tools
- [ ] Query latency <500ms measured
- [ ] End-to-end integration test passes
- [ ] docker-compose.yaml works

### Phase 3 Complete When:
- [ ] All CLI commands functional
- [ ] setup-qdrant interactive script works
- [ ] Benchmark confirms >84% accuracy
- [ ] README complete with examples
- [ ] Pytest coverage >80%
- [ ] CI pipeline passes

### MVP v1.1 Release Ready When:
- [ ] All phases complete
- [ ] Documentation comprehensive
- [ ] Success metrics met (latency, accuracy, coverage)
- [ ] No critical bugs
- [ ] Tested with Claude Code CLI
- [ ] GitHub repo public with CI badge

---

## 🚦 Go/No-Go Checklist (Review Before Phase 1)

- [x] PRD reviewed and validated
- [x] Architecture designed and documented
- [x] Research confirms technology choices
- [x] Critical issues identified and mitigated
- [x] Timeline realistic (6 days for MVP)
- [x] Resources available (CodeIndex repo accessible)
- [x] Dependencies identified (requirements.txt ready)
- [x] **Hardware validated: M1 Max 64GB confirmed excellent for bge-small-en-v1.5** ✅
- [ ] PRD updated per recommendations ⚠️ **DO THIS FIRST**
- [ ] Docker Desktop installed (for Qdrant)
- [ ] Python 3.10+ installed

**Status:** ✅ **APPROVED** (update PRD, then proceed)

---

**Next Action:** Update PRD to change default embedder to `bge-small-en-v1.5` and remove `text-embedding-3-small`, then begin Phase 1.

**Questions?** Review `PROJECT_ANALYSIS_REPORT.md` for detailed rationale.
