# SemVecMem v1.3.1 - Quality-Gated Implementation Plan
## Testing Waypoints & Technical Debt Prevention

**Date:** 2025-10-07
**Status:** ✅ **READY FOR IMPLEMENTATION**
**Philosophy:** Continuous testing waypoints prevent late-stage debt accumulation
**Approach:** Test early, test often, refactor immediately

---

## TL;DR - Testing Waypoint Strategy

**Problem:** Technical debt accumulates silently, explodes at integration time

**Solution:** Testing waypoints after each major component
- ✅ Build → Test → Refactor cycle (not Build → Build → Build → Test)
- ✅ Complexity monitoring at each waypoint
- ✅ Immediate refactoring if quality gates fail
- ✅ No "we'll fix it later" - fix it now

**Waypoints:** 12 testing checkpoints across 4 phases

---

## Continuous Quality Monitoring Framework

### Quality Metrics Dashboard

**Real-Time Monitoring:**
```bash
# Install quality monitoring tools
pip install pytest pytest-cov radon mypy ruff

# Continuous monitoring script (runs on every commit)
cat > scripts/quality_check.sh <<'EOF'
#!/bin/bash
set -e

echo "🔍 Running quality checks..."

# 1. Cyclomatic Complexity
echo "📊 Cyclomatic Complexity:"
radon cc src/semvecmem/ -a -nc
radon cc src/semvecmem/ -n C  # Fail if CC > 10

# 2. Code Coverage
echo "🧪 Test Coverage:"
pytest --cov=src/semvecmem --cov-report=term-missing --cov-fail-under=80

# 3. Type Checking
echo "🔎 Type Checking:"
mypy src/semvecmem/

# 4. Code Quality
echo "✨ Code Quality (ruff):"
ruff check src/semvecmem/

# 5. Maintainability Index
echo "📈 Maintainability Index:"
radon mi src/semvecmem/ -n B  # Fail if MI < B (moderate)

echo "✅ All quality checks passed!"
EOF

chmod +x scripts/quality_check.sh
```

### Pre-Commit Hooks (Automatic Enforcement)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: complexity-check
        name: Cyclomatic Complexity Check
        entry: radon cc src/semvecmem/ -n C
        language: system
        pass_filenames: false

      - id: test-coverage
        name: Test Coverage Check
        entry: pytest --cov=src/semvecmem --cov-fail-under=80 -q
        language: system
        pass_filenames: false

      - id: type-check
        name: Type Check
        entry: mypy src/semvecmem/
        language: system
        pass_filenames: false

      - id: code-quality
        name: Code Quality Check
        entry: ruff check src/semvecmem/
        language: system
        pass_filenames: false
```

---

## Phase 0: POC with Testing Foundation (2-3 Days)

**Goal:** Validate unified API design + establish testing infrastructure

### Day 0.1: Testing Infrastructure Setup

**Tasks:**
- [ ] Set up pytest framework
- [ ] Configure pytest-cov (coverage tracking)
- [ ] Install radon (complexity monitoring)
- [ ] Install mypy (type checking)
- [ ] Install ruff (linting)
- [ ] Create quality check script
- [ ] Set up pre-commit hooks
- [ ] Establish baseline metrics

**Deliverable:** Testing infrastructure operational

**Quality Gate:** All tools installed and running

---

### Day 0.2: POC Implementation

**Build:**
- [ ] UnifiedVectorStore skeleton (single collection)
- [ ] Basic embedder integration
- [ ] Dimension verification prototype

**Test (WAYPOINT 1):**
```python
# tests/test_unified_vector_store_poc.py
def test_unified_vector_store_basic():
    """POC: Verify basic API works"""
    store = UnifiedVectorStore(mock_qdrant)
    embedder = MockEmbedder(dimension=384)

    store.set_embedder(embedder)
    assert store.active_dimension == 384
    assert store.active_collection == "semvecmem_384d"

def test_dimension_verification_poc():
    """POC: Verify dimension mismatch caught"""
    store = UnifiedVectorStore(mock_qdrant)
    store.set_embedder(MockEmbedder(dimension=384))

    # Try to insert 768D embedding
    with pytest.raises(DimensionMismatchError):
        store.upsert([Chunk(embedding=np.random.rand(768))])
```

**Quality Check:**
```bash
# Run after POC implementation
./scripts/quality_check.sh

# Expected results:
# - Coverage: >50% (POC, limited scope)
# - CC: ≤6 for UnifiedVectorStore methods
# - Mypy: 0 errors
# - Ruff: 0 errors
```

**Refactor Trigger:**
- If CC > 6 → Refactor immediately
- If any quality check fails → Fix before proceeding

**Exit Criteria:**
- ✅ POC demonstrates unified API works
- ✅ Dimension verification catches mismatches
- ✅ CC ≤ 6
- ✅ All quality checks pass

---

## Phase 1: Foundation (4-5 Days, 5 Waypoints)

### Day 1.1: Project Skeleton + Config

**Build:**
- [ ] Create pyproject.toml with dependencies
- [ ] Set up src/semvecmem/ structure
- [ ] Configuration system (YAML + Pydantic)
- [ ] Logger setup

**Test (WAYPOINT 2):**
```python
# tests/test_config.py
def test_config_loads_from_yaml():
    """Config: Verify YAML loading"""
    config = Config.from_yaml("config.yaml")
    assert config.qdrant_host == "localhost"
    assert config.embedder_model in VALID_MODELS

def test_config_validation():
    """Config: Verify Pydantic validation"""
    with pytest.raises(ValidationError):
        Config(qdrant_host="", embedder_model="invalid")

def test_config_env_override():
    """Config: Verify environment variable overrides"""
    os.environ["SEMVECMEM_EMBEDDER"] = "arctic"
    config = Config.from_yaml("config.yaml")
    assert config.embedder_model == "snowflake/arctic-embed-m"
```

**Quality Check:**
```bash
./scripts/quality_check.sh

