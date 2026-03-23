"""
Waypoint 1: POC Unified Vector Store validation tests.

Tests basic functionality of UnifiedVectorStore with dimension verification.
"""

import pytest
import numpy as np

from recall.core.store import (
    UnifiedVectorStore,
    Chunk,
    SearchResult,
    DimensionMismatchError,
)
from recall.embedders.mock import MockEmbedder


class TestUnifiedVectorStorePOC:
    """POC tests for UnifiedVectorStore."""

    def test_set_embedder_routes_to_correct_collection(self) -> None:
        """POC: Verify embedder routing to dimension-specific collection."""
        store = UnifiedVectorStore()

        # Set 384D embedder
        embedder_384 = MockEmbedder(dimension=384, model_name="mock-384")
        store.set_embedder(embedder_384)

        assert store.active_dimension == 384
        assert store.active_collection == "recall_384d"

        # Switch to 1024D embedder
        embedder_1024 = MockEmbedder(dimension=1024, model_name="mock-1024")
        store.set_embedder(embedder_1024)

        assert store.active_dimension == 1024
        assert store.active_collection == "recall_1024d"

    def test_dimension_verification_on_upsert(self) -> None:
        """POC: Verify dimension mismatch caught on upsert."""
        store = UnifiedVectorStore()
        store.set_embedder(MockEmbedder(dimension=384, model_name="mock-384"))

        # Try to insert chunk with wrong dimension
        chunk = Chunk(content="test", embedding=np.random.rand(1024).astype(np.float32))

        with pytest.raises(DimensionMismatchError) as exc_info:
            store.upsert([chunk])

        # Verify error message is helpful
        error_msg = str(exc_info.value)
        assert "Expected 384D" in error_msg
        assert "got 1024D" in error_msg
        assert "migrate-embeddings" in error_msg

    def test_dimension_verification_on_search(self) -> None:
        """POC: Verify dimension check on search queries."""
        store = UnifiedVectorStore()

        # Set 384D embedder
        embedder = MockEmbedder(dimension=384, model_name="mock-384")
        store.set_embedder(embedder)

        # Search should work with correct dimension
        results = store.search("test query")
        assert isinstance(results, list)

    def test_no_embedder_set_error(self) -> None:
        """POC: Verify error if no embedder set."""
        store = UnifiedVectorStore()

        with pytest.raises(ValueError, match="No active embedder"):
            store.search("test")

        with pytest.raises(ValueError, match="No active embedder"):
            store.upsert([Chunk(content="test")])

    def test_basic_upsert_and_search(self) -> None:
        """POC: Verify basic upsert and search functionality."""
        store = UnifiedVectorStore()
        embedder = MockEmbedder(dimension=384, model_name="mock-384")
        store.set_embedder(embedder)

        # Upsert chunks
        chunks = [
            Chunk(content="Python authentication code"),
            Chunk(content="JavaScript routing logic"),
            Chunk(content="Database connection pooling"),
        ]
        store.upsert(chunks)

        # Verify chunks stored
        assert store.count() == 3

        # Search
        results = store.search("authentication", top_k=2)
        assert len(results) <= 2
        # Verify results are SearchResult instances
        for result in results:
            assert isinstance(result, SearchResult)
            assert hasattr(result, "content")
            assert hasattr(result, "score")
            assert hasattr(result, "chunk_id")
            assert hasattr(result, "metadata")

    def test_deterministic_chunk_ids(self) -> None:
        """POC: Verify content hash generates deterministic IDs."""
        chunk1 = Chunk(content="identical content")
        chunk2 = Chunk(content="identical content")

        assert chunk1.id == chunk2.id

    def test_chunk_replacement_on_duplicate_id(self) -> None:
        """POC: Verify chunks with same ID are replaced, not duplicated."""
        store = UnifiedVectorStore()
        embedder = MockEmbedder(dimension=384)
        store.set_embedder(embedder)

        # Insert same content twice
        chunk1 = Chunk(content="duplicate content")
        chunk2 = Chunk(content="duplicate content")

        store.upsert([chunk1])
        assert store.count() == 1

        store.upsert([chunk2])
        assert store.count() == 1  # Should still be 1, not 2

    def test_add_with_metadata(self) -> None:
        """Enhanced API: Verify add() method with metadata."""
        store = UnifiedVectorStore()
        embedder = MockEmbedder(dimension=384)
        store.set_embedder(embedder)

        # Add chunk with metadata
        chunk_id = store.add(
            content="User session data",
            metadata={"session_id": "abc123", "user": "test_user"},
        )

        assert isinstance(chunk_id, str)
        assert len(chunk_id) > 0
        assert store.count() == 1

    def test_search_with_filtering(self) -> None:
        """Enhanced API: Verify search with metadata filtering."""
        store = UnifiedVectorStore()
        embedder = MockEmbedder(dimension=384)
        store.set_embedder(embedder)

        # Add chunks with different sessions
        store.add(
            content="Session A: Redis configuration",
            metadata={"session_id": "session-a"},
        )
        store.add(
            content="Session B: PostgreSQL setup",
            metadata={"session_id": "session-b"},
        )
        store.add(
            content="Session A: Authentication logic",
            metadata={"session_id": "session-a"},
        )

        # Search without filter - should return all relevant chunks
        all_results = store.search("database", top_k=10)
        assert len(all_results) >= 2

        # Search with filter - should only return session-a chunks
        filtered_results = store.search("configuration", filter={"session_id": "session-a"})
        for result in filtered_results:
            assert result.metadata.get("session_id") == "session-a"

    def test_search_result_has_scores(self) -> None:
        """Enhanced API: Verify SearchResult includes similarity scores."""
        store = UnifiedVectorStore()
        embedder = MockEmbedder(dimension=384)
        store.set_embedder(embedder)

        store.add(content="Python programming language")
        store.add(content="JavaScript web development")

        results = store.search("Python code")

        for result in results:
            assert isinstance(result.score, float)
            assert 0.0 <= result.score <= 1.0  # Cosine similarity range


