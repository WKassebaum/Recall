"""Tests for UnifiedVectorStore filtering methods."""

import numpy as np
import pytest
from unittest.mock import MagicMock

from recall.core.store import Chunk, DimensionMismatchError, SearchResult, UnifiedVectorStore


class TestApplyFilter:
    """Test metadata filtering."""

    @pytest.fixture
    def store_with_embedder(self):
        """Create store with mock embedder."""
        store = UnifiedVectorStore()
        embedder = MagicMock()
        embedder.dimension = 384
        embedder.name = "test-embedder"
        embedder.encode.return_value = np.array([0.1] * 384, dtype=np.float32)
        store.set_embedder(embedder)
        return store

    def test_filter_single_key(self, store_with_embedder):
        """Verify single key filter works."""
        chunks = [
            Chunk(content="chunk1", metadata={"session_id": "test"}),
            Chunk(content="chunk2", metadata={"session_id": "other"}),
            Chunk(content="chunk3", metadata={"session_id": "test"}),
        ]

        result = store_with_embedder._apply_filter(chunks, {"session_id": "test"})

        assert len(result) == 2
        assert all(c.metadata["session_id"] == "test" for c in result)

    def test_filter_multiple_keys(self, store_with_embedder):
        """Verify multiple key filter requires all to match."""
        chunks = [
            Chunk(content="c1", metadata={"session_id": "test", "type": "code"}),
            Chunk(content="c2", metadata={"session_id": "test", "type": "text"}),
            Chunk(content="c3", metadata={"session_id": "other", "type": "code"}),
        ]

        result = store_with_embedder._apply_filter(chunks, {"session_id": "test", "type": "code"})

        assert len(result) == 1
        assert result[0].content == "c1"

    def test_filter_no_matches(self, store_with_embedder):
        """Verify empty result when no matches."""
        chunks = [
            Chunk(content="chunk1", metadata={"session_id": "abc"}),
            Chunk(content="chunk2", metadata={"session_id": "def"}),
        ]

        result = store_with_embedder._apply_filter(chunks, {"session_id": "xyz"})

        assert len(result) == 0


class TestApplyTimeFilter:
    """Test temporal filtering."""

    @pytest.fixture
    def store_with_embedder(self):
        """Create store with mock embedder."""
        store = UnifiedVectorStore()
        embedder = MagicMock()
        embedder.dimension = 384
        embedder.name = "test-embedder"
        embedder.encode.return_value = np.array([0.1] * 384, dtype=np.float32)
        store.set_embedder(embedder)
        return store

    def test_time_filter_range(self, store_with_embedder):
        """Verify time range filtering works."""
        chunks = [
            Chunk(content="c1", metadata={"ingested_at": "2025-10-01T12:00:00+00:00"}),
            Chunk(content="c2", metadata={"ingested_at": "2025-10-05T12:00:00+00:00"}),
            Chunk(content="c3", metadata={"ingested_at": "2025-10-10T12:00:00+00:00"}),
            Chunk(content="c4", metadata={"ingested_at": "2025-10-15T12:00:00+00:00"}),
        ]

        # Use timezone-aware date strings
        result = store_with_embedder._apply_time_filter(
            chunks, ("2025-10-04T00:00:00+00:00", "2025-10-12T00:00:00+00:00")
        )

        assert len(result) == 2
        assert result[0].content == "c2"
        assert result[1].content == "c3"

    def test_time_filter_open_ended(self, store_with_embedder):
        """Verify open-ended time range (no end date)."""
        chunks = [
            Chunk(content="c1", metadata={"ingested_at": "2025-10-01T12:00:00+00:00"}),
            Chunk(content="c2", metadata={"ingested_at": "2025-10-10T12:00:00+00:00"}),
            Chunk(content="c3", metadata={"ingested_at": "2025-10-20T12:00:00+00:00"}),
        ]

        result = store_with_embedder._apply_time_filter(chunks, ("2025-10-05T00:00:00+00:00", None))

        assert len(result) == 2
        assert result[0].content == "c2"
        assert result[1].content == "c3"

    def test_time_filter_skips_missing_timestamp(self, store_with_embedder):
        """Verify chunks without timestamps are skipped."""
        chunks = [
            Chunk(content="c1", metadata={"ingested_at": "2025-10-10T12:00:00+00:00"}),
            Chunk(content="c2", metadata={}),  # No timestamp
            Chunk(content="c3", metadata={"session_id": "test"}),  # No timestamp
        ]

        result = store_with_embedder._apply_time_filter(
            chunks, ("2025-10-01T00:00:00+00:00", "2025-10-20T00:00:00+00:00")
        )

        assert len(result) == 1
        assert result[0].content == "c1"

    def test_time_filter_handles_z_suffix(self, store_with_embedder):
        """Verify Z suffix in timestamps is handled."""
        chunks = [
            Chunk(content="c1", metadata={"ingested_at": "2025-10-10T12:00:00Z"}),
        ]

        result = store_with_embedder._apply_time_filter(
            chunks, ("2025-10-01T00:00:00+00:00", "2025-10-20T00:00:00+00:00")
        )

        assert len(result) == 1


