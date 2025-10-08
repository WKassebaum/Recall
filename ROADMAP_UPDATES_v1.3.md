# SemVecMem Roadmap Updates v1.3

**Date:** 2025-10-05
**Based On:** Critical Architecture Review
**Impact:** Timeline extended to 10-11 days, critical architecture fixes

---

## Summary of Changes

Based on comprehensive architecture review, we've identified **7 critical issues** that require addressing before/during implementation:

### Critical Issues Fixed

1. ✅ **Multi-Collection Strategy:** Separate collections per dimension (384D, 768D, 1024D)
2. ✅ **Simplified Fallback:** Reduced from 4-tier to 2-tier (Arctic → MiniLM)
3. ✅ **Migration Tool:** Moved from Phase 4 to Phase 3 (required for usability)
4. ✅ **Startup Validation:** Added config/dimension validation
5. ✅ **Concurrency Safety:** Deterministic chunk IDs + concurrency tests
6. ✅ **Error Handling:** Comprehensive coverage across all phases
7. ✅ **Benchmark Suite:** Moved from "optional" to required (Phase 3)

### Timeline Impact

**Original:** 7 days (56 hours)
**Updated:** 10-11 days (80-88 hours)
**Delta:** +3-4 days (+43% increase)

**Justification:** Critical issues (multi-collection, migration, benchmarks) were underestimated or missing.

---

## Updated Phase Breakdown

### Phase 1: Foundation & Core (3.5 days) - **+1 day from original**

**New Requirements:**

#### 1. Multi-Collection Strategy Implementation ⭐ **CRITICAL**

**Problem:** Different embedding models have different dimensions (384D, 768D, 1024D). Cannot mix dimensions in single Qdrant collection.

**Solution:**
```python
# src/semvecmem/storage/multi_collection.py

class MultiCollectionStrategy:
    """
    Manages multiple Qdrant collections, one per dimension.

    Collections:
    - semvecmem_384d: BGE + MiniLM
    - semvecmem_768d: Nomic
    - semvecmem_1024d: Arctic
    """

    DIMENSION_MAP = {
        "snowflake/arctic-embed-m": 1024,
        "nomic-embed-text-v1.5": 768,
        "bge-small-en-v1.5": 384,
        "all-MiniLM-L6-v2": 384
    }

    def get_collection_for_model(self, model_name: str) -> str:
        """Route to correct collection based on model dimensions."""
        dims = self.DIMENSION_MAP[model_name]
        return f"semvecmem_{dims}d"

    def ensure_collection_exists(self, model_name: str):
        """Auto-create collection if missing."""
        collection = self.get_collection_for_model(model_name)
        dims = self.DIMENSION_MAP[model_name]

        if not self.client.collection_exists(collection):
            self.client.create_collection(
                collection_name=collection,
                vectors_config={
                    "size": dims,
                    "distance": "Cosine"
                },
                hnsw_config={
                    "ef_construct": 100,
                    "m": 16
                }
            )
```

**Impact:**
- Users can switch models without dimension mismatch errors
- Each collection optimized for its dimension
- Enables hybrid queries across collections (future)

**Testing:**
- [ ] Create collections for all 4 models
- [ ] Verify dimension constraints enforced
- [ ] Test switching models without errors

**Effort:** +0.5 days

---

#### 2. Simplified Fallback Chain (2-Tier) ⭐ **RECOMMENDED**

**Problem:** 4-tier fallback (Arctic → Nomic → BGE → MiniLM) is over-engineered. Nomic (4.8GB) is larger than Arctic (3.5GB) - illogical fallback.

**Solution:**
```yaml
# config.yaml (SIMPLIFIED)

embedder: snowflake/arctic-embed-m  # Primary

fallback:
  enabled: true
  model: all-MiniLM-L6-v2  # Only fallback (smallest, most reliable)

# Alternative: Disable automatic fallback
fallback:
  enabled: false  # Fail fast with clear error message
```

**Implementation:**
```python
# src/semvecmem/embedder/factory.py

class EmbedderFactory:
    def create(self, config):
        primary_model = config.embedder

        try:
            return self._load_model(primary_model)
        except ModelLoadError as e:
            if config.fallback.enabled:
                logger.warning(f"{primary_model} failed, falling back to {config.fallback.model}")
                return self._load_model(config.fallback.model)
            else:
                raise ConfigurationError(
                    f"Failed to load {primary_model}. "
                    f"Options: (1) Install model, (2) Switch to all-MiniLM-L6-v2"
                ) from e
```

