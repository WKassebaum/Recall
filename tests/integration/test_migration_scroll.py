"""Integration test for migration scroll fix.

Tests that UnifiedVectorStore.scroll() correctly retrieves all chunks
from an embedded Qdrant instance, including pagination across multiple pages.
This validates the fix for: Migration tool fails with empty query (issue #2).
"""

import shutil
import tempfile

import numpy as np
import pytest

from recall.backends.qdrant import QdrantBackend
from recall.core.store import Chunk, UnifiedVectorStore
from recall.embedders.mock import MockEmbedder


@pytest.fixture
def tmp_qdrant(tmp_path):
    """Create a temporary embedded Qdrant backend."""
    qdrant_path = str(tmp_path / "qdrant_test")
    backend = QdrantBackend(path=qdrant_path)
    yield backend
    # Cleanup handled by tmp_path


class TestScrollIntegration:
    """Integration tests for scroll-based chunk retrieval."""

    def test_scroll_retrieves_all_chunks(self, tmp_qdrant):
        """Verify scroll() returns all chunks from embedded Qdrant."""
        store = UnifiedVectorStore(backend=tmp_qdrant)
        embedder = MockEmbedder(dimension=384, model_name="mock-384")
        store.set_embedder(embedder)

        # Insert 25 chunks (more than a single scroll page of 10)
        for i in range(25):
            store.add(
                content=f"Health record chunk {i}: patient data",
                metadata={"session_id": "test-session", "index": str(i)},
            )

        assert store.count() == 25

        # scroll() should return all 25 chunks
        chunks = store.scroll()
        assert len(chunks) == 25

        # Verify all chunks are present
        contents = {c.content for c in chunks}
        for i in range(25):
            assert f"Health record chunk {i}: patient data" in contents

    def test_scroll_preserves_metadata(self, tmp_qdrant):
        """Verify scroll() preserves chunk metadata."""
        store = UnifiedVectorStore(backend=tmp_qdrant)
        embedder = MockEmbedder(dimension=384, model_name="mock-384")
        store.set_embedder(embedder)

        store.add(
            content="CBS pathway molybdenum urea cycle insight",
            metadata={
                "session_id": "health-records",
                "event_type": "discovery",
                "tags": "molybdenum,CBS-pathway,urea-cycle",
            },
        )

        chunks = store.scroll()
        assert len(chunks) == 1
        assert chunks[0].metadata["session_id"] == "health-records"
        assert chunks[0].metadata["event_type"] == "discovery"
        assert "molybdenum" in chunks[0].metadata["tags"]

    def test_scroll_empty_collection(self, tmp_qdrant):
        """Verify scroll() on empty collection returns empty list."""
        store = UnifiedVectorStore(backend=tmp_qdrant)
        embedder = MockEmbedder(dimension=384, model_name="mock-384")
        store.set_embedder(embedder)

        chunks = store.scroll()
        assert chunks == []

    def test_scroll_returns_embeddings(self, tmp_qdrant):
        """Verify scroll() returns chunks with their embeddings."""
        store = UnifiedVectorStore(backend=tmp_qdrant)
        embedder = MockEmbedder(dimension=384, model_name="mock-384")
        store.set_embedder(embedder)

        store.add(content="Test chunk with embedding")

        chunks = store.scroll()
        assert len(chunks) == 1
        assert chunks[0].embedding is not None
        assert len(chunks[0].embedding) == 384

    def test_scroll_large_collection_pagination(self, tmp_qdrant):
        """Verify scroll() paginates correctly for larger collections."""
        store = UnifiedVectorStore(backend=tmp_qdrant)
        embedder = MockEmbedder(dimension=384, model_name="mock-384")
        store.set_embedder(embedder)

        # Insert 150 chunks to force multiple scroll pages
        chunk_count = 150
        for i in range(chunk_count):
            store.add(
                content=f"Chunk number {i:04d}",
                metadata={"session_id": "pagination-test"},
            )

        assert store.count() == chunk_count

        chunks = store.scroll()
        assert len(chunks) == chunk_count

        # Verify no duplicates
        chunk_ids = [c.id for c in chunks]
        assert len(set(chunk_ids)) == chunk_count
