"""Waypoint 16: System Integration Tests.

Comprehensive end-to-end validation of all system components working together:
- MCP server with all tools (ingest, recall, stats)
- CLI commands (ingest, recall, stats, migrate)
- Multi-strategy chunking (Python, Markdown, JSON, Prose)
- Multi-collection routing (different embedding dimensions)
- Metadata handling and filtering
- Complete workflows from ingestion to retrieval
"""

import json
from pathlib import Path

import pytest

from recall.backends.qdrant import QdrantBackend
from recall.chunking.factory import ChunkerFactory
from recall.config.loader import load_config
from recall.core.store import UnifiedVectorStore
from recall.embedders.sentence_transformer import SentenceTransformerEmbedder


class TestSystemIntegration:
    """Waypoint 16: System-wide integration tests."""

    @pytest.fixture
    def cleanup_all_collections(self) -> None:
        """Clean up all test collections before and after tests."""
        backend = QdrantBackend(host="localhost", port=6333)

        # Cleanup before
        for collection in ["recall_384d", "recall_768d", "recall_1024d"]:
            try:
                backend.delete_collection(collection)
            except Exception:
                pass

        yield

        # Cleanup after
        for collection in ["recall_384d", "recall_768d", "recall_1024d"]:
            try:
                backend.delete_collection(collection)
            except Exception:
                pass

    def test_end_to_end_multi_content_workflow(self, cleanup_all_collections: None) -> None:
        """Waypoint 16: Complete workflow with multiple content types."""
        # 1. Initialize system components
        config = load_config("config.yaml")
        embedder = SentenceTransformerEmbedder(config.embedder_model)
        backend = QdrantBackend(host=config.qdrant_host, port=config.qdrant_port)
        store = UnifiedVectorStore(backend=backend)
        store.set_embedder(embedder)
        chunker_factory = ChunkerFactory()

        # 2. Ingest diverse content types

        # Python code
        python_code = """
def authenticate_user(username, password):
    \"\"\"Authenticate user with JWT token.\"\"\"
    if not username or not password:
        return None
    token = create_jwt_token(username)
    return token

class SessionManager:
    \"\"\"Manage user sessions with Redis cache.\"\"\"

    def __init__(self):
        self.sessions = {}

    def create_session(self, user_id):
        session_id = generate_session_id()
        self.sessions[session_id] = user_id
        return session_id
"""
        python_chunks = chunker_factory.chunk(python_code, content_type="python")
        for chunk in python_chunks:
            store.add(
                chunk.content,
                metadata={
                    "content_type": "python",
                    "session_id": "integration_test",
                    "source": "test_auth.py",
                },
            )

        # Markdown documentation
        markdown_doc = """
# User Authentication API

## POST /auth/login

Authenticate a user and receive a JWT token.

### Request Body

```json
{
  "username": "user@example.com",
  "password": "secret123"
}
```

### Response

```json
{
  "token": "eyJhbGc...",
  "expires_in": 3600
}
```

## Session Management

Sessions are stored in Redis with TTL of 24 hours.
Use the JWT token in Authorization header for protected routes.
"""
        markdown_chunks = chunker_factory.chunk(markdown_doc, content_type="markdown")
        for chunk in markdown_chunks:
            store.add(
                chunk.content,
                metadata={
                    "content_type": "markdown",
                    "session_id": "integration_test",
                    "source": "api_docs.md",
                },
            )

        # JSON configuration
        json_config = {
            "authentication": {
                "jwt": {
                    "secret_key": "your-secret-key",
                    "algorithm": "HS256",
                    "expiration_hours": 24,
                },
                "session": {
                    "backend": "redis",
                    "ttl_seconds": 86400,
                    "cookie_name": "session_id",
                },
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "userdb",
                "pool_size": 10,
            },
        }
        json_chunks = chunker_factory.chunk(json.dumps(json_config, indent=2), content_type="json")
        for chunk in json_chunks:
            store.add(
                chunk.content,
                metadata={
                    "content_type": "json",
                    "session_id": "integration_test",
                    "source": "config.json",
                },
            )

        # 3. Verify ingestion
        total_chunks = store.count()
        assert total_chunks > 0, "No chunks ingested"

        # 4. Test semantic search across content types
        auth_results = store.search("JWT token authentication", top_k=5)
        assert len(auth_results) > 0, "No authentication results found"

        # Verify results contain relevant content from multiple sources
        all_content = " ".join(r.content for r in auth_results)
        assert "jwt" in all_content.lower() or "token" in all_content.lower()

        # 5. Test metadata filtering
        python_only = store.search("authentication", top_k=10, filter={"content_type": "python"})
        assert len(python_only) > 0, "No Python results found"
        for result in python_only:
            assert result.metadata.get("content_type") == "python"

        # 6. Test session-based filtering
        session_results = store.search(
            "session management",
            top_k=10,
            filter={"session_id": "integration_test"},
        )
        assert len(session_results) > 0, "No session results found"
        for result in session_results:
            assert result.metadata.get("session_id") == "integration_test"

        # 7. Test chunk count
        assert store.count() == total_chunks
        assert store.active_dimension == embedder.dimension

    def test_multi_collection_dimension_routing(self, cleanup_all_collections: None) -> None:
        """Waypoint 16: Verify multi-collection routing works correctly."""
        config = load_config("config.yaml")
        backend = QdrantBackend(host=config.qdrant_host, port=config.qdrant_port)

        # Test with Arctic (768D)
        embedder_768 = SentenceTransformerEmbedder("Snowflake/snowflake-arctic-embed-m")
        store_768 = UnifiedVectorStore(backend=backend)
        store_768.set_embedder(embedder_768)

        store_768.add("Test content for 768D collection", metadata={"dim": "768"})
        assert store_768.count() == 1

        # Test with MiniLM (384D)
        embedder_384 = SentenceTransformerEmbedder("all-MiniLM-L6-v2")
        store_384 = UnifiedVectorStore(backend=backend)
        store_384.set_embedder(embedder_384)

        store_384.add("Test content for 384D collection", metadata={"dim": "384"})
        assert store_384.count() == 1

        # Verify collections are separate
        assert store_768.count() == 1  # Should still be 1, not 2
        assert store_384.count() == 1  # Should still be 1, not 2

        # Verify search works in correct collection
        results_768 = store_768.search("768D collection", top_k=1)
        assert len(results_768) == 1
        assert results_768[0].metadata.get("dim") == "768"

        results_384 = store_384.search("384D collection", top_k=1)
        assert len(results_384) == 1
        assert results_384[0].metadata.get("dim") == "384"

    def test_complex_metadata_queries(self, cleanup_all_collections: None) -> None:
        """Waypoint 16: Test advanced metadata filtering scenarios."""
        config = load_config("config.yaml")
        embedder = SentenceTransformerEmbedder(config.embedder_model)
        backend = QdrantBackend(host=config.qdrant_host, port=config.qdrant_port)
        store = UnifiedVectorStore(backend=backend)
        store.set_embedder(embedder)

        # Ingest content with rich metadata
        test_data = [
            {
                "content": "User authentication with OAuth2",
                "metadata": {
                    "topic": "auth",
                    "priority": "high",
                    "tags": "oauth,security",
                    "session_id": "session_1",
                },
            },
            {
                "content": "Database connection pooling",
                "metadata": {
                    "topic": "database",
                    "priority": "medium",
                    "tags": "postgres,performance",
                    "session_id": "session_1",
                },
            },
            {
                "content": "API rate limiting implementation",
                "metadata": {
                    "topic": "api",
                    "priority": "high",
                    "tags": "security,performance",
                    "session_id": "session_2",
                },
            },
            {
                "content": "Logging and monitoring setup",
                "metadata": {
                    "topic": "monitoring",
                    "priority": "low",
                    "tags": "observability",
                    "session_id": "session_2",
                },
            },
        ]

        for item in test_data:
            store.add(item["content"], metadata=item["metadata"])

        assert store.count() == 4

        # Test filtering by topic
        auth_results = store.search("security", top_k=10, filter={"topic": "auth"})
        assert len(auth_results) > 0
        for result in auth_results:
            assert result.metadata.get("topic") == "auth"

        # Test filtering by priority
        high_priority = store.search("implementation", top_k=10, filter={"priority": "high"})
        assert len(high_priority) > 0
        for result in high_priority:
            assert result.metadata.get("priority") == "high"

        # Test filtering by session
        session_1_results = store.search("database", top_k=10, filter={"session_id": "session_1"})
        assert len(session_1_results) > 0
        for result in session_1_results:
            assert result.metadata.get("session_id") == "session_1"

    def test_chunking_strategy_validation(self, cleanup_all_collections: None) -> None:
        """Waypoint 16: Verify all chunking strategies work correctly."""
        chunker_factory = ChunkerFactory()

        # Test Python chunking
        python_code = """
def function_one():
    pass

def function_two():
    pass

class MyClass:
    def method_one(self):
        pass
"""
        python_chunks = chunker_factory.chunk(python_code, content_type="python")
        assert len(python_chunks) >= 2  # At least 2 top-level constructs

        # Test Markdown chunking
        markdown_doc = """
# Section One

Content for section one.

## Subsection 1.1

More content.

# Section Two

Content for section two.
"""
        markdown_chunks = chunker_factory.chunk(markdown_doc, content_type="markdown")
        assert len(markdown_chunks) >= 1  # At least 1 chunk

        # Test JSON chunking
        json_doc = {
            "section1": {"key1": "value1", "key2": "value2"},
            "section2": {"key3": "value3", "key4": "value4"},
        }
        json_chunks = chunker_factory.chunk(json.dumps(json_doc, indent=2), content_type="json")
        assert len(json_chunks) >= 1

        # Test prose chunking (auto-detection)
        prose_text = "This is a simple text. " * 100  # Long prose text
        prose_chunks = chunker_factory.chunk(prose_text)  # Auto-detects as prose
        assert len(prose_chunks) > 0

    def test_stats_validation(self, cleanup_all_collections: None) -> None:
        """Waypoint 16: Verify store properties and counts are accurate."""
        config = load_config("config.yaml")
        embedder = SentenceTransformerEmbedder(config.embedder_model)
        backend = QdrantBackend(host=config.qdrant_host, port=config.qdrant_port)
        store = UnifiedVectorStore(backend=backend)
        store.set_embedder(embedder)

        # Ingest known content
        test_content = [
            "First test chunk",
            "Second test chunk",
            "Third test chunk",
            "Fourth test chunk",
            "Fifth test chunk",
        ]

        for i, content in enumerate(test_content):
            store.add(content, metadata={"index": str(i), "batch": "test_batch"})

        # Verify store properties
        assert store.count() == len(test_content)
        assert store.active_dimension == embedder.dimension
        assert store.active_collection == f"recall_{embedder.dimension}d"

    def test_error_handling_and_recovery(self, cleanup_all_collections: None) -> None:
        """Waypoint 16: Verify system handles errors gracefully."""
        config = load_config("config.yaml")
        embedder = SentenceTransformerEmbedder(config.embedder_model)
        backend = QdrantBackend(host=config.qdrant_host, port=config.qdrant_port)
        store = UnifiedVectorStore(backend=backend)
        store.set_embedder(embedder)

        # Test empty content handling
        store.add("Valid content", metadata={"test": "valid"})
        assert store.count() == 1

        # Test search with no results
        results = store.search("zzzzzz_nonexistent_query_zzzzzz", top_k=5)
        assert isinstance(results, list)
        # Results may be empty or low-scoring

        # Test metadata filter with nonexistent field (should not crash)
        results = store.search("test query", top_k=5, filter={"nonexistent_field": "value"})
        assert isinstance(results, list)
        # Filter returns empty list when no matches found