**Rationale:**
- Arctic or MiniLM - clear binary choice
- Nomic/BGE remain user-selectable, not automatic fallback
- Simpler code, easier to reason about
- MiniLM is smallest (most likely to succeed if Arctic fails)

**User Options:**
```bash
# Explicit model selection (no fallback needed)
semvecmem ingest file.py --embedder nomic-embed-text-v1.5
semvecmem ingest file.py --embedder bge-small-en-v1.5

# Use default with fallback
semvecmem ingest file.py  # Uses Arctic, falls back to MiniLM if needed
```

**Effort:** -0.5 days (simpler than 4-tier)

---

#### 3. Startup Validation Framework ⭐ **REQUIRED**

**Problem:** No validation on startup leads to cryptic runtime errors.

**Solution:**
```python
# src/semvecmem/core/validation.py

class StartupValidator:
    """Validates system state before allowing operations."""

    def validate_all(self, config):
        """Run all validation checks."""
        self.validate_config(config)
        self.validate_qdrant(config)
        self.validate_embedder(config)
        self.validate_collections(config)

    def validate_config(self, config):
        """Validate configuration values."""
        if config.embedder not in SUPPORTED_MODELS:
            raise ConfigError(f"Unsupported embedder: {config.embedder}")

        if config.top_k <= 0:
            raise ConfigError(f"top_k must be positive, got {config.top_k}")

    def validate_qdrant(self, config):
        """Check Qdrant is reachable."""
        try:
            health = self.client.health_check()
            if not health.ok:
                raise QdrantError("Qdrant unhealthy. Run: semvecmem setup-qdrant")
        except ConnectionError:
            raise QdrantError(
                "Cannot connect to Qdrant at {config.qdrant.host}:{config.qdrant.port}\n"
                "Run: semvecmem setup-qdrant"
            )

    def validate_embedder(self, config):
        """Test load embedder."""
        try:
            factory = EmbedderFactory(config)
            embedder = factory.create()
            # Quick embedding test
            embedder.embed(["test"])
        except Exception as e:
            raise EmbedderError(f"Failed to load {config.embedder}: {e}")

    def validate_collections(self, config):
        """Verify collection dimensions match embedder."""
        collection = self.get_collection_for_model(config.embedder)
        expected_dims = DIMENSION_MAP[config.embedder]

        if self.client.collection_exists(collection):
            info = self.client.get_collection(collection)
            actual_dims = info.config.params.vectors.size

            if actual_dims != expected_dims:
                raise DimensionMismatchError(
                    f"Collection {collection} has {actual_dims}D vectors, "
                    f"but {config.embedder} produces {expected_dims}D vectors.\n"
                    f"Run: semvecmem migrate-embeddings --to {config.embedder}"
                )
```

**When to Run:**
- On every MCP server startup
- Before each CLI command (optional, for performance)
- After config changes

**Effort:** +0.5 days

---

#### 4. Deterministic Chunk IDs ⭐ **REQUIRED**

**Problem:** Concurrent agents may ingest same file, creating duplicate chunks.

**Solution:**
```python
# src/semvecmem/core/chunking.py

def generate_chunk_id(content: str, metadata: dict) -> str:
    """
    Generate deterministic chunk ID from content.

    Same content → same ID → upsert (not duplicate).
    """
    # Include lang in hash for same content in different contexts
    stable_metadata = {
        "lang": metadata.get("lang", "unknown"),
        "chunk_type": metadata.get("chunk_type", "code")
    }

    hash_input = json.dumps({
        "content": content,
        "metadata": stable_metadata
    }, sort_keys=True)

    return hashlib.sha256(hash_input.encode()).hexdigest()
```

**Benefits:**
- Same file ingested twice → upsert, not duplicate
- Multiple agents can safely ingest concurrently
- Reproducible chunk IDs for debugging

**Testing:**
- [ ] Ingest same file twice → verify single chunk
- [ ] Concurrent ingest (2 agents, same file) → verify no corruption

**Effort:** +0.5 days (implementation + tests)

---

**Phase 1 Total:** 3.5 days

**Deliverables:**
- [ ] Multi-collection strategy working
- [ ] 2-tier fallback implemented
- [ ] Startup validation framework
- [ ] Deterministic chunk IDs
- [ ] All original Phase 1 tasks

---

### Phase 2: Core Functionality (2.5 days) - **+0.5 days from original**

**New Requirements:**