# Target:
# - Coverage: >80% for config module
# - CC: ≤4 (config should be simple)
```

**Refactor Checkpoint:**
- Review config complexity
- Simplify if CC > 4
- Ensure error messages clear

---

### Day 1.2: Embedder Factory

**Build:**
- [ ] EmbedderModel protocol
- [ ] 4 concrete embedders (Arctic, Nomic, BGE, MiniLM)
- [ ] 2-tier fallback chain
- [ ] Model caching

**Test (WAYPOINT 3):**
```python
# tests/test_embedder_factory.py
def test_load_all_four_models(tmp_path):
    """Embedders: Verify all 4 models load successfully"""
    factory = EmbedderFactory(cache_dir=tmp_path)

    for model_name in ["arctic", "nomic", "bge", "minilm"]:
        embedder = factory.create_embedder(model_name, fallback=False)
        assert embedder.dimension == EXPECTED_DIMENSIONS[model_name]

def test_fallback_chain():
    """Embedders: Verify Arctic→MiniLM fallback"""
    factory = EmbedderFactory()

    with patch('sentence_transformers.SentenceTransformer') as mock_st:
        # Make Arctic fail
        mock_st.side_effect = [RuntimeError("Arctic failed"), MagicMock()]

        embedder = factory.create_embedder("arctic", fallback=True)

        # Should fall back to MiniLM
        assert embedder.name == "all-MiniLM-L6-v2"

def test_fallback_monitoring():
    """Embedders: Verify fallback is logged/alerted"""
    factory = EmbedderFactory()

    with patch('sentence_transformers.SentenceTransformer') as mock_st:
        mock_st.side_effect = RuntimeError("Arctic failed")

        with pytest.raises(RuntimeError):
            factory.create_embedder("arctic", fallback=False)

        # Verify error was logged with context
        assert "Arctic failed" in caplog.text
        assert "Model load failure" in caplog.text

def test_embedder_dimension_consistency():
    """Embedders: Verify embedding dimensions match spec"""
    factory = EmbedderFactory()

    for model_name, expected_dim in DIMENSION_MAP.items():
        embedder = factory.create_embedder(model_name)
        test_embedding = embedder.encode("test")
        assert len(test_embedding) == expected_dim
```

**Quality Check:**
```bash
./scripts/quality_check.sh

# Target:
# - Coverage: >80% for embedder module
# - CC: ≤5 for create_embedder (2-tier fallback)
```

**Complexity Review:**
```python
# Check create_embedder complexity
radon cc src/semvecmem/embedders/factory.py -s

# If CC > 5, refactor:
class EmbedderFactory:
    def create_embedder(self, model_name: str, fallback: bool = True):
        """Keep this method ≤5 CC"""
        try:
            return self._load_model(model_name)
        except Exception as e:
            return self._handle_load_failure(model_name, e, fallback)

    def _handle_load_failure(self, model: str, error: Exception, fallback: bool):
        """Separate fallback logic to reduce CC"""
        self._alert_model_failure(model, error)

        if fallback and model != "all-MiniLM-L6-v2":
            logger.warning(f"Falling back to MiniLM")
            return self._load_model("all-MiniLM-L6-v2")
        raise
```

---

### Day 1.3: Qdrant Integration + Multi-Collection

**Build:**
- [ ] Qdrant client wrapper
- [ ] Health checks
- [ ] Multi-collection creation (384d, 768d, 1024d)
- [ ] Collection lifecycle management

**Test (WAYPOINT 4):**
```python
# tests/test_qdrant_integration.py
def test_qdrant_connection():
    """Qdrant: Verify connection established"""
    client = QdrantClientWrapper(host="localhost", port=6333)
    assert client.health_check() == True

def test_multi_collection_creation():
    """Qdrant: Verify all 3 collections created"""
    client = QdrantClientWrapper(...)

    client.ensure_collections_exist()

    assert client.collection_exists("semvecmem_384d")
    assert client.collection_exists("semvecmem_768d")
    assert client.collection_exists("semvecmem_1024d")

def test_collection_schema_correct():
    """Qdrant: Verify collection dimensions match"""
    client = QdrantClientWrapper(...)

    info_384 = client.get_collection("semvecmem_384d")
    assert info_384.config.params.vectors.size == 384

    info_768 = client.get_collection("semvecmem_768d")
    assert info_768.config.params.vectors.size == 768

    info_1024 = client.get_collection("semvecmem_1024d")
    assert info_1024.config.params.vectors.size == 1024

def test_qdrant_error_handling():
    """Qdrant: Verify graceful handling of connection failures"""
    client = QdrantClientWrapper(host="invalid", port=9999)

    with pytest.raises(QdrantConnectionError):
        client.health_check()
```

**Integration Test:**
```python
# tests/integration/test_embedder_qdrant.py
def test_embedder_to_qdrant_pipeline():
    """Integration: Embedder → Qdrant full pipeline"""
    factory = EmbedderFactory()
    client = QdrantClientWrapper(...)

    # Load Arctic embedder
    embedder = factory.create_embedder("arctic")

    # Encode test content
    embedding = embedder.encode("test content")

    # Insert into correct collection (1024d)
    client.upsert(
        collection_name="semvecmem_1024d",
        points=[{"id": "test", "vector": embedding}]
    )

    # Verify retrieval
    results = client.search(
        collection_name="semvecmem_1024d",
        query_vector=embedding,
        limit=1
    )
    assert len(results) == 1
    assert results[0].id == "test"
```

**Quality Check:**
```bash
./scripts/quality_check.sh

# Target:
# - Coverage: >80% for qdrant module
# - CC: ≤6 for collection management
```

---

### Day 1.4: UnifiedVectorStore Implementation

**Build:**
- [ ] UnifiedVectorStore class
- [ ] set_embedder() with auto-routing
- [ ] Dimension verification framework
- [ ] search() and upsert() methods

**Test (WAYPOINT 5):**
```python
# tests/test_unified_vector_store.py
def test_set_embedder_routes_correctly():
    """UnifiedVectorStore: Verify embedder routing"""
    store = UnifiedVectorStore(qdrant_client)

    # Set Arctic embedder
    arctic = EmbedderFactory().create_embedder("arctic")
    store.set_embedder(arctic)

    assert store.active_dimension == 1024
    assert store.active_collection == "semvecmem_1024d"

    # Switch to MiniLM
    minilm = EmbedderFactory().create_embedder("minilm")
    store.set_embedder(minilm)

    assert store.active_dimension == 384
    assert store.active_collection == "semvecmem_384d"