class TestApplyEventTypeFilter:
    """Test event type filtering."""

    @pytest.fixture
    def store_with_embedder(self):
        """Create store with mock embedder."""
        store = UnifiedVectorStore()
        embedder = MagicMock()
        embedder.dimension = 384
        embedder.name = "test-embedder"
        embedder.encode.return_value = np.array([0.1] * 384, dtype=np.float32)
        store.set_embedder(embedder)
        return store

    def test_event_type_single(self, store_with_embedder):
        """Verify single event type filter."""
        chunks = [
            Chunk(content="c1", metadata={"event_type": "decision"}),
            Chunk(content="c2", metadata={"event_type": "discovery"}),
            Chunk(content="c3", metadata={"event_type": "decision"}),
        ]

        result = store_with_embedder._apply_event_type_filter(chunks, ["decision"])

        assert len(result) == 2

    def test_event_type_multiple(self, store_with_embedder):
        """Verify multiple event types filter."""
        chunks = [
            Chunk(content="c1", metadata={"event_type": "decision"}),
            Chunk(content="c2", metadata={"event_type": "discovery"}),
            Chunk(content="c3", metadata={"event_type": "milestone"}),
            Chunk(content="c4", metadata={"event_type": "error"}),
        ]

        result = store_with_embedder._apply_event_type_filter(chunks, ["decision", "milestone"])

        assert len(result) == 2
        assert result[0].content == "c1"
        assert result[1].content == "c3"

    def test_event_type_no_matches(self, store_with_embedder):
        """Verify empty result when no event type matches."""
        chunks = [
            Chunk(content="c1", metadata={"event_type": "decision"}),
            Chunk(content="c2", metadata={"event_type": "discovery"}),
        ]

        result = store_with_embedder._apply_event_type_filter(chunks, ["error"])

        assert len(result) == 0


class TestSortChronologically:
    """Test chronological sorting."""

    @pytest.fixture
    def store_with_embedder(self):
        """Create store with mock embedder."""
        store = UnifiedVectorStore()
        embedder = MagicMock()
        embedder.dimension = 384
        embedder.name = "test-embedder"
        embedder.encode.return_value = np.array([0.1] * 384, dtype=np.float32)
        store.set_embedder(embedder)
        return store

    def test_sort_by_timestamp(self, store_with_embedder):
        """Verify sorting by ingested_at timestamp."""
        chunks = [
            Chunk(content="c3", metadata={"ingested_at": "2025-10-15T12:00:00+00:00"}),
            Chunk(content="c1", metadata={"ingested_at": "2025-10-01T12:00:00+00:00"}),
            Chunk(content="c2", metadata={"ingested_at": "2025-10-10T12:00:00+00:00"}),
        ]
        # Add embeddings
        for chunk in chunks:
            chunk.embedding = np.array([0.1] * 384, dtype=np.float32)

        result = store_with_embedder._sort_chronologically(chunks, top_k=10)

        assert len(result) == 3
        assert result[0].content == "c1"
        assert result[1].content == "c2"
        assert result[2].content == "c3"

    def test_sort_respects_top_k(self, store_with_embedder):
        """Verify top_k limit is respected."""
        chunks = [
            Chunk(content=f"c{i}", metadata={"ingested_at": f"2025-10-{i+1:02}T12:00:00+00:00"})
            for i in range(10)
        ]
        for chunk in chunks:
            chunk.embedding = np.array([0.1] * 384, dtype=np.float32)

        result = store_with_embedder._sort_chronologically(chunks, top_k=3)

        assert len(result) == 3

    def test_sort_score_is_zero(self, store_with_embedder):
        """Verify chronological results have score=0."""
        chunks = [
            Chunk(content="c1", metadata={"ingested_at": "2025-10-01T12:00:00+00:00"}),
        ]
        chunks[0].embedding = np.array([0.1] * 384, dtype=np.float32)

        result = store_with_embedder._sort_chronologically(chunks, top_k=10)

        assert result[0].score == 0.0


