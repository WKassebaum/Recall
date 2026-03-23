"""Integration test for hybrid search (dense + sparse vectors).

Tests that BM25 sparse vectors improve retrieval for domain-specific
content by combining keyword matching with semantic similarity.
"""

import numpy as np
import pytest

from recall.backends.qdrant import QdrantBackend
from recall.core.store import Chunk, UnifiedVectorStore
from recall.embedders.mock import MockEmbedder
from recall.sparse.encoder import SparseEncoder


@pytest.fixture
def tmp_qdrant(tmp_path):
    """Create a temporary embedded Qdrant backend."""
    qdrant_path = str(tmp_path / "qdrant_hybrid_test")
    backend = QdrantBackend(path=qdrant_path)
    yield backend


@pytest.fixture
def hybrid_store(tmp_qdrant):
    """Create a store with both dense embedder and sparse encoder."""
    store = UnifiedVectorStore(backend=tmp_qdrant)
    store.set_sparse_encoder(SparseEncoder())
    embedder = MockEmbedder(dimension=384, model_name="mock-384")
    store.set_embedder(embedder)
    return store


class TestHybridSearchIntegration:
    """Integration tests for hybrid keyword + semantic search."""

    def test_new_collection_uses_named_vectors(self, tmp_qdrant):
        """Verify new collections are created with named vector schema."""
        store = UnifiedVectorStore(backend=tmp_qdrant)
        store.set_sparse_encoder(SparseEncoder())
        embedder = MockEmbedder(dimension=384, model_name="mock-384")
        store.set_embedder(embedder)

        assert not tmp_qdrant.is_legacy_collection("recall_384d")

    def test_ingest_stores_sparse_vectors(self, hybrid_store):
        """Verify ingested chunks get both dense and sparse vectors."""
        hybrid_store.add(
            content="CBS pathway molybdenum urea cycle ammonia dopamine",
            metadata={"session_id": "test"},
        )

        assert hybrid_store.count() == 1

        # Scroll and verify chunk has content
        chunks = hybrid_store.scroll()
        assert len(chunks) == 1
        assert chunks[0].embedding is not None
        assert len(chunks[0].embedding) == 384

    def test_hybrid_search_basic(self, hybrid_store):
        """Verify hybrid search returns results."""
        hybrid_store.add(content="CBS pathway molybdenum urea cycle")
        hybrid_store.add(content="Plans of treatment follow-up visit")
        hybrid_store.add(content="General lab results CBC panel")

        results = hybrid_store.search(
            query="health data",
            keywords="CBS,molybdenum",
            top_k=10,
        )

        assert len(results) > 0

    def test_hybrid_search_boosts_keyword_matches(self, hybrid_store):
        """Verify hybrid search ranks keyword-matching chunks higher."""
        # Add domain-specific chunk and generic chunks
        hybrid_store.add(
            content="CBS pathway upregulated due to molybdenum deficiency affects urea cycle",
            metadata={"type": "specific"},
        )
        for i in range(10):
            hybrid_store.add(
                content=f"General clinical note number {i} with routine patient data",
                metadata={"type": "generic"},
            )

        # Hybrid search with keywords should find the CBS chunk
        results = hybrid_store.search(
            query="health",
            keywords="CBS,molybdenum",
            top_k=5,
        )

        assert len(results) > 0
        # The CBS chunk should appear in results
        contents = [r.content for r in results]
        assert any("CBS" in c for c in contents)

    def test_dense_only_search_still_works(self, hybrid_store):
        """Verify search without keywords uses dense-only path."""
        hybrid_store.add(content="Test chunk one")
        hybrid_store.add(content="Test chunk two")

        results = hybrid_store.search(query="test", top_k=5)
        assert len(results) == 2

    def test_hybrid_search_with_filters(self, hybrid_store):
        """Verify hybrid search works with metadata filters."""
        hybrid_store.add(
            content="CBS pathway in session A",
            metadata={"session_id": "session-a"},
        )
        hybrid_store.add(
            content="CBS pathway in session B",
            metadata={"session_id": "session-b"},
        )

        results = hybrid_store.search(
            query="pathway",
            keywords="CBS",
            filter={"session_id": "session-a"},
            top_k=5,
        )

        for r in results:
            assert r.metadata.get("session_id") == "session-a"

    def test_many_chunks_with_keywords(self, hybrid_store):
        """Verify hybrid search works with larger corpus."""
        # Add 50 generic chunks
        for i in range(50):
            hybrid_store.add(content=f"Generic health record entry {i}")

        # Add specific domain chunk
        hybrid_store.add(content="ASTM A36 structural steel bolt torque specification")

        # Hybrid search for engineering term
        results = hybrid_store.search(
            query="engineering",
            keywords="ASTM,A36,bolt",
            top_k=5,
        )

        assert len(results) > 0
        contents = [r.content for r in results]
        assert any("ASTM" in c for c in contents)


class TestLegacyCompatibility:
    """Test backward compatibility with unnamed-vector collections."""

    def test_legacy_collection_dense_search_works(self, tmp_qdrant):
        """Verify legacy unnamed-vector collections still work for dense search."""
        from qdrant_client.models import VectorParams, Distance

        # Manually create an old-style unnamed-vector collection
        tmp_qdrant.client.create_collection(
            collection_name="recall_384d",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

        store = UnifiedVectorStore(backend=tmp_qdrant)
        store.set_sparse_encoder(SparseEncoder())
        embedder = MockEmbedder(dimension=384, model_name="mock-384")
        store.set_embedder(embedder)

        # Should detect legacy mode
        assert tmp_qdrant.is_legacy_collection("recall_384d")

        # Dense search should still work
        store.add(content="Test legacy content")
        results = store.search(query="test", top_k=5)
        assert len(results) == 1
        assert results[0].content == "Test legacy content"

    def test_legacy_hybrid_falls_back_to_dense(self, tmp_qdrant):
        """Verify hybrid search falls back to dense-only for legacy collections."""
        from qdrant_client.models import VectorParams, Distance

        tmp_qdrant.client.create_collection(
            collection_name="recall_384d",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

        store = UnifiedVectorStore(backend=tmp_qdrant)
        store.set_sparse_encoder(SparseEncoder())
        embedder = MockEmbedder(dimension=384, model_name="mock-384")
        store.set_embedder(embedder)

        store.add(content="Legacy content with keywords test")

        # Hybrid search should work (falls back to dense)
        results = store.search(query="test", keywords="keywords", top_k=5)
        assert len(results) == 1