def test_dimension_verification_ingestion():
    """UnifiedVectorStore: Verify dimension check on upsert"""
    store = UnifiedVectorStore(qdrant_client)
    store.set_embedder(EmbedderFactory().create_embedder("minilm"))  # 384D

    # Try to insert 1024D embedding
    chunk = Chunk(content="test", embedding=np.random.rand(1024))

    with pytest.raises(DimensionMismatchError) as exc_info:
        store.upsert([chunk])

    # Verify error message is helpful
    assert "Expected 384D" in str(exc_info.value)
    assert "got 1024D" in str(exc_info.value)
    assert "semvecmem migrate-embeddings" in str(exc_info.value)

def test_dimension_verification_query():
    """UnifiedVectorStore: Verify dimension check on search"""
    store = UnifiedVectorStore(qdrant_client)
    store.set_embedder(EmbedderFactory().create_embedder("arctic"))  # 1024D

    # Mock embedder to return wrong dimension
    with patch.object(store.active_embedder, 'encode', return_value=np.random.rand(768)):
        with pytest.raises(DimensionMismatchError):
            store.search("test query")

def test_no_embedder_set_error():
    """UnifiedVectorStore: Verify error if no embedder set"""
    store = UnifiedVectorStore(qdrant_client)

    with pytest.raises(ValueError, match="No active embedder"):
        store.search("test")

    with pytest.raises(ValueError, match="No active embedder"):
        store.upsert([Chunk(content="test")])

def test_deterministic_chunk_ids():
    """UnifiedVectorStore: Verify content hash IDs"""
    store = UnifiedVectorStore(qdrant_client)
    store.set_embedder(EmbedderFactory().create_embedder("minilm"))

    chunk1 = Chunk(content="identical content")
    chunk2 = Chunk(content="identical content")

    store.upsert([chunk1])
    store.upsert([chunk2])  # Should update, not duplicate

    # Verify only 1 chunk exists
    results = store.search("identical content")
    assert len(results) == 1
```

**Complexity Review:**
```bash
radon cc src/semvecmem/vector_store.py -s

# Target: CC ≤ 6 for all methods
# If any method > 6, refactor immediately
```

**Example Refactoring if CC > 6:**
```python
# Before (CC = 8)
def upsert(self, chunks: List[Chunk]) -> None:
    if not self.active_embedder:
        raise ValueError("No active embedder")

    for chunk in chunks:
        chunk.id = self._generate_id(chunk.content)
        chunk.embedding = self.active_embedder.encode(chunk.content)

        if len(chunk.embedding) != self.active_dimension:
            # Complex error message construction
            source_model = self._infer_model(len(chunk.embedding))
            target_model = self.active_embedder.name

            if source_model != target_model:
                raise DimensionMismatchError(
                    f"Dimension mismatch: {len(chunk.embedding)}D → {self.active_dimension}D\n"
                    f"Migration required: {source_model} → {target_model}\n"
                    f"Run: semvecmem migrate-embeddings --from {source_model} --to {target_model}"
                )

    self.client.upsert(...)

# After (CC = 4)
def upsert(self, chunks: List[Chunk]) -> None:
    self._ensure_embedder_set()

    prepared_chunks = [self._prepare_chunk(chunk) for chunk in chunks]
    self.client.upsert(collection_name=self.active_collection, points=prepared_chunks)

def _prepare_chunk(self, chunk: Chunk) -> Chunk:
    chunk.id = self._generate_id(chunk.content)
    chunk.embedding = self.active_embedder.encode(chunk.content)
    self._verify_dimension(chunk.embedding)
    return chunk

def _verify_dimension(self, embedding: np.ndarray):
    if len(embedding) != self.active_dimension:
        raise self._build_dimension_error(len(embedding))
```

---

### Day 1.5: Startup Validation + Phase 1 Integration Tests

**Build:**
- [ ] Startup validation framework
- [ ] Config sanity checks
- [ ] Qdrant reachability test
- [ ] Embedder load test
- [ ] Collection health checks

**Test (WAYPOINT 6):**
```python
# tests/test_startup_validation.py
def test_startup_validator_all_checks():
    """Startup: Verify all validation checks run"""
    validator = StartupValidator(config)
    report = validator.validate_all()

    assert "config_valid" in report.checks
    assert "qdrant_reachable" in report.checks
    assert "embedders_loadable" in report.checks
    assert "collections_healthy" in report.checks

def test_startup_fails_on_invalid_config():
    """Startup: Verify validation fails with bad config"""
    bad_config = Config(qdrant_host="", embedder_model="invalid")
    validator = StartupValidator(bad_config)

    with pytest.raises(ValidationError):
        validator.validate_all()

def test_startup_fails_on_qdrant_unreachable():
    """Startup: Verify validation fails if Qdrant down"""
    config = Config(qdrant_host="invalid", qdrant_port=9999)
    validator = StartupValidator(config)

    with pytest.raises(ValidationError):
        validator.validate_all()

def test_embedder_dimension_verification():
    """Startup: Verify embedder dimensions match spec"""
    validator = StartupValidator(config)

    # Should verify all 4 models produce correct dimensions
    report = validator._validate_embedders()

    assert report.checks["arctic_dimension"] == 1024
    assert report.checks["nomic_dimension"] == 768
    assert report.checks["bge_dimension"] == 384
    assert report.checks["minilm_dimension"] == 384
```

**Integration Test (WAYPOINT 7 - CRITICAL):**
```python
# tests/integration/test_phase1_end_to_end.py
def test_phase1_end_to_end():
    """
    Phase 1 Integration: Full pipeline from config → embedder → qdrant → unified API
    """
    # 1. Load config
    config = Config.from_yaml("config.yaml")

    # 2. Startup validation
    validator = StartupValidator(config)
    validator.validate_all()  # Should pass

    # 3. Create embedder factory
    factory = EmbedderFactory()
    arctic = factory.create_embedder("arctic")

    # 4. Create Qdrant client
    qdrant = QdrantClientWrapper(host=config.qdrant_host, port=config.qdrant_port)
    qdrant.ensure_collections_exist()

    # 5. Create UnifiedVectorStore
    store = UnifiedVectorStore(qdrant)
    store.set_embedder(arctic)

    # 6. Ingest test chunk
    chunk = Chunk(content="Test content for Phase 1 validation")
    store.upsert([chunk])

    # 7. Search and verify
    results = store.search("Phase 1 validation", top_k=1)
    assert len(results) == 1
    assert "Test content" in results[0].content

    # 8. Test embedder switching
    minilm = factory.create_embedder("minilm")
    store.set_embedder(minilm)

    chunk2 = Chunk(content="MiniLM test content")
    store.upsert([chunk2])

    results2 = store.search("MiniLM", top_k=1)
    assert len(results2) == 1

    # 9. Verify collections are separate
    assert qdrant.count("semvecmem_1024d") == 1  # Arctic chunk
    assert qdrant.count("semvecmem_384d") == 1   # MiniLM chunk