#### 1. Concurrency Test Suite ⭐ **REQUIRED**

**Scenarios to Test:**

**Test 1: Concurrent Ingestion**
```python
# tests/integration/test_concurrency.py

def test_concurrent_ingest_same_file():
    """Two agents ingest same file simultaneously."""
    file_path = "test_data/auth.py"

    # Start 2 ingest processes concurrently
    results = run_concurrent([
        lambda: ingest_file(file_path),
        lambda: ingest_file(file_path)
    ])

    # Verify: Only one set of chunks (deterministic IDs prevent duplicates)
    chunks = query_collection("semvecmem_1024d")
    expected_chunks = count_chunks_in_file(file_path)
    assert len(chunks) == expected_chunks
```

**Test 2: Concurrent Queries**
```python
def test_concurrent_queries():
    """10 agents query simultaneously."""
    query = "authentication logic"

    results = run_concurrent([
        lambda: recall_memory(query, top_k=5)
        for _ in range(10)
    ])

    # Verify: All results identical (deterministic)
    assert all(r == results[0] for r in results)
```

**Test 3: Read During Write**
```python
def test_query_during_ingest():
    """Query while ingestion is happening."""
    # Start long-running ingest
    ingest_thread = Thread(target=lambda: ingest_large_corpus())
    ingest_thread.start()

    time.sleep(0.5)  # Let ingest start

    # Query while ingesting
    results = recall_memory("test query")

    # Verify: Query succeeds (eventual consistency OK)
    assert results is not None
```

**Effort:** +0.5 days

---

**Phase 2 Total:** 2.5 days

**Deliverables:**
- [ ] Concurrency test suite
- [ ] Runtime error handling
- [ ] Collection routing logic
- [ ] All original Phase 2 tasks

---

### Phase 3: CLI & Tools (4 days) - **+1.5 days from original**

**New Requirements:**

#### 1. Migration Tool ⭐ **MOVED FROM PHASE 4** (CRITICAL)

**Problem:** Users switch models but have existing chunks in old collection.

**Solution:**
```bash
semvecmem migrate-embeddings \
  --from all-MiniLM-L6-v2 \
  --to snowflake/arctic-embed-m \
  --batch-size 1000 \
  --verify \
  --keep-old  # Optional: keep old collection as backup
```

**Implementation:**
```python
# src/semvecmem/cli/migrate_cmd.py

@click.command()
@click.option('--from', 'from_model', required=True)
@click.option('--to', 'to_model', required=True)
@click.option('--batch-size', default=1000)
@click.option('--verify', is_flag=True)
@click.option('--keep-old', is_flag=True)
def migrate_embeddings(from_model, to_model, batch_size, verify, keep_old):
    """Migrate embeddings from one model to another."""

    # 1. Get source and target collections
    src_collection = get_collection_for_model(from_model)
    dst_collection = get_collection_for_model(to_model)

    # 2. Load target embedder
    embedder = EmbedderFactory(config).create_for_model(to_model)

    # 3. Ensure target collection exists
    ensure_collection_exists(dst_collection, to_model)

    # 4. Retrieve all chunks from source (scroll API)
    total_chunks = count_chunks(src_collection)

    with tqdm(total=total_chunks, desc="Migrating chunks") as pbar:
        for batch in scroll_chunks(src_collection, batch_size):
            # Extract text content only (not vectors)
            texts = [chunk.payload['content'] for chunk in batch]
            metadatas = [chunk.payload['metadata'] for chunk in batch]

            # Re-embed with new model
            vectors = embedder.embed(texts)

            # Store in target collection
            upsert_chunks(dst_collection, texts, vectors, metadatas)

            pbar.update(len(batch))

    # 5. Verify migration (optional)
    if verify:
        verify_migration(src_collection, dst_collection)

    # 6. Update config to use new model
    update_config('embedder', to_model)

    # 7. Delete old collection (unless --keep-old)
    if not keep_old:
        delete_collection(src_collection)
        click.echo(f"Deleted old collection: {src_collection}")

    click.echo(f"✓ Migration complete: {from_model} → {to_model}")
    click.echo(f"  Migrated: {total_chunks} chunks")
    click.echo(f"  New collection: {dst_collection}")
```

**Edge Cases:**
- [ ] Handle partial failures (resume from checkpoint)
- [ ] Verify embedder loads before starting migration
- [ ] Estimate time for large migrations (10K+ chunks)

**Effort:** +1 day

---