class TestUnifiedVectorStoreScroll:
    """Tests for UnifiedVectorStore.scroll() method."""

    def test_scroll_returns_all_chunks(self) -> None:
        """Verify scroll() returns all chunks without a query."""
        store = UnifiedVectorStore()
        embedder = MockEmbedder(dimension=384, model_name="mock-384")
        store.set_embedder(embedder)

        # Add several chunks
        for i in range(5):
            store.add(content=f"Chunk content {i}", metadata={"index": str(i)})

        chunks = store.scroll()

        assert len(chunks) == 5
        contents = {c.content for c in chunks}
        for i in range(5):
            assert f"Chunk content {i}" in contents

    def test_scroll_no_embedder_error(self) -> None:
        """Verify scroll() raises if no embedder set."""
        store = UnifiedVectorStore()

        with pytest.raises(ValueError, match="No active embedder"):
            store.scroll()

    def test_scroll_empty_collection(self) -> None:
        """Verify scroll() returns empty list for empty collection."""
        store = UnifiedVectorStore()
        embedder = MockEmbedder(dimension=384, model_name="mock-384")
        store.set_embedder(embedder)

        chunks = store.scroll()
        assert chunks == []


class TestMockEmbedder:
    """Tests for MockEmbedder."""

    def test_deterministic_embeddings(self) -> None:
        """Verify MockEmbedder generates deterministic embeddings."""
        embedder = MockEmbedder(dimension=384)

        emb1 = embedder.encode("test content")
        emb2 = embedder.encode("test content")

        assert np.allclose(emb1, emb2)

    def test_correct_dimension(self) -> None:
        """Verify MockEmbedder produces correct dimension."""
        for dim in [384, 768, 1024]:
            embedder = MockEmbedder(dimension=dim)
            embedding = embedder.encode("test")

            assert len(embedding) == dim
            assert embedder.dimension == dim

    def test_normalized_embeddings(self) -> None:
        """Verify embeddings are normalized (unit length)."""
        embedder = MockEmbedder(dimension=384)
        embedding = embedder.encode("test")

        norm = np.linalg.norm(embedding)
        assert np.isclose(norm, 1.0, atol=1e-6)