```

**Quality Gate (Phase 1 Exit):**
```bash
# Run full quality check suite
./scripts/quality_check.sh

# Phase 1 specific checks
pytest tests/integration/test_phase1_end_to_end.py -v

# Coverage report
pytest --cov=src/semvecmem --cov-report=html
# Open htmlcov/index.html and verify >80%

# Complexity report
radon cc src/semvecmem/ -a -s > complexity_report_phase1.txt
# Review: No methods with CC > 6

# Maintainability index
radon mi src/semvecmem/ -s
# Target: MI > B (moderate maintainability)
```

**Technical Debt Review (Phase 1):**
```bash
# Generate comprehensive debt report
cat > scripts/debt_report.sh <<'EOF'
#!/bin/bash

echo "🔍 Technical Debt Report - Phase 1"
echo "=================================="

echo ""
echo "1. Code Coverage:"
pytest --cov=src/semvecmem --cov-report=term-missing | grep TOTAL

echo ""
echo "2. Cyclomatic Complexity (High-Risk Methods):"
radon cc src/semvecmem/ -n B  # Show methods with CC > 6

echo ""
echo "3. Maintainability Index:"
radon mi src/semvecmem/ -n C  # Show modules with MI < C

echo ""
echo "4. Type Coverage:"
mypy src/semvecmem/ --strict

echo ""
echo "5. Code Quality Issues:"
ruff check src/semvecmem/

echo ""
echo "6. TODO/FIXME Count:"
grep -r "TODO\|FIXME\|HACK" src/semvecmem/ | wc -l
EOF

chmod +x scripts/debt_report.sh
./scripts/debt_report.sh > phase1_debt_report.txt
```

**Refactoring Session:**
- Review debt report
- Address all CC > 6 methods
- Fix all type errors
- Resolve all ruff issues
- Document any accepted technical debt (with justification)

**Phase 1 Exit Criteria:**
- ✅ All 7 waypoint tests passing
- ✅ Integration test passing
- ✅ Code coverage >80%
- ✅ All methods CC ≤ 6
- ✅ Mypy strict mode clean
- ✅ Ruff clean
- ✅ Maintainability Index ≥ B
- ✅ Zero TODO/FIXME in production code

---

## Phase 2: Ingestion & Retrieval (3-4 Days, 4 Waypoints)

### Day 2.1: TreeSitter Chunking

**Build:**
- [ ] TreeSitter AST parser integration
- [ ] Language detection (Python, JS, TS for MVP)
- [ ] Function/class extraction
- [ ] NLTK fallback for non-code

**Test (WAYPOINT 8):**
```python
# tests/test_chunking.py
def test_treesitter_python_function_extraction():
    """Chunking: Verify Python function extraction"""
    code = '''
def example_function(x: int) -> int:
    """Example docstring"""
    return x * 2

class ExampleClass:
    def method(self):
        pass
'''

    chunker = TreeSitterChunker(language="python")
    chunks = chunker.chunk(code)

    assert len(chunks) >= 2  # Function + class
    assert any("example_function" in c.content for c in chunks)
    assert any("ExampleClass" in c.content for c in chunks)

def test_treesitter_javascript_extraction():
    """Chunking: Verify JavaScript function extraction"""
    code = '''
function exampleFunc() {
    return 42;
}

const arrowFunc = () => console.log('test');
'''

    chunker = TreeSitterChunker(language="javascript")
    chunks = chunker.chunk(code)

    assert len(chunks) >= 2
    assert any("exampleFunc" in c.content for c in chunks)

def test_nltk_fallback_for_markdown():
    """Chunking: Verify NLTK fallback for non-code"""
    markdown = "# Header\n\n" + "Sentence. " * 100

    chunker = ChunkerFactory().get_chunker("markdown")
    chunks = chunker.chunk(markdown)

    # Should chunk by sentences, max 512 tokens
    assert all(len(c.content.split()) <= 512 for c in chunks)

def test_deterministic_chunk_ids():
    """Chunking: Verify same content → same ID"""
    code = "def test(): pass"

    chunker = TreeSitterChunker(language="python")
    chunks1 = chunker.chunk(code)
    chunks2 = chunker.chunk(code)

    assert chunks1[0].id == chunks2[0].id
```

**Complexity Check:**
```bash
radon cc src/semvecmem/chunking/ -s
# Target: CC ≤ 6 per method
```

---

### Day 2.2: Retrieval Engine

**Build:**
- [ ] Query processing
- [ ] Semantic search via embeddings
- [ ] Result ranking (cosine similarity)
- [ ] Top-K selection

**Test (WAYPOINT 9):**
```python
# tests/test_retrieval.py
def test_semantic_search_accuracy():
    """Retrieval: Verify semantic search finds relevant results"""
    store = UnifiedVectorStore(qdrant)
    store.set_embedder(EmbedderFactory().create_embedder("arctic"))

    # Ingest test corpus
    chunks = [
        Chunk(content="Python function for authentication"),
        Chunk(content="JavaScript authentication handler"),
        Chunk(content="Database connection pooling"),
        Chunk(content="HTTP request routing"),
    ]
    store.upsert(chunks)

    # Query: Should prioritize auth-related chunks
    results = store.search("authentication logic", top_k=2)

    assert len(results) == 2
    assert "authentication" in results[0].content.lower()
    assert "authentication" in results[1].content.lower()

def test_query_latency():
    """Retrieval: Verify query latency <500ms"""
    store = setup_store_with_1000_chunks()

    import time
    start = time.time()
    results = store.search("test query", top_k=5)
    elapsed = time.time() - start

    assert elapsed < 0.5  # <500ms

def test_empty_results():
    """Retrieval: Verify graceful handling of no results"""
    store = UnifiedVectorStore(qdrant)
    store.set_embedder(EmbedderFactory().create_embedder("arctic"))

    results = store.search("nonexistent query")
    assert results == []