class TestDimensionMismatch:
    """Test dimension verification."""

    def test_verify_query_dimension_mismatch(self):
        """Verify query dimension mismatch raises error."""
        store = UnifiedVectorStore()
        embedder = MagicMock()
        embedder.dimension = 384
        embedder.name = "test-embedder"
        store.set_embedder(embedder)

        wrong_dim_vector = np.array([0.1] * 768, dtype=np.float32)

        with pytest.raises(DimensionMismatchError) as exc_info:
            store._verify_query_dimension(wrong_dim_vector)

        assert "Expected 384D" in str(exc_info.value)
        assert "got 768D" in str(exc_info.value)


class TestSearchModes:
    """Test different search retrieval modes."""

    @pytest.fixture
    def store_with_data(self):
        """Create store with test data."""
        store = UnifiedVectorStore()
        embedder = MagicMock()
        embedder.dimension = 384
        embedder.name = "test-embedder"
        embedder.encode.return_value = np.array([0.1] * 384, dtype=np.float32)
        store.set_embedder(embedder)

        # Add some chunks
        for i in range(5):
            chunk = Chunk(
                content=f"content {i}",
                metadata={
                    "session_id": "test",
                    "ingested_at": f"2025-10-{i+1:02}T12:00:00+00:00",
                    "event_type": "decision" if i % 2 == 0 else "discovery",
                },
            )
            chunk.embedding = np.array([0.1 + i * 0.01] * 384, dtype=np.float32)
            store._storage[store.active_collection].append(chunk)

        return store

    def test_semantic_requires_query(self, store_with_data):
        """Verify semantic mode requires query."""
        with pytest.raises(ValueError, match="Semantic mode requires query"):
            store_with_data.search(retrieval_mode="semantic")

    def test_invalid_mode_raises_error(self, store_with_data):
        """Verify invalid retrieval mode raises error."""
        with pytest.raises(ValueError, match="Invalid retrieval_mode"):
            store_with_data.search(query="test", retrieval_mode="invalid")

    def test_chronological_mode(self, store_with_data):
        """Verify chronological mode returns time-ordered results."""
        results = store_with_data.search(retrieval_mode="chronological", top_k=10)

        assert len(results) == 5
        # Should be sorted oldest to newest
        assert results[0].content == "content 0"
        assert results[-1].content == "content 4"

    def test_hybrid_mode_with_filters(self, store_with_data):
        """Verify hybrid mode applies filters."""
        results = store_with_data.search(
            query="test",
            retrieval_mode="hybrid",
            event_types=["decision"],
            top_k=10,
        )

        # Only decision events (0, 2, 4)
        assert len(results) == 3


class TestCount:
    """Test count method."""

    def test_count_no_collection(self):
        """Verify count returns 0 when no collection set."""
        store = UnifiedVectorStore()
        assert store.count() == 0

    def test_count_in_memory(self):
        """Verify count works with in-memory storage."""
        store = UnifiedVectorStore()
        embedder = MagicMock()
        embedder.dimension = 384
        embedder.name = "test-embedder"
        embedder.encode.return_value = np.array([0.1] * 384, dtype=np.float32)
        store.set_embedder(embedder)

        # Add chunks
        store.add("content 1")
        store.add("content 2")

        assert store.count() == 2

    def test_count_with_backend(self):
        """Verify count uses backend when available."""
        mock_backend = MagicMock()
        mock_backend.count.return_value = 42

        store = UnifiedVectorStore(backend=mock_backend)
        embedder = MagicMock()
        embedder.dimension = 384
        embedder.name = "test-embedder"
        store.set_embedder(embedder)

        assert store.count() == 42
        mock_backend.count.assert_called_with("recall_384d")