#### 2. Benchmark Suite ⭐ **MOVED FROM "OPTIONAL"** (CRITICAL)

**Purpose:** Validate 87% accuracy claim with real data.

**Test Corpus:**
```
tests/benchmark/
  ├─ corpus/
  │  ├─ python/       # 100 Python files (10K LOC each)
  │  ├─ javascript/   # 50 JS files (5K LOC each)
  │  └─ prose/        # 20 markdown files
  └─ queries.json     # 20 test queries with ground truth
```

**queries.json Example:**
```json
[
  {
    "id": 1,
    "query": "authentication logic with OAuth",
    "relevant_chunks": ["file1.py:lines_12-45", "file3.py:lines_89-120"],
    "lang": "python"
  },
  {
    "id": 2,
    "query": "error handling patterns with try-catch",
    "relevant_chunks": ["file5.js:lines_34-56", "file7.js:lines_78-95"],
    "lang": "javascript"
  }
]
```

**Benchmark Command:**
```bash
semvecmem benchmark \
  --corpus tests/benchmark/corpus/ \
  --queries tests/benchmark/queries.json \
  --models arctic,nomic,bge,minilm
```

**Output:**
```
Running accuracy benchmarks...

snowflake/arctic-embed-m:
  Top-5 Recall: 87.2% ✓
  Top-1 Recall: 73.5%
  Avg Latency: 35ms
  Memory: 3.5GB

nomic-embed-text-v1.5:
  Top-5 Recall: 86.8% ✓
  Top-1 Recall: 72.1%
  Avg Latency: 41.9ms
  Memory: 4.8GB

bge-small-en-v1.5:
  Top-5 Recall: 84.3% ✓
  Top-1 Recall: 69.2%
  Avg Latency: 22.5ms
  Memory: 2.1GB

all-MiniLM-L6-v2:
  Top-5 Recall: 78.4% ⚠️
  Top-1 Recall: 61.8%
  Avg Latency: 14.7ms
  Memory: 1.2GB

Recommendation: snowflake/arctic-embed-m (highest accuracy)
```

**Implementation:**
```python
# src/semvecmem/cli/benchmark_cmd.py

def run_accuracy_benchmark(model_name, corpus_path, queries_path):
    """Run accuracy benchmark on test corpus."""

    # 1. Ingest corpus with model
    ingest_corpus(corpus_path, model_name)

    # 2. Load queries with ground truth
    queries = load_queries(queries_path)

    # 3. Run each query, compare with ground truth
    top5_hits = 0
    top1_hits = 0

    for query in queries:
        results = recall_memory(query['query'], top_k=5)

        # Check if relevant chunks in top-5
        relevant_in_top5 = any(
            chunk_id in [r['chunk_id'] for r in results]
            for chunk_id in query['relevant_chunks']
        )

        if relevant_in_top5:
            top5_hits += 1

        if results[0]['chunk_id'] in query['relevant_chunks']:
            top1_hits += 1

    top5_recall = (top5_hits / len(queries)) * 100
    top1_recall = (top1_hits / len(queries)) * 100

    return {
        "top5_recall": top5_recall,
        "top1_recall": top1_recall
    }
```

**Effort:** +1 day (corpus curation + benchmark implementation)

---

**Phase 3 Total:** 4 days

**Deliverables:**
- [ ] Migration tool (working)
- [ ] Benchmark suite (validates accuracy claims)
- [ ] Enhanced error handling
- [ ] Test coverage >80%
- [ ] All original Phase 3 tasks

---

### Phase 4: Polish & Release (1 day) - **NEW PHASE**

**Tasks:**
- [ ] Final integration testing
- [ ] Performance profiling (identify bottlenecks)
- [ ] Documentation review (README, API docs, troubleshooting)
- [ ] GitHub repo cleanup (labels, milestones, issues)
- [ ] Release v1.0 tag

**Validation Criteria:**
- [ ] All success metrics met
- [ ] No critical bugs in issue tracker
- [ ] CI pipeline passing
- [ ] Documentation complete

**Effort:** 1 day

---

## Updated Timeline Summary

| Phase | Original | Updated | Delta | Reason |
|-------|----------|---------|-------|--------|
| Phase 1: Foundation | 2.5 days | **3.5 days** | +1 day | Multi-collection + validation |
| Phase 2: Core | 2 days | **2.5 days** | +0.5 days | Concurrency tests |
| Phase 3: CLI & Tools | 2.5 days | **4 days** | +1.5 days | Migration tool + benchmarks |
| Phase 4: Polish | - | **1 day** | +1 day | Final testing + release |
| **Total** | **7 days** | **11 days** | **+4 days** | **Critical fixes** |