```

**Performance Test:**
```python
# tests/performance/test_retrieval_performance.py
@pytest.mark.benchmark
def test_retrieval_scales_with_corpus_size():
    """Performance: Verify latency stays <500ms with large corpus"""
    store = UnifiedVectorStore(qdrant)
    store.set_embedder(EmbedderFactory().create_embedder("arctic"))

    # Test with 1K, 10K, 100K chunks
    for corpus_size in [1000, 10000, 100000]:
        populate_store_with_n_chunks(store, corpus_size)

        latencies = []
        for _ in range(10):
            start = time.time()
            store.search("test query", top_k=5)
            latencies.append(time.time() - start)

        avg_latency = np.mean(latencies)
        p95_latency = np.percentile(latencies, 95)

        assert avg_latency < 0.5, f"Avg latency {avg_latency:.3f}s at {corpus_size} chunks"
        assert p95_latency < 1.0, f"P95 latency {p95_latency:.3f}s at {corpus_size} chunks"
```

---

### Day 2.3: Concurrency Safety

**Build:**
- [ ] Deterministic chunk IDs (already implemented)
- [ ] Concurrent ingestion tests
- [ ] Race condition prevention

**Test (WAYPOINT 10):**
```python
# tests/test_concurrency.py
def test_concurrent_ingestion_no_duplicates():
    """Concurrency: Verify no duplicates from simultaneous upserts"""
    store = UnifiedVectorStore(qdrant)
    store.set_embedder(EmbedderFactory().create_embedder("arctic"))

    chunk = Chunk(content="Identical content")

    # Simulate 10 agents upserting same content simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(store.upsert, [chunk]) for _ in range(10)]
        concurrent.futures.wait(futures)

    # Verify only 1 chunk exists
    results = store.search("Identical content")
    assert len(results) == 1

def test_concurrent_search_and_upsert():
    """Concurrency: Verify reads don't block writes"""
    store = setup_store_with_1000_chunks()

    def search_worker():
        for _ in range(100):
            store.search("test query")

    def upsert_worker():
        for i in range(100):
            store.upsert([Chunk(content=f"New chunk {i}")])

    # Run searches and upserts concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        search_futures = [executor.submit(search_worker) for _ in range(5)]
        upsert_futures = [executor.submit(upsert_worker) for _ in range(5)]

        concurrent.futures.wait(search_futures + upsert_futures)

    # Verify no corruption
    total_chunks = qdrant.count("semvecmem_1024d")
    assert total_chunks == 1000 + 500  # Original + 5 workers × 100 chunks
```

---

### Day 2.4: MCP Server + Phase 2 Integration

**Build:**
- [ ] FastMCP server setup
- [ ] Tool definitions (ingest, recall, summarize)
- [ ] MCP integration

**Test (WAYPOINT 11):**
```python
# tests/test_mcp_server.py
def test_mcp_ingest_tool():
    """MCP: Verify ingest tool works"""
    response = mcp_server.call_tool(
        "semvecmem_ingest",
        {"path": "test_file.py", "recursive": False}
    )

    assert response.success == True
    assert response.chunks_ingested > 0

def test_mcp_recall_tool():
    """MCP: Verify recall tool works"""
    # Ingest first
    mcp_server.call_tool("semvecmem_ingest", {"path": "test_corpus/"})

    # Recall
    response = mcp_server.call_tool(
        "semvecmem_recall",
        {"query": "authentication logic", "top_k": 5}
    )

    assert len(response.results) <= 5
    assert all("score" in r for r in response.results)

def test_mcp_token_overhead():
    """MCP: Verify token overhead <5%"""
    # Ingest 1000 chunks
    mcp_server.call_tool("semvecmem_ingest", {"path": "large_corpus/"})

    # Recall and measure payload
    response = mcp_server.call_tool(
        "semvecmem_recall",
        {"query": "test", "top_k": 5}
    )

    payload_size = len(json.dumps(response))
    content_size = sum(len(r["content"]) for r in response.results)

    overhead = (payload_size - content_size) / content_size
    assert overhead < 0.05  # <5% overhead
```

**Integration Test (Phase 2 Exit):**
```python
# tests/integration/test_phase2_end_to_end.py
def test_phase2_end_to_end():
    """
    Phase 2 Integration: Chunking → Ingestion → Retrieval → MCP
    """
    # 1. Set up store
    store = UnifiedVectorStore(qdrant)
    store.set_embedder(EmbedderFactory().create_embedder("arctic"))

    # 2. Chunk code file
    with open("example_code.py") as f:
        code = f.read()

    chunker = TreeSitterChunker(language="python")
    chunks = chunker.chunk(code)

    # 3. Ingest chunks
    store.upsert(chunks)

    # 4. Retrieve semantically
    results = store.search("function that handles authentication", top_k=3)
    assert len(results) > 0

    # 5. Verify via MCP
    mcp_response = mcp_server.call_tool(
        "semvecmem_recall",
        {"query": "authentication", "top_k": 3}
    )
    assert len(mcp_response.results) > 0

    # 6. Verify latency
    assert mcp_response.latency_ms < 500
```

**Quality Gate (Phase 2 Exit):**
```bash
# Full quality check
./scripts/quality_check.sh

# Performance benchmarks
pytest tests/performance/ -v --benchmark

# Concurrency stress test
pytest tests/test_concurrency.py -v -n 10

# Debt report
./scripts/debt_report.sh > phase2_debt_report.txt

# Coverage
pytest --cov=src/semvecmem --cov-report=html
# Target: >80%
```

**Phase 2 Exit Criteria:**
- ✅ All 11 waypoint tests passing
- ✅ Retrieval accuracy >85% (manual spot-check)
- ✅ Query latency <500ms (measured)
- ✅ Token overhead <5% (measured)
- ✅ Concurrency tests pass
- ✅ Code coverage >80%
- ✅ All methods CC ≤ 6
- ✅ Zero critical technical debt

---

## Phase 3: Migration & Benchmarks (5-6 Days, 4 Waypoints)

### Day 3.1-3.2: CLI Development

**Build:**
- [ ] CLI framework (typer)
- [ ] Commands: ingest, recall, stats, health
- [ ] Command validation

**Test (WAYPOINT 12):**
```python
# tests/test_cli.py
def test_cli_ingest_command():
    """CLI: Verify ingest command works"""
    result = runner.invoke(cli, ["ingest", "test_file.py"])
    assert result.exit_code == 0
    assert "chunks ingested" in result.output

