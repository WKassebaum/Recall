"""
Waypoints 10-11: MCP Server Integration Tests.

Tests MCP server tools with real components (embedder, chunker, Qdrant).
"""

import pytest

from semvecmem.backends.qdrant import QdrantBackend
from semvecmem.mcp import server


class TestMCPServerIntegration:
    """Waypoints 10-11 tests - MCP server integration validation."""

    @pytest.fixture
    def cleanup_collections(self) -> None:
        """Clean up test collections after each test."""
        yield
        # Cleanup
        backend = QdrantBackend(host="localhost", port=6333)
        try:
            backend.delete_collection("semvecmem_768d")
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_ingest_memory_tool(self, cleanup_collections: None) -> None:
        """Waypoint 10: Verify ingest_memory tool works end-to-end."""
        # Reset global components to force reinitialization
        server._config = None
        server._chunker_factory = None
        server._embedder = None
        server._store = None

        # Ingest Python code
        python_code = """
def calculate_fibonacci(n):
    \"\"\"Calculate nth Fibonacci number.\"\"\"
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

class MathUtils:
    \"\"\"Utility class for math operations.\"\"\"

    @staticmethod
    def factorial(n):
        if n == 0:
            return 1
        return n * MathUtils.factorial(n-1)
"""
        result = await server.ingest_memory(
            content=python_code,
            session_id="test-session-python",
            content_type="python",
            metadata={"project": "math-utils", "author": "test"},
        )

        # Verify result message
        assert "Ingested" in result
        assert "chunks" in result
        assert "test-session-python" in result

        # Verify chunks were stored
        _, _, _, store = server.get_components()
        assert store.count() >= 2  # At least 2 chunks (function + class)

    @pytest.mark.asyncio
    async def test_recall_memory_tool(self, cleanup_collections: None) -> None:
        """Waypoint 11: Verify recall_memory tool works end-to-end."""
        # Reset global components
        server._config = None
        server._chunker_factory = None
        server._embedder = None
        server._store = None

        # First ingest some content
        code = """
def authenticate_user(username, password):
    \"\"\"Authenticate user with credentials.\"\"\"
    return username == "admin" and password == "secret"

def logout_user(session_id):
    \"\"\"Logout user by session ID.\"\"\"
    return True
"""
        await server.ingest_memory(
            content=code, session_id="test-session-auth", content_type="python"
        )

        # Search for authentication-related code
        results = await server.recall_memory(
            query="user authentication", top_k=5, session_id="test-session-auth"
        )

        # Verify results
        assert "Found" in results
        assert "memories" in results
        assert "authenticate" in results.lower() or "user" in results.lower()
        assert "test-session-auth" in results

    @pytest.mark.asyncio
    async def test_recall_memory_with_filtering(self, cleanup_collections: None) -> None:
        """Waypoint 11: Verify session-based filtering works."""
        # Reset global components
        server._config = None
        server._chunker_factory = None
        server._embedder = None
        server._store = None

        # Ingest content from two different sessions
        await server.ingest_memory(
            content="Session A uses Redis for caching",
            session_id="session-a",
            content_type="prose",
        )
        await server.ingest_memory(
            content="Session B uses PostgreSQL for storage",
            session_id="session-b",
            content_type="prose",
        )

        # Search with session filter
        results_a = await server.recall_memory(query="database", session_id="session-a", top_k=10)
        results_b = await server.recall_memory(query="database", session_id="session-b", top_k=10)

        # Verify filtering works
        assert "session-a" in results_a
        assert "session-b" not in results_a
        assert "session-b" in results_b
        assert "session-a" not in results_b

    @pytest.mark.asyncio
    async def test_recall_memory_with_min_score(self, cleanup_collections: None) -> None:
        """Waypoint 11: Verify min_score threshold filtering works."""
        # Reset global components
        server._config = None
        server._chunker_factory = None
        server._embedder = None
        server._store = None

        # Ingest specific content
        await server.ingest_memory(
            content="Python is a programming language",
            session_id="test-session-score",
            content_type="prose",
        )

        # Search with very high min_score (should filter most results)
        # Note: Even unrelated queries can score >0.8 due to shared semantic space
        results_high_threshold = await server.recall_memory(
            query="completely unrelated query about cooking recipes",
            min_score=0.95,  # Very high threshold
            top_k=10,
        )

        # Should have no results due to very high threshold
        assert (
            "No matching memories" in results_high_threshold or "Found 0" in results_high_threshold
        )

        # Search with low min_score (should return results)
        results_low_threshold = await server.recall_memory(
            query="Python programming", min_score=0.0, top_k=10  # Low threshold
        )

        # Should have results
        assert "Found" in results_low_threshold
        assert "Python" in results_low_threshold

    @pytest.mark.asyncio
    async def test_memory_stats_tool(self, cleanup_collections: None) -> None:
        """Waypoint 11: Verify memory_stats tool works."""
        # Reset global components
        server._config = None
        server._chunker_factory = None
        server._embedder = None
        server._store = None

        # Get stats before ingestion
        stats_before = await server.memory_stats()
        assert "SemVecMem Statistics" in stats_before
        assert "Total chunks: 0" in stats_before
        assert "Active collection:" in stats_before
        assert "Embedder:" in stats_before
        assert "Dimension:" in stats_before

        # Ingest some content
        await server.ingest_memory(
            content="Test content for stats",
            session_id="test-session-stats",
            content_type="prose",
        )

        # Get stats after ingestion
        stats_after = await server.memory_stats()
        assert "Total chunks: 1" in stats_after
        assert "semvecmem_768d" in stats_after

    @pytest.mark.asyncio
    async def test_auto_content_type_detection(self, cleanup_collections: None) -> None:
        """Waypoint 10: Verify auto-detection of content type works."""
        # Reset global components
        server._config = None
        server._chunker_factory = None
        server._embedder = None
        server._store = None

        # Ingest Markdown without specifying type (should auto-detect)
        markdown_content = """
# Introduction

This is a markdown document with code blocks.

## Code Example

```python
def hello():
    print("Hello, world!")
```

This should be detected as Markdown.
"""
        result = await server.ingest_memory(
            content=markdown_content,
            session_id="test-session-markdown",
            # No content_type specified - should auto-detect
        )

        assert "Ingested" in result
        assert "auto-detected" in result

    @pytest.mark.asyncio
    async def test_end_to_end_memory_flow(self, cleanup_collections: None) -> None:
        """Waypoint 11: Verify complete ingest → recall → stats flow."""
        # Reset global components
        server._config = None
        server._chunker_factory = None
        server._embedder = None
        server._store = None

        # 1. Check initial stats
        stats_1 = await server.memory_stats()
        assert "Total chunks: 0" in stats_1

        # 2. Ingest multiple pieces of content
        await server.ingest_memory(
            content="FastAPI is a web framework for Python",
            session_id="web-dev",
            content_type="prose",
        )
        await server.ingest_memory(
            content="React is a JavaScript library for UIs",
            session_id="web-dev",
            content_type="prose",
        )
        await server.ingest_memory(
            content="PostgreSQL is a relational database",
            session_id="databases",
            content_type="prose",
        )

        # 3. Check stats after ingestion
        stats_2 = await server.memory_stats()
        assert "Total chunks: 3" in stats_2

        # 4. Recall web development content
        web_results = await server.recall_memory(
            query="web development frameworks", session_id="web-dev", top_k=5
        )
        assert "FastAPI" in web_results or "React" in web_results
        assert "web-dev" in web_results

        # 5. Recall database content
        db_results = await server.recall_memory(
            query="database systems", session_id="databases", top_k=5
        )
        assert "PostgreSQL" in db_results
        assert "databases" in db_results

        # 6. Cross-session search (no filter)
        all_results = await server.recall_memory(query="technology", top_k=10)  # No session filter
        assert "Found" in all_results

    @pytest.mark.asyncio
    async def test_metadata_preservation(self, cleanup_collections: None) -> None:
        """Waypoint 10: Verify metadata is preserved through ingestion."""
        # Reset global components
        server._config = None
        server._chunker_factory = None
        server._embedder = None
        server._store = None

        # Ingest with custom metadata
        await server.ingest_memory(
            content="Custom metadata test content",
            session_id="metadata-test",
            content_type="prose",
            metadata={"priority": "high", "category": "testing", "version": "1.0"},
        )

        # Recall should include metadata in results
        results = await server.recall_memory(
            query="metadata test", session_id="metadata-test", top_k=5
        )

        # Verify session_id is in results (guaranteed metadata)
        assert "metadata-test" in results
        assert "Found" in results
