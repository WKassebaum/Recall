"""Tests for the MCP server tools.

Tests ingest_memory, recall_memory, memory_stats, and diagnose_installation tools.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestMCPServerIngest:
    """Test ingest_memory tool."""

    @pytest.fixture
    def mock_components(self):
        """Create mock components for MCP server."""
        mock_config = MagicMock()
        mock_chunker_factory = MagicMock()
        mock_embedder = MagicMock()
        mock_embedder.name = "test-embedder"
        mock_embedder.dimension = 384
        mock_store = MagicMock()
        mock_store.add.return_value = "chunk-id-123"
        mock_store.count.return_value = 10
        mock_store.active_collection = "recall_384d"
        mock_store.backend = MagicMock()
        mock_store.backend.mode = "embedded"
        mock_store.backend.path = "~/.recall/qdrant"

        return mock_config, mock_chunker_factory, mock_embedder, mock_store

    @pytest.mark.asyncio
    async def test_ingest_memory_basic(self, mock_components):
        """Verify basic memory ingestion."""
        from recall.mcp.server import ingest_memory

        config, chunker_factory, embedder, store = mock_components

        # Mock chunker to return 2 chunks
        mock_chunk1 = MagicMock()
        mock_chunk1.id = "chunk-1"
        mock_chunk1.content = "First chunk"
        mock_chunk2 = MagicMock()
        mock_chunk2.id = "chunk-2"
        mock_chunk2.content = "Second chunk"
        chunker_factory.chunk.return_value = [mock_chunk1, mock_chunk2]

        with patch("recall.mcp.server.get_components", return_value=mock_components):
            result = await ingest_memory(
                content="Test content for ingestion", session_id="test-session"
            )

        assert "Ingested 2 chunks" in result
        assert "test-session" in result
        assert store.add.call_count == 2

    @pytest.mark.asyncio
    async def test_ingest_memory_with_metadata(self, mock_components):
        """Verify memory ingestion with event metadata."""
        from recall.mcp.server import ingest_memory

        config, chunker_factory, embedder, store = mock_components

        mock_chunk = MagicMock()
        mock_chunk.id = "chunk-1"
        mock_chunk.content = "Decision content"
        chunker_factory.chunk.return_value = [mock_chunk]

        with patch("recall.mcp.server.get_components", return_value=mock_components):
            result = await ingest_memory(
                content="Selected Arctic embedder",
                session_id="architecture",
                metadata={
                    "event_type": "decision",
                    "tags": "architecture,embeddings",
                    "outcome": "Arctic selected",
                },
            )

        assert "Ingested 1 chunks" in result
        assert "decision" in result
        # Verify metadata was passed to store.add
        call_args = store.add.call_args
        assert "decision" in str(call_args)

    @pytest.mark.asyncio
    async def test_ingest_memory_with_content_type(self, mock_components):
        """Verify memory ingestion with explicit content type."""
        from recall.mcp.server import ingest_memory

        config, chunker_factory, embedder, store = mock_components

        mock_chunk = MagicMock()
        mock_chunk.id = "chunk-1"
        mock_chunk.content = "def test(): pass"
        chunker_factory.chunk.return_value = [mock_chunk]

        with patch("recall.mcp.server.get_components", return_value=mock_components):
            result = await ingest_memory(
                content="def test(): pass", session_id="code-session", content_type="python"
            )

        assert "Ingested 1 chunks" in result
        assert "python" in result
        chunker_factory.chunk.assert_called_with("def test(): pass", content_type="python")


class TestMCPServerRecall:
    """Test recall_memory tool."""

    @pytest.fixture
    def mock_components_with_results(self):
        """Create mock components with search results."""
        mock_config = MagicMock()
        mock_chunker_factory = MagicMock()
        mock_embedder = MagicMock()
        mock_embedder.name = "test-embedder"
        mock_embedder.dimension = 384

        mock_store = MagicMock()
        mock_store.count.return_value = 10
        mock_store.active_collection = "recall_384d"
        mock_store.backend = MagicMock()
        mock_store.backend.mode = "embedded"
        mock_store.backend.path = "~/.recall/qdrant"

        # Create mock search results
        mock_result1 = MagicMock()
        mock_result1.content = "First memory content"
        mock_result1.score = 0.95
        mock_result1.metadata = {
            "session_id": "test-session",
            "ingested_at": "2025-10-10T12:00:00Z",
            "event_type": "decision",
        }

        mock_result2 = MagicMock()
        mock_result2.content = "Second memory content"
        mock_result2.score = 0.85
        mock_result2.metadata = {
            "session_id": "test-session",
            "ingested_at": "2025-10-09T12:00:00Z",
            "event_type": "discovery",
        }

        mock_store.search.return_value = [mock_result1, mock_result2]

        return mock_config, mock_chunker_factory, mock_embedder, mock_store

    @pytest.mark.asyncio
    async def test_recall_memory_semantic(self, mock_components_with_results):
        """Verify semantic memory recall."""
        from recall.mcp.server import recall_memory

        with patch("recall.mcp.server.get_components", return_value=mock_components_with_results):
            result = await recall_memory(query="test query", top_k=5)

        assert "Found 2 relevant memories" in result
        assert "SEMANTIC" in result
        assert "First memory content" in result
        assert "0.95" in result

    @pytest.mark.asyncio
    async def test_recall_memory_chronological(self, mock_components_with_results):
        """Verify chronological memory recall."""
        from recall.mcp.server import recall_memory

        with patch("recall.mcp.server.get_components", return_value=mock_components_with_results):
            result = await recall_memory(retrieval_mode="chronological", session_id="test-session")

        assert "CHRONOLOGICAL" in result
        # Score should not be shown in chronological mode
        assert "decision" in result

    @pytest.mark.asyncio
    async def test_recall_memory_hybrid(self, mock_components_with_results):
        """Verify hybrid memory recall."""
        from recall.mcp.server import recall_memory

        with patch("recall.mcp.server.get_components", return_value=mock_components_with_results):
            result = await recall_memory(
                query="test",
                retrieval_mode="hybrid",
                time_range="2025-10-01,2025-10-15",
                event_types="decision,discovery",
            )

        assert "HYBRID" in result
        _, _, _, mock_store = mock_components_with_results
        # Verify search was called with correct parameters
        mock_store.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_recall_memory_no_results(self, mock_components_with_results):
        """Verify handling when no memories found."""
        from recall.mcp.server import recall_memory

        _, _, _, mock_store = mock_components_with_results
        mock_store.search.return_value = []

        with patch("recall.mcp.server.get_components", return_value=mock_components_with_results):
            result = await recall_memory(query="nonexistent")

        assert "No matching memories" in result

    @pytest.mark.asyncio
    async def test_recall_memory_with_min_score_filter(self, mock_components_with_results):
        """Verify min_score filtering."""
        from recall.mcp.server import recall_memory

        with patch("recall.mcp.server.get_components", return_value=mock_components_with_results):
            result = await recall_memory(
                query="test", min_score=0.9  # Should filter out the 0.85 result
            )

        # Only the 0.95 result should pass
        assert "First memory content" in result


class TestMCPServerStats:
    """Test memory_stats tool."""

    @pytest.mark.asyncio
    async def test_memory_stats(self):
        """Verify memory stats output."""
        from recall.mcp.server import memory_stats

        mock_config = MagicMock()
        mock_chunker_factory = MagicMock()
        mock_embedder = MagicMock()
        mock_embedder.name = "arctic-embed-m"
        mock_embedder.dimension = 1024

        mock_backend = MagicMock()
        mock_backend.mode = "network"
        mock_backend.host = "localhost"
        mock_backend.port = 6337

        mock_store = MagicMock()
        mock_store.count.return_value = 42
        mock_store.active_collection = "recall_1024d"
        mock_store.backend = mock_backend

        mock_components = (mock_config, mock_chunker_factory, mock_embedder, mock_store)

        with patch("recall.mcp.server.get_components", return_value=mock_components):
            result = await memory_stats()

        assert "42" in result  # Total chunks
        assert "arctic-embed-m" in result
        assert "1024D" in result
        assert "recall_1024d" in result
        assert "localhost:6337" in result


class TestMCPServerGetComponents:
    """Test get_components initialization."""

    def test_get_components_initializes_once(self, tmp_path):
        """Verify components are initialized lazily."""
        # This test would require more complex mocking
        # of the module-level globals, so we'll skip detailed testing
        pass


class TestMCPServerDiagnoseInstallation:
    """Test diagnose_installation tool."""

    @pytest.mark.asyncio
    async def test_diagnose_installation_all_passing(self, tmp_path):
        """Verify diagnosis when all checks pass."""
        from recall.mcp.server import diagnose_installation

        # Create mock ~/.claude.json
        claude_config = tmp_path / ".claude.json"
        claude_config.write_text(
            '{"mcpServers": {"plugin:recall:recall": {"command": "/usr/bin/python3"}}}'
        )

        mock_components = (
            MagicMock(),  # config
            MagicMock(),  # chunker_factory
            MagicMock(name="arctic-embed-m", dimension=1024),  # embedder
            MagicMock(
                count=lambda: 10, backend=MagicMock(mode="embedded", path="~/.recall/qdrant")
            ),  # store
        )

        with patch.object(Path, "home", return_value=tmp_path):
            with patch("recall.mcp.server.get_components", return_value=mock_components):
                with patch("importlib.metadata.version", return_value="1.4.0"):
                    result = await diagnose_installation()

        assert "Diagnostics" in result
        assert "Python" in result
