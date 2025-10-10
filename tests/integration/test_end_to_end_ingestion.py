"""
Waypoint 6: End-to-end ingestion test.

Tests complete pipeline: config → embedder → chunker → store → search.
"""

import pytest

from recall.backends.qdrant import QdrantBackend
from recall.chunking.python import PythonChunker
from recall.config.loader import load_config
from recall.core.store import UnifiedVectorStore
from recall.embedders.sentence_transformer import SentenceTransformerEmbedder


class TestEndToEndIngestion:
    """Waypoint 6 tests - End-to-end pipeline validation."""

    @pytest.fixture
    def cleanup_collections(self) -> None:
        """Clean up test collections after each test."""
        yield
        # Cleanup
        backend = QdrantBackend(host="localhost", port=6333)
        try:
            backend.delete_collection("recall_768d")
        except Exception:
            pass

    def test_full_ingestion_pipeline(self, cleanup_collections: None) -> None:
        """Waypoint 6: Verify complete ingestion pipeline works."""
        # 1. Load configuration
        config = load_config("config.yaml")
        assert config.embedder_model == "Snowflake/snowflake-arctic-embed-m"

        # 2. Create embedder
        embedder = SentenceTransformerEmbedder(config.embedder_model)
        assert embedder.dimension == 768

        # 3. Create Qdrant backend
        backend = QdrantBackend(host=config.qdrant_host, port=config.qdrant_port)
        assert backend.health_check()

        # 4. Create unified store with backend
        store = UnifiedVectorStore(backend=backend)
        store.set_embedder(embedder)

        # 5. Chunk Python code
        chunker = PythonChunker()
        code = """
def authenticate_user(username, password):
    \"\"\"Authenticate user with credentials.\"\"\"
    if not username or not password:
        return False
    return username == "admin" and password == "secret"

class UserManager:
    \"\"\"Manage user accounts.\"\"\"

    def __init__(self):
        self.users = []

    def add_user(self, user):
        self.users.append(user)

def logout_user(session_id):
    \"\"\"Logout user by session ID.\"\"\"
    return True
"""
        chunks = chunker.chunk_code(code)
        assert len(chunks) == 3  # 2 functions + 1 class

        # 6. Ingest chunks
        store.upsert(chunks)

        # 7. Verify chunks stored
        assert store.count() == 3

        # 8. Search for chunks
        results = store.search("user authentication", top_k=2)

        # Verify search results
        assert len(results) <= 2
        assert len(results) > 0

        # Verify results contain relevant content
        all_content = " ".join(r.content for r in results)
        assert "authenticate" in all_content.lower() or "user" in all_content.lower()

    def test_dimension_verification_with_backend(self, cleanup_collections: None) -> None:
        """Waypoint 6: Verify dimension verification works with Qdrant backend."""
        import numpy as np

        from recall.core.store import Chunk, DimensionMismatchError

        # Create store with backend
        config = load_config("config.yaml")
        embedder = SentenceTransformerEmbedder(config.embedder_model)
        backend = QdrantBackend(host=config.qdrant_host, port=config.qdrant_port)
        store = UnifiedVectorStore(backend=backend)
        store.set_embedder(embedder)

        # Try to insert chunk with wrong dimension
        wrong_chunk = Chunk(content="test", embedding=np.random.rand(1024).astype(np.float32))

        with pytest.raises(DimensionMismatchError) as exc_info:
            store.upsert([wrong_chunk])

        assert "768D" in str(exc_info.value)
        assert "1024D" in str(exc_info.value)

    def test_search_relevance(self, cleanup_collections: None) -> None:
        """Waypoint 6: Verify search returns relevant results."""
        config = load_config("config.yaml")
        embedder = SentenceTransformerEmbedder(config.embedder_model)
        backend = QdrantBackend(host=config.qdrant_host, port=config.qdrant_port)
        store = UnifiedVectorStore(backend=backend)
        store.set_embedder(embedder)

        chunker = PythonChunker()
        code = """
def calculate_tax(amount):
    return amount * 0.1

def process_payment(card_number, amount):
    return True

def send_email(recipient, subject, body):
    return True
"""
        chunks = chunker.chunk_code(code)
        store.upsert(chunks)

        # Search for payment-related code
        results = store.search("payment processing", top_k=1)

        assert len(results) == 1
        assert "payment" in results[0].content.lower()