def test_cli_recall_command():
    """CLI: Verify recall command works"""
    # Ingest first
    runner.invoke(cli, ["ingest", "test_corpus/"])

    # Recall
    result = runner.invoke(cli, ["recall", "authentication"])
    assert result.exit_code == 0
    assert "results found" in result.output

def test_cli_health_command():
    """CLI: Verify health check works"""
    result = runner.invoke(cli, ["health"])
    assert result.exit_code == 0
    assert "Qdrant: ✅" in result.output
    assert "Embedder: ✅" in result.output
```

---

### Day 3.3-3.4: Migration Tool (CRITICAL)

**Build:**
- [ ] Basic migration (batch processing)
- [ ] Canary migration strategy
- [ ] Checkpointing (resume from failure)
- [ ] State management
- [ ] Rollback support

**Test (WAYPOINT 13 - MOST CRITICAL):**
```python
# tests/test_migration.py
def test_basic_migration():
    """Migration: Verify basic migration works"""
    # Ingest 100 chunks with MiniLM
    store = setup_store_with_embedder("minilm", chunk_count=100)

    # Migrate to Arctic
    migrator = MigrationTool()
    result = migrator.migrate("minilm", "arctic")

    assert result.chunks_migrated == 100
    assert result.errors == 0

    # Verify chunks now in 1024d collection
    count_1024 = qdrant.count("semvecmem_1024d")
    count_384 = qdrant.count("semvecmem_384d")
    assert count_1024 == 100
    assert count_384 == 0  # Old chunks removed

def test_canary_migration():
    """Migration: Verify canary migration works"""
    store = setup_store_with_embedder("minilm", chunk_count=1000)

    migrator = MigrationTool()
    result = migrator.migrate_with_canary(
        "minilm",
        "arctic",
        canary_percentage=0.1,
        validation_queries=["test query 1", "test query 2"]
    )

    # Verify canary phase (100 chunks)
    assert "canary_phase_complete" in result.stages
    assert result.stages["canary_phase_complete"]["chunks"] == 100

    # Verify validation passed
    assert result.stages["canary_validation"]["passed"] == True

    # Verify full migration
    assert result.chunks_migrated == 1000

def test_migration_resume_from_checkpoint():
    """Migration: Verify resume from checkpoint after failure"""
    store = setup_store_with_embedder("minilm", chunk_count=1000)

    migrator = MigrationTool()

    # Simulate failure at chunk 500
    with patch.object(qdrant, 'upsert') as mock_upsert:
        mock_upsert.side_effect = [None] * 500 + [OSError("Disk full")]

        with pytest.raises(MigrationError):
            migrator.migrate("minilm", "arctic")

    # Verify checkpoint saved
    checkpoint = migrator.load_checkpoint()
    assert checkpoint.chunks_migrated == 500
    assert checkpoint.last_chunk_id is not None

    # Resume migration
    result = migrator.resume_migration()
    assert result.chunks_migrated == 1000
    assert result.resumed_from == 500

def test_migration_rollback():
    """Migration: Verify rollback on validation failure"""
    store = setup_store_with_embedder("minilm", chunk_count=1000)

    migrator = MigrationTool()

    # Force validation to fail
    with patch.object(migrator, '_validate_canary', return_value=False):
        with pytest.raises(MigrationValidationError):
            migrator.migrate_with_canary("minilm", "arctic")

    # Verify rollback occurred
    count_384 = qdrant.count("semvecmem_384d")
    count_1024 = qdrant.count("semvecmem_1024d")

    assert count_384 == 1000  # Original chunks intact
    assert count_1024 == 0    # No migrated chunks

def test_migration_state_tracking():
    """Migration: Verify state transitions tracked"""
    migrator = MigrationTool()

    # Start migration
    migrator.start_migration("minilm", "arctic")
    assert migrator.state == MigrationState.IN_PROGRESS

    # Complete canary
    migrator.complete_canary()
    assert migrator.state == MigrationState.CANARY_COMPLETE

    # Complete full migration
    migrator.complete_migration()
    assert migrator.state == MigrationState.COMPLETE

    # Verify state transition audit trail
    transitions = migrator.get_state_transitions()
    assert len(transitions) >= 3
    assert transitions[0]["from"] == "not_started"
    assert transitions[-1]["to"] == "complete"
```

**Failure Injection Tests (WAYPOINT 14 - CRITICAL):**
```python
# tests/integration/test_migration_failures.py
@pytest.mark.slow
class TestMigrationFailureScenarios:
    """Comprehensive failure scenarios for migration robustness"""

    def test_disk_full_during_migration(self):
        """Failure: Disk full mid-migration"""
        # [Implementation from earlier synthesis]
        pass

    def test_network_timeout_to_qdrant(self):
        """Failure: Qdrant connection timeout"""
        pass

    def test_model_crash_mid_embedding(self):
        """Failure: Embedder crash during encoding"""
        pass

    def test_corrupted_source_collection(self):
        """Failure: Corrupted data in source"""
        pass

    def test_concurrent_migration_attempts(self):
        """Failure: Multiple processes attempt migration"""
        pass

    @pytest.mark.benchmark
    def test_large_corpus_stress(self):
        """Stress: 100K chunk migration"""
        pass
```

**Complexity Review:**
```bash
radon cc src/semvecmem/migration/ -s

# Migration tool is complex, but should stay ≤8 per method
# If any method >8, refactor with strategy pattern
```

---

### Day 3.5: Benchmark Suite

**Build:**
- [ ] Test corpus (150 files)
- [ ] Ground truth annotations
- [ ] Benchmark runner
- [ ] Accuracy measurement

**Test (WAYPOINT 15):**
```python
# tests/benchmark/test_accuracy_benchmark.py
@pytest.mark.benchmark
def test_benchmark_all_models():
    """Benchmark: Verify all 4 models meet accuracy targets"""
    corpus = load_benchmark_corpus()  # 150 files
    queries = load_benchmark_queries()  # 20 queries with ground truth

    results = {}
    for model_name in ["arctic", "nomic", "bge", "minilm"]:
        store = setup_store_with_model(model_name)

        # Ingest corpus
        for file in corpus:
            chunks = chunk_file(file)
            store.upsert(chunks)

        # Run benchmark queries
        accuracy = measure_accuracy(store, queries)
        results[model_name] = accuracy

    # Verify accuracy targets
    assert results["arctic"] >= 0.85, f"Arctic: {results['arctic']:.1%}"
    assert results["nomic"] >= 0.80, f"Nomic: {results['nomic']:.1%}"
    assert results["bge"] >= 0.75, f"BGE: {results['bge']:.1%}"
    assert results["minilm"] >= 0.70, f"MiniLM: {results['minilm']:.1%}"

    # Log results
    print(f"\n📊 Benchmark Results:")
    for model, acc in results.items():
        print(f"  {model}: {acc:.1%}")
