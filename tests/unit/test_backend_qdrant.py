"""Tests for the Qdrant backend.

Tests QdrantBackend initialization and operations.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from recall.backends.qdrant import QdrantBackend
from recall.core.store import Chunk


class TestQdrantBackendInit:
    """Test QdrantBackend initialization."""

    def test_init_embedded_mode(self, tmp_path):
        """Verify embedded mode initialization."""
        with patch("recall.backends.qdrant.QdrantClient") as mock_client:
            mock_client.return_value = MagicMock()

            backend = QdrantBackend(path=str(tmp_path / "qdrant"))

            assert backend.mode == "embedded"
            assert backend.path == str(tmp_path / "qdrant")
            assert backend.host is None
            assert backend.port is None

    def test_init_network_mode(self):
        """Verify network mode initialization."""
        with patch("recall.backends.qdrant.QdrantClient") as mock_client:
            mock_client.return_value = MagicMock()

            backend = QdrantBackend(host="localhost", port=6337)

            assert backend.mode == "network"
            assert backend.host == "localhost"
            assert backend.port == 6337
            assert backend.path is None

    def test_init_requires_path_or_host(self):
        """Verify error when neither path nor host provided."""
        with pytest.raises(ValueError, match="Must provide either 'path'"):
            QdrantBackend()

    def test_init_blocking_io_error(self, tmp_path):
        """Verify helpful error on embedded mode conflict."""
        with patch("recall.backends.qdrant.QdrantClient") as mock_client:
            mock_client.side_effect = BlockingIOError("Database locked")

            with pytest.raises(BlockingIOError) as exc_info:
                QdrantBackend(path=str(tmp_path / "qdrant"))

            assert "already in use by another process" in str(exc_info.value)
            assert "Multiple Claude Code windows" in str(exc_info.value)


class TestQdrantBackendHashToUUID:
    """Test hash to UUID conversion."""

    def test_hash_to_uuid_deterministic(self):
        """Verify hash to UUID is deterministic."""
        hash_str = "abc123def456789012345678901234567890"
        uuid1 = QdrantBackend._hash_to_uuid(hash_str)
        uuid2 = QdrantBackend._hash_to_uuid(hash_str)

        assert uuid1 == uuid2

    def test_hash_to_uuid_valid_format(self):
        """Verify UUID format is valid."""
        hash_str = "abc123def456789012345678901234567890"
        uuid_str = QdrantBackend._hash_to_uuid(hash_str)

        # UUID format: 8-4-4-4-12
        parts = uuid_str.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12


class TestQdrantBackendHealthCheck:
    """Test health check functionality."""

    def test_health_check_success(self):
        """Verify health check success."""
        with patch("recall.backends.qdrant.QdrantClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get_collections.return_value = MagicMock(collections=[])
            mock_client.return_value = mock_instance

            backend = QdrantBackend(host="localhost", port=6333)
            result = backend.health_check()

            assert result is True
            mock_instance.get_collections.assert_called()

    def test_health_check_failure(self):
        """Verify health check failure."""
        with patch("recall.backends.qdrant.QdrantClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get_collections.side_effect = Exception("Connection refused")
            mock_client.return_value = mock_instance

            backend = QdrantBackend(host="localhost", port=6333)
            result = backend.health_check()

            assert result is False


class TestQdrantBackendEnsureCollection:
    """Test collection management."""

    def test_ensure_collection_creates_new_with_named_vectors(self):
        """Verify new collection uses named vectors."""
        with patch("recall.backends.qdrant.QdrantClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get_collections.return_value = MagicMock(collections=[])
            mock_client.return_value = mock_instance

            backend = QdrantBackend(host="localhost", port=6333)
            backend.ensure_collection("recall_384d", 384, sparse=True)

            mock_instance.create_collection.assert_called_once()
            call_kwargs = mock_instance.create_collection.call_args[1]
            assert call_kwargs["collection_name"] == "recall_384d"
            # Should use named vectors dict, not plain VectorParams
            assert isinstance(call_kwargs["vectors_config"], dict)
            assert "dense" in call_kwargs["vectors_config"]
            # Should have sparse config
            assert call_kwargs["sparse_vectors_config"] is not None

    def test_ensure_collection_creates_without_sparse(self):
        """Verify new collection without sparse flag omits sparse config."""
        with patch("recall.backends.qdrant.QdrantClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get_collections.return_value = MagicMock(collections=[])
            mock_client.return_value = mock_instance

            backend = QdrantBackend(host="localhost", port=6333)
            backend.ensure_collection("recall_384d", 384, sparse=False)

            call_kwargs = mock_instance.create_collection.call_args[1]
            assert call_kwargs["sparse_vectors_config"] is None

    def test_ensure_collection_detects_legacy(self):
        """Verify existing unnamed-vector collection enters legacy mode."""
        from qdrant_client.models import VectorParams

        with patch("recall.backends.qdrant.QdrantClient") as mock_client:
            mock_collection = MagicMock()
            mock_collection.name = "recall_384d"
            mock_instance = MagicMock()
            mock_instance.get_collections.return_value = MagicMock(collections=[mock_collection])
            # Simulate unnamed vectors
            mock_info = MagicMock()
            mock_info.config.params.vectors = VectorParams(size=384, distance="Cosine")
            mock_instance.get_collection.return_value = mock_info
            mock_client.return_value = mock_instance

            backend = QdrantBackend(host="localhost", port=6333)
            backend.ensure_collection("recall_384d", 384)

            assert backend.is_legacy_collection("recall_384d")
            mock_instance.create_collection.assert_not_called()

    def test_ensure_collection_named_not_legacy(self):
        """Verify existing named-vector collection is not legacy."""
        with patch("recall.backends.qdrant.QdrantClient") as mock_client:
            mock_collection = MagicMock()
            mock_collection.name = "recall_384d"
            mock_instance = MagicMock()
            mock_instance.get_collections.return_value = MagicMock(collections=[mock_collection])
            # Simulate named vectors (dict)
            mock_info = MagicMock()
            mock_info.config.params.vectors = {"dense": MagicMock()}
            mock_instance.get_collection.return_value = mock_info
            mock_client.return_value = mock_instance

            backend = QdrantBackend(host="localhost", port=6333)
            backend.ensure_collection("recall_384d", 384)

            assert not backend.is_legacy_collection("recall_384d")


class TestQdrantBackendOperations:
    """Test CRUD operations."""

    @pytest.fixture
    def mock_backend(self):
        """Create backend with mocked client."""
        with patch("recall.backends.qdrant.QdrantClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            backend = QdrantBackend(host="localhost", port=6333)
            backend._mock_instance = mock_instance
            yield backend

    def test_upsert_chunks(self, mock_backend):
        """Verify chunk upsert."""
        chunks = [
            Chunk(
                content="Test content",
                embedding=np.array([0.1] * 384, dtype=np.float32),
                chunk_id="abc123def456789012345678901234567890",
            )
        ]

        mock_backend.upsert_chunks("recall_384d", chunks)

        mock_backend._mock_instance.upsert.assert_called_once()
        call_kwargs = mock_backend._mock_instance.upsert.call_args[1]
        assert call_kwargs["collection_name"] == "recall_384d"
        assert len(call_kwargs["points"]) == 1

    def test_search_legacy(self, mock_backend):
        """Verify search with legacy (unnamed) vectors."""
        # Mark as legacy
        mock_backend._legacy_collections.add("recall_384d")

        mock_result = MagicMock()
        mock_result.id = "test-uuid"
        mock_result.payload = {
            "content": "Test content",
            "original_id": "chunk-123",
            "metadata": {"session_id": "test"},
        }
        mock_result.vector = [0.1] * 384
        mock_result.score = 0.95

        mock_backend._mock_instance.search.return_value = [mock_result]

        query_vector = np.array([0.1] * 384, dtype=np.float32)
        results = mock_backend.search("recall_384d", query_vector, top_k=5)

        assert len(results) == 1
        assert results[0].content == "Test content"
        assert results[0].id == "chunk-123"
        # Legacy uses unnamed query_vector
        call_kwargs = mock_backend._mock_instance.search.call_args[1]
        assert isinstance(call_kwargs["query_vector"], list)

    def test_search_named_vectors(self, mock_backend):
        """Verify search with named vectors uses ('dense', vector) tuple."""
        mock_result = MagicMock()
        mock_result.id = "test-uuid"
        mock_result.payload = {
            "content": "Test content",
            "original_id": "chunk-123",
            "metadata": {"session_id": "test"},
        }
        mock_result.vector = {"dense": [0.1] * 384}
        mock_result.score = 0.95

        mock_backend._mock_instance.search.return_value = [mock_result]

        query_vector = np.array([0.1] * 384, dtype=np.float32)
        results = mock_backend.search("recall_384d", query_vector, top_k=5)

        assert len(results) == 1
        assert results[0].content == "Test content"
        # Named uses ("dense", vector) tuple
        call_kwargs = mock_backend._mock_instance.search.call_args[1]
        assert isinstance(call_kwargs["query_vector"], tuple)
        assert call_kwargs["query_vector"][0] == "dense"

    def test_search_no_vector_error(self, mock_backend):
        """Verify error when search returns no vectors."""
        mock_backend._legacy_collections.add("recall_384d")
        mock_result = MagicMock()
        mock_result.id = "test-uuid"
        mock_result.payload = {"content": "Test", "original_id": "test"}
        mock_result.vector = None

        mock_backend._mock_instance.search.return_value = [mock_result]

        query_vector = np.array([0.1] * 384, dtype=np.float32)

        with pytest.raises(ValueError, match="did not return vectors"):
            mock_backend.search("recall_384d", query_vector)

    def test_hybrid_search(self, mock_backend):
        """Verify hybrid search uses query_points with RRF fusion."""
        from qdrant_client.models import SparseVector

        mock_result = MagicMock()
        mock_result.id = "test-uuid"
        mock_result.payload = {
            "content": "CBS pathway",
            "original_id": "chunk-1",
            "metadata": {},
        }
        mock_result.vector = {"dense": [0.1] * 384}

        mock_backend._mock_instance.query_points.return_value = MagicMock(points=[mock_result])

        query_vector = np.array([0.1] * 384, dtype=np.float32)
        sparse_query = SparseVector(indices=[42, 100], values=[1.0, 1.0])

        results = mock_backend.hybrid_search("recall_384d", query_vector, sparse_query, top_k=5)

        assert len(results) == 1
        assert results[0].content == "CBS pathway"
        mock_backend._mock_instance.query_points.assert_called_once()

    def test_hybrid_search_falls_back_for_legacy(self, mock_backend):
        """Verify hybrid search falls back to dense-only for legacy collections."""
        mock_backend._legacy_collections.add("recall_384d")

        mock_result = MagicMock()
        mock_result.id = "test-uuid"
        mock_result.payload = {"content": "Test", "original_id": "chunk-1", "metadata": {}}
        mock_result.vector = [0.1] * 384
        mock_backend._mock_instance.search.return_value = [mock_result]

        from qdrant_client.models import SparseVector

        query_vector = np.array([0.1] * 384, dtype=np.float32)
        sparse_query = SparseVector(indices=[42], values=[1.0])

        results = mock_backend.hybrid_search("recall_384d", query_vector, sparse_query, top_k=5)

        assert len(results) == 1
        # Should have used client.search, not query_points
        mock_backend._mock_instance.search.assert_called_once()
        mock_backend._mock_instance.query_points.assert_not_called()

    def test_get_all_chunks_unnamed_vectors(self, mock_backend):
        """Verify get_all_chunks with unnamed (legacy) vectors."""
        mock_point = MagicMock()
        mock_point.id = "test-uuid"
        mock_point.payload = {"content": "Test content", "original_id": "chunk-123", "metadata": {}}
        mock_point.vector = [0.1] * 384

        mock_backend._mock_instance.scroll.return_value = ([mock_point], None)

        chunks = mock_backend.get_all_chunks("recall_384d", limit=100)

        assert len(chunks) == 1
        assert chunks[0].content == "Test content"

    def test_get_all_chunks_named_vectors(self, mock_backend):
        """Verify get_all_chunks extracts dense from named vector dict."""
        mock_point = MagicMock()
        mock_point.id = "test-uuid"
        mock_point.payload = {"content": "Named content", "original_id": "chunk-456", "metadata": {}}
        mock_point.vector = {"dense": [0.2] * 384}

        mock_backend._mock_instance.scroll.return_value = ([mock_point], None)

        chunks = mock_backend.get_all_chunks("recall_384d", limit=100)

        assert len(chunks) == 1
        assert chunks[0].content == "Named content"
        assert len(chunks[0].embedding) == 384

    def test_get_all_chunks_paginated(self, mock_backend):
        """Verify get_all_chunks paginates through all pages."""
        # Page 1: returns a point and a next_offset
        point1 = MagicMock()
        point1.id = "uuid-1"
        point1.payload = {"content": "Chunk 1", "original_id": "id-1", "metadata": {}}
        point1.vector = [0.1] * 384

        # Page 2: returns a point and None offset (last page)
        point2 = MagicMock()
        point2.id = "uuid-2"
        point2.payload = {"content": "Chunk 2", "original_id": "id-2", "metadata": {}}
        point2.vector = [0.2] * 384

        mock_backend._mock_instance.scroll.side_effect = [
            ([point1], "offset-2"),
            ([point2], None),
        ]

        chunks = mock_backend.get_all_chunks("recall_384d", limit=1, paginate=True)

        assert len(chunks) == 2
        assert chunks[0].content == "Chunk 1"
        assert chunks[1].content == "Chunk 2"
        assert mock_backend._mock_instance.scroll.call_count == 2

    def test_get_all_chunks_no_vector_error(self, mock_backend):
        """Verify error when scroll returns no vectors."""
        mock_point = MagicMock()
        mock_point.id = "test-uuid"
        mock_point.payload = {"content": "Test", "original_id": "test"}
        mock_point.vector = None

        mock_backend._mock_instance.scroll.return_value = ([mock_point], None)

        with pytest.raises(ValueError, match="did not return vectors"):
            mock_backend.get_all_chunks("recall_384d")

    def test_count(self, mock_backend):
        """Verify chunk count."""
        mock_info = MagicMock()
        mock_info.points_count = 42
        mock_backend._mock_instance.get_collection.return_value = mock_info

        count = mock_backend.count("recall_384d")

        assert count == 42

    def test_count_none(self, mock_backend):
        """Verify chunk count handles None."""
        mock_info = MagicMock()
        mock_info.points_count = None
        mock_backend._mock_instance.get_collection.return_value = mock_info

        count = mock_backend.count("recall_384d")

        assert count == 0

    def test_delete_collection(self, mock_backend):
        """Verify collection deletion."""
        mock_backend.delete_collection("recall_384d")

        mock_backend._mock_instance.delete_collection.assert_called_with(
            collection_name="recall_384d"
        )