**Realistic Estimate: 10-11 days (80-88 hours)**

---

## Architectural Decisions

### Decision #1: Multi-Collection Strategy ✅ APPROVED

**Strategy:** Dimension-based collections
```yaml
collections:
  semvecmem_384d   # BGE + MiniLM
  semvecmem_768d   # Nomic
  semvecmem_1024d  # Arctic
```

**Rationale:**
- Prevents dimension mismatch errors
- Enables seamless model switching
- Allows hybrid queries (future enhancement)

---

### Decision #2: Simplified Fallback Chain ✅ APPROVED

**Strategy:** 2-tier fallback (Arctic → MiniLM)
```yaml
embedder: snowflake/arctic-embed-m
fallback:
  enabled: true
  model: all-MiniLM-L6-v2
```

**Rationale:**
- Arctic (87%) or MiniLM (78.1%) - clear binary choice
- Reduces complexity significantly
- MiniLM is smallest (most reliable fallback)

**Alternative Models:** Nomic/BGE remain user-selectable (not automatic fallback)

---

### Decision #3: Deterministic Chunk IDs ✅ APPROVED

**Strategy:** Content-based hashing
```python
chunk_id = hashlib.sha256(
    json.dumps({"content": content, "lang": lang}, sort_keys=True).encode()
).hexdigest()
```

**Rationale:**
- Same content → same ID → upsert (prevents duplicates)
- Concurrent-safe
- Reproducible for debugging

---

### Decision #4: Migration Tool in Phase 3 ✅ APPROVED

**Rationale:**
- Required for usability (not optional)
- Users will switch models
- No alternative for dimension mismatch

**Move from:** Phase 4 (optional)
**Move to:** Phase 3 (required)

---

### Decision #5: Benchmark Suite Required ✅ APPROVED

**Rationale:**
- Validates 87% accuracy claim
- Builds user confidence
- Essential for scientific rigor

**Move from:** "Nice-to-have"
**Move to:** Required (Phase 3)

---

## Updated Success Metrics

| Metric | Target | How Validated | Phase |
|--------|--------|---------------|-------|
| Retrieval Accuracy (Top-5) | >85% (target: 87%) | Benchmark suite | Phase 3 |
| Query Latency (avg) | <500ms | Latency tests | Phase 3 |
| Query Latency (p95) | <500ms | Latency tests | Phase 3 |
| Token Overhead | <5% | MCP payload measurement | Phase 2 |
| Code Coverage | >80% | pytest-cov | Phase 3 |
| Model Switching | Zero-code | Integration test | Phase 3 |
| Concurrent Safety | No corruption | Concurrency tests | Phase 2 |
| Migration Success | 100% chunks | Migration tool tests | Phase 3 |

---

## Risk Mitigation

### Risk #1: Timeline Overrun

**Mitigation:**
- Set realistic expectations (10-11 days)
- Prioritize Phase 1 critical items
- Defer non-critical features to v1.1

### Risk #2: CodeIndex Adaptation Difficulty

**Mitigation:**
- Verify CodeIndex access before Phase 1
- Review chunker.py early
- Backup plan: Implement TreeSitter chunker from scratch (+1 day)

### Risk #3: Benchmark Corpus Quality

**Mitigation:**
- Curate corpus in parallel with Phase 1-2
- Use real-world codebases (not synthetic)
- Get user feedback on query relevance

### Risk #4: Multi-Collection Complexity

**Mitigation:**
- Implement collection router early (Phase 1)
- Comprehensive unit tests
- Clear error messages for users

---

## Conclusion

**Status:** ✅ **APPROVED FOR IMPLEMENTATION**

**Critical Path:**
1. Implement multi-collection strategy (Phase 1)
2. Build migration tool (Phase 3)
3. Validate with benchmarks (Phase 3)

**Confidence Level:** HIGH (with updated timeline)

**Timeline:** 10-11 days (vs original 7 days)

**Risk Level:** MEDIUM → LOW (after architectural fixes)

**Next Steps:**
1. Begin Phase 1 with multi-collection implementation
2. Curate benchmark corpus in parallel
3. Regular check-ins after each phase

---

**Document Version:** 1.3
**Last Updated:** 2025-10-05
**Based On:** ARCHITECTURE_REVIEW.md critical findings