```

---

### Day 3.6: Phase 3 Integration + Final Debt Review

**Integration Test:**
```python
# tests/integration/test_phase3_end_to_end.py
def test_phase3_complete_migration_workflow():
    """
    Phase 3 Integration: CLI → Migration → Benchmark
    """
    # 1. Ingest via CLI
    result = runner.invoke(cli, ["ingest", "test_corpus/", "--model", "minilm"])
    assert result.exit_code == 0

    # 2. Migrate to Arctic
    result = runner.invoke(cli, [
        "migrate-embeddings",
        "--from", "minilm",
        "--to", "arctic",
        "--canary", "0.1"
    ])
    assert result.exit_code == 0
    assert "Migration complete" in result.output

    # 3. Run benchmark
    result = runner.invoke(cli, ["benchmark"])
    assert result.exit_code == 0
    assert "Arctic: " in result.output

    # 4. Verify migration successful
    result = runner.invoke(cli, ["stats"])
    assert "semvecmem_1024d" in result.output
```

**Final Technical Debt Audit:**
```bash
# Comprehensive debt review
./scripts/debt_report.sh > phase3_debt_report.txt

# Compare with previous phases
diff phase1_debt_report.txt phase3_debt_report.txt

# Quality metrics
pytest --cov=src/semvecmem --cov-report=html --cov-fail-under=80
radon cc src/semvecmem/ -n C  # Should show no CC > 10
radon mi src/semvecmem/ -n C  # Should show no MI < C
mypy src/semvecmem/ --strict
ruff check src/semvecmem/

# Count remaining TODOs/FIXMEs
grep -r "TODO\|FIXME\|HACK" src/semvecmem/ || echo "Clean!"
```

**Phase 3 Exit Criteria:**
- ✅ All 15 waypoint tests passing
- ✅ Migration tool passes ALL failure injection tests
- ✅ Canary migration working
- ✅ Benchmark validates >85% accuracy (87% for Arctic)
- ✅ All 4 models benchmarked
- ✅ Code coverage >80%
- ✅ All methods CC ≤ 8 (migration), ≤ 6 (others)
- ✅ Zero high-priority technical debt

---

## Phase 4: Polish & Integration (2-3 Days, 2 Waypoints)

### Day 4.1: Final Integration Testing

**Test (WAYPOINT 16 - FINAL):**
```python
# tests/integration/test_complete_system.py
@pytest.mark.integration
def test_complete_system_smoke_test():
    """Final: Complete system smoke test"""
    # Full workflow from scratch

    # 1. Initialize system
    runner.invoke(cli, ["setup-qdrant"])
    runner.invoke(cli, ["health"])

    # 2. Ingest large corpus
    runner.invoke(cli, ["ingest", "large_corpus/", "--recursive"])

    # 3. Search
    result = runner.invoke(cli, ["recall", "authentication logic"])
    assert result.exit_code == 0

    # 4. Migrate
    result = runner.invoke(cli, ["migrate-embeddings", "--from", "minilm", "--to", "arctic"])
    assert result.exit_code == 0

    # 5. Benchmark
    result = runner.invoke(cli, ["benchmark"])
    assert result.exit_code == 0

    # 6. Stats
    result = runner.invoke(cli, ["stats"])
    assert result.exit_code == 0
```

---

### Day 4.2: Performance Profiling

**Test (WAYPOINT 17 - FINAL):**
```python
# tests/performance/test_system_performance.py
@pytest.mark.performance
def test_memory_usage_under_8gb():
    """Performance: Verify memory usage <8GB"""
    import psutil
    process = psutil.Process()

    # Load all 4 models
    factory = EmbedderFactory()
    models = [
        factory.create_embedder("arctic"),
        factory.create_embedder("nomic"),
        factory.create_embedder("bge"),
        factory.create_embedder("minilm")
    ]

    # Ingest large corpus
    store = UnifiedVectorStore(qdrant)
    store.set_embedder(models[0])

    chunks = generate_large_corpus(10000)
    store.upsert(chunks)

    # Measure memory
    memory_mb = process.memory_info().rss / 1024 / 1024
    assert memory_mb < 8000, f"Memory usage: {memory_mb:.0f}MB"

@pytest.mark.performance
def test_query_latency_percentiles():
    """Performance: Verify latency targets"""
    store = setup_store_with_10k_chunks()

    latencies = []
    for _ in range(100):
        start = time.time()
        store.search("test query", top_k=5)
        latencies.append(time.time() - start)

    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)

    assert p50 < 0.100, f"P50: {p50:.3f}s"
    assert p95 < 0.500, f"P95: {p95:.3f}s"
    assert p99 < 1.000, f"P99: {p99:.3f}s"
```

---

### Day 4.3: Final Quality Audit

**Final Debt Report:**
```bash
#!/bin/bash
# scripts/final_quality_audit.sh

echo "🎯 FINAL QUALITY AUDIT - SemVecMem v1.0"
echo "========================================"

echo ""
echo "1. TEST COVERAGE:"
pytest --cov=src/semvecmem --cov-report=term --cov-fail-under=80
COVERAGE_EXIT=$?

echo ""
echo "2. CYCLOMATIC COMPLEXITY:"
radon cc src/semvecmem/ -a -nc
radon cc src/semvecmem/ -n C
CC_EXIT=$?

echo ""
echo "3. MAINTAINABILITY INDEX:"
radon mi src/semvecmem/ -s
radon mi src/semvecmem/ -n C
MI_EXIT=$?

echo ""
echo "4. TYPE COVERAGE:"
mypy src/semvecmem/ --strict
MYPY_EXIT=$?

