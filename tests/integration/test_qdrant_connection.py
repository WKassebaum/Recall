"""
Waypoint 2: Qdrant connection test.

Validates Qdrant connectivity and basic operations.
"""

import pytest

from semvecmem.backends.qdrant import QdrantBackend


class TestQdrantConnection:
    """Waypoint 2 tests - Qdrant connection validation."""

    @pytest.fixture
    def backend(self) -> QdrantBackend:
        """Create Qdrant backend."""
        return QdrantBackend(host="localhost", port=6333)

    def test_qdrant_health_check(self, backend: QdrantBackend) -> None:
        """Waypoint 2: Verify Qdrant is accessible."""
        assert backend.health_check(), (
            "Qdrant health check failed. "
            "Ensure Qdrant is running: docker run -p 6333:6333 qdrant/qdrant"
        )

    def test_create_collection(self, backend: QdrantBackend) -> None:
        """Waypoint 2: Verify collection creation."""
        collection_name = "test_collection_384d"

        # Clean up if exists
        try:
            backend.delete_collection(collection_name)
        except Exception:
            pass

        # Create collection
        backend.ensure_collection(collection_name, dimension=384)

        # Verify exists
        collections = backend.client.get_collections().collections
        collection_names = [c.name for c in collections]
        assert collection_name in collection_names

        # Clean up
        backend.delete_collection(collection_name)

    def test_collection_persistence(self, backend: QdrantBackend) -> None:
        """Waypoint 2: Verify collections persist across connections."""
        collection_name = "test_persistence_384d"

        # Clean up if exists
        try:
            backend.delete_collection(collection_name)
        except Exception:
            pass

        # Create collection
        backend.ensure_collection(collection_name, dimension=384)

        # Create new client connection
        backend2 = QdrantBackend(host="localhost", port=6333)
        collections = backend2.client.get_collections().collections
        collection_names = [c.name for c in collections]

        assert collection_name in collection_names

        # Clean up
        backend.delete_collection(collection_name)