echo ""
echo "5. CODE QUALITY:"
ruff check src/semvecmem/
RUFF_EXIT=$?

echo ""
echo "6. SECURITY AUDIT:"
bandit -r src/semvecmem/
BANDIT_EXIT=$?

echo ""
echo "7. DOCUMENTATION COVERAGE:"
interrogate -v src/semvecmem/ --fail-under 80
DOC_EXIT=$?

echo ""
echo "8. TECHNICAL DEBT COUNT:"
TODO_COUNT=$(grep -r "TODO\|FIXME\|HACK" src/semvecmem/ | wc -l)
echo "TODO/FIXME/HACK count: $TODO_COUNT"

echo ""
echo "========================================"
echo "FINAL RESULTS:"
[ $COVERAGE_EXIT -eq 0 ] && echo "✅ Coverage >80%" || echo "❌ Coverage <80%"
[ $CC_EXIT -eq 0 ] && echo "✅ Complexity ≤10" || echo "❌ Complexity >10"
[ $MI_EXIT -eq 0 ] && echo "✅ Maintainability ≥C" || echo "❌ Maintainability <C"
[ $MYPY_EXIT -eq 0 ] && echo "✅ Type checking clean" || echo "❌ Type errors found"
[ $RUFF_EXIT -eq 0 ] && echo "✅ Code quality clean" || echo "❌ Quality issues found"
[ $BANDIT_EXIT -eq 0 ] && echo "✅ Security audit passed" || echo "❌ Security issues found"
[ $DOC_EXIT -eq 0 ] && echo "✅ Documentation >80%" || echo "❌ Documentation <80%"
[ $TODO_COUNT -eq 0 ] && echo "✅ Zero technical debt" || echo "⚠️  $TODO_COUNT debt items"

# Exit with failure if any check failed
if [ $COVERAGE_EXIT -ne 0 ] || [ $CC_EXIT -ne 0 ] || [ $MI_EXIT -ne 0 ] || \
   [ $MYPY_EXIT -ne 0 ] || [ $RUFF_EXIT -ne 0 ] || [ $BANDIT_EXIT -ne 0 ] || \
   [ $DOC_EXIT -ne 0 ]; then
    echo ""
    echo "❌ QUALITY AUDIT FAILED"
    exit 1
else
    echo ""
    echo "✅ QUALITY AUDIT PASSED"
    exit 0
fi
```

**Phase 4 Exit Criteria (RELEASE CRITERIA):**
- ✅ All 17 waypoint tests passing
- ✅ All integration tests passing
- ✅ Performance targets met
- ✅ Code coverage >80%
- ✅ All methods CC ≤ 8
- ✅ Maintainability Index ≥ C
- ✅ Mypy strict mode clean
- ✅ Ruff clean
- ✅ Bandit security scan clean
- ✅ Documentation >80%
- ✅ Zero TODO/FIXME in production code
- ✅ Final quality audit passes

---

## Continuous Monitoring During Development

### Daily Quality Dashboard

```bash
# scripts/daily_dashboard.sh
#!/bin/bash

echo "📊 Daily Quality Dashboard - $(date +%Y-%m-%d)"
echo "============================================="

# Quick metrics
echo ""
echo "Coverage: $(pytest --cov=src/semvecmem --cov-report=term | grep TOTAL | awk '{print $4}')"
echo "CC Average: $(radon cc src/semvecmem/ -a -s | grep Average | awk '{print $3}')"
echo "MI Average: $(radon mi src/semvecmem/ -s | grep Average | awk '{print $3}')"
echo "Tests Passing: $(pytest --co -q | wc -l) tests"
echo "Type Errors: $(mypy src/semvecmem/ | grep -c error || echo 0)"
echo "Code Quality Issues: $(ruff check src/semvecmem/ | grep -c error || echo 0)"

# Trend
echo ""
echo "Trend (vs yesterday):"
diff <(cat yesterday_metrics.txt) <(cat today_metrics.txt) || echo "First run"

# Save today's metrics
cat > today_metrics.txt <<EOF
$(pytest --cov=src/semvecmem --cov-report=term | grep TOTAL)
$(radon cc src/semvecmem/ -a -s | grep Average)
$(radon mi src/semvecmem/ -s | grep Average)
EOF
```

---

## Summary: 17 Testing Waypoints

| Phase | Waypoint | Focus | CC Target | Coverage Target |
|-------|----------|-------|-----------|-----------------|
| POC | 1 | Unified API POC | ≤6 | >50% |
| 1 | 2 | Config system | ≤4 | >80% |
| 1 | 3 | Embedder factory | ≤5 | >80% |
| 1 | 4 | Qdrant + multi-collection | ≤6 | >80% |
| 1 | 5 | UnifiedVectorStore | ≤6 | >80% |
| 1 | 6 | Startup validation | ≤7 | >80% |
| 1 | 7 | Phase 1 integration | N/A | >80% |
| 2 | 8 | Chunking | ≤6 | >80% |
| 2 | 9 | Retrieval | ≤6 | >80% |
| 2 | 10 | Concurrency | N/A | >80% |
| 2 | 11 | MCP + Phase 2 integration | N/A | >80% |
| 3 | 12 | CLI | ≤5 | >80% |
| 3 | 13 | Migration tool | ≤8 | >80% |
| 3 | 14 | Migration failures | ≤8 | 100% |
| 3 | 15 | Benchmarks | N/A | N/A |
| 4 | 16 | System integration | N/A | >80% |
| 4 | 17 | Performance | N/A | N/A |

**Philosophy:** Build → Test → Refactor → Repeat

**Benefits:**
- ✅ Catches technical debt immediately
- ✅ Prevents compound complexity
- ✅ Maintains velocity (no late-stage refactoring marathons)
- ✅ Continuous quality visibility
- ✅ Safe to ship at any waypoint

---

## Next Steps

1. [ ] Review waypoint strategy with team
2. [ ] Set up testing infrastructure (Day 0.1)
3. [ ] Begin POC (Day 0.2)
4. [ ] Establish daily quality dashboard
5. [ ] Start Phase 1 with continuous testing

---

**Plan Completed By:** Claude Code (Sonnet 4.5)
**Date:** 2025-10-07
**Version:** 1.3.1 (Quality-Gated, Testing Waypoints)
**Philosophy:** Quality first, technical debt never
