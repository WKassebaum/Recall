"""Tests for Recall CLI commands.

Waypoint 12: CLI validation (CC ≤ 5, coverage >80%)
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from recall.cli.main import cli
from recall.core.store import SearchResult


class TestCLICommands:
    """Waypoint 12 tests - CLI command validation."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create Click test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_components(self) -> None:
        """Mock all external dependencies."""
        with patch("recall.cli.main.load_config") as mock_config, patch(
            "recall.embedders.sentence_transformer.SentenceTransformerEmbedder"
        ) as mock_embedder, patch("recall.cli.main.QdrantBackend") as mock_backend, patch(
            "recall.cli.main.UnifiedVectorStore"
        ) as mock_store, patch(
            "recall.cli.main.ChunkerFactory"
        ) as mock_chunker:
            # Configure mocks
            mock_config.return_value = MagicMock(
                embedder_model="mock-model",
                qdrant_host="localhost",
                qdrant_port=6333,
            )

            mock_embedder_instance = MagicMock()
            mock_embedder_instance.name = "mock-embedder"
            mock_embedder_instance.dimension = 384
            mock_embedder.return_value = mock_embedder_instance

            mock_backend_instance = MagicMock()
            mock_backend_instance.health_check.return_value = True
            mock_backend.return_value = mock_backend_instance

            mock_store_instance = MagicMock()
            mock_store_instance.active_collection = "recall_384d"
            mock_store_instance.count.return_value = 10
            mock_store.return_value = mock_store_instance

            mock_chunker_instance = MagicMock()
            mock_chunker_instance.chunk.return_value = [
                MagicMock(content="chunk1", id="id1"),
                MagicMock(content="chunk2", id="id2"),
            ]
            mock_chunker.return_value = mock_chunker_instance

            yield {
                "config": mock_config,
                "embedder": mock_embedder,
                "backend": mock_backend,
                "store": mock_store,
                "chunker": mock_chunker,
                "store_instance": mock_store_instance,
            }

    def test_cli_version(self, runner: CliRunner) -> None:
        """Verify CLI version command works."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "1.3.1" in result.output

    def test_cli_help(self, runner: CliRunner) -> None:
        """Verify CLI help command works."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Semantic vector memory" in result.output
        assert "ingest" in result.output
        assert "search" in result.output
        assert "stats" in result.output

    def test_ingest_command_with_text(self, runner: CliRunner, mock_components: dict) -> None:
        """Waypoint 12: Verify ingest command works with text."""
        result = runner.invoke(
            cli,
            ["ingest", "def hello(): pass", "-s", "test-session", "-t", "python"],
        )

        assert result.exit_code == 0
        assert "Ingested 2 chunks" in result.output
        assert "test-session" in result.output
        assert "python" in result.output

        # Verify store.add was called
        store_instance = mock_components["store_instance"]
        assert store_instance.add.call_count == 2

    def test_ingest_command_with_file(
        self, runner: CliRunner, mock_components: dict, tmp_path: Path
    ) -> None:
        """Waypoint 12: Verify ingest command works with file input."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        result = runner.invoke(
            cli,
            ["ingest", "dummy", "-s", "test-session", "-f", str(test_file)],
        )

        assert result.exit_code == 0
        assert f"Reading from {test_file}" in result.output
        assert "Ingested 2 chunks" in result.output

    def test_ingest_command_missing_session(self, runner: CliRunner) -> None:
        """Waypoint 12: Verify ingest fails without session ID."""
        result = runner.invoke(cli, ["ingest", "content"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_search_command(self, runner: CliRunner, mock_components: dict) -> None:
        """Waypoint 12: Verify search command works."""
        # Mock search results
        mock_results = [
            SearchResult(
                content="test content 1",
                score=0.95,
                chunk_id="id1",
                metadata={"session_id": "test-session"},
            ),
            SearchResult(
                content="test content 2",
                score=0.85,
                chunk_id="id2",
                metadata={"session_id": "test-session"},
            ),
        ]
        mock_components["store_instance"].search.return_value = mock_results

        result = runner.invoke(cli, ["search", "test query", "-k", "5"])

        assert result.exit_code == 0
        assert "Found 2 relevant memories" in result.output
        assert "test content 1" in result.output
        assert "0.950" in result.output

    def test_search_command_with_session_filter(
        self, runner: CliRunner, mock_components: dict
    ) -> None:
        """Waypoint 12: Verify search with session filtering."""
        mock_results = [
            SearchResult(
                content="filtered content",
                score=0.9,
                chunk_id="id1",
                metadata={"session_id": "my-session"},
            )
        ]
        mock_components["store_instance"].search.return_value = mock_results

        result = runner.invoke(cli, ["search", "query", "-s", "my-session", "-k", "10"])

        assert result.exit_code == 0
        assert "Found 1 relevant" in result.output
        assert "my-session" in result.output

    def test_search_command_with_min_score(self, runner: CliRunner, mock_components: dict) -> None:
        """Waypoint 12: Verify search with min score filtering."""
        # Return results with varying scores
        mock_results = [
            SearchResult(content="high score", score=0.95, chunk_id="id1", metadata={}),
            SearchResult(content="low score", score=0.3, chunk_id="id2", metadata={}),
        ]
        mock_components["store_instance"].search.return_value = mock_results

        result = runner.invoke(cli, ["search", "query", "--min-score", "0.5"])

        assert result.exit_code == 0
        # Should only show high score result (0.95 >= 0.5)
        assert "high score" in result.output
        assert "low score" not in result.output

    def test_search_command_no_results(self, runner: CliRunner, mock_components: dict) -> None:
        """Waypoint 12: Verify search handles no results gracefully."""
        mock_components["store_instance"].search.return_value = []

        result = runner.invoke(cli, ["search", "nonexistent"])

        assert result.exit_code == 0
        assert "No matching memories" in result.output

    def test_stats_command(self, runner: CliRunner, mock_components: dict) -> None:
        """Waypoint 12: Verify stats command works."""
        result = runner.invoke(cli, ["stats"])

        assert result.exit_code == 0
        assert "Recall Statistics" in result.output
        assert "Total chunks: 10" in result.output
        assert "recall_384d" in result.output
        assert "mock-embedder" in result.output
        assert "384D" in result.output

    def test_setup_qdrant_running(self, runner: CliRunner) -> None:
        """Waypoint 12: Verify setup-qdrant detects running instance."""
        with patch("recall.cli.main.load_config") as mock_config, patch(
            "recall.cli.main.QdrantBackend"
        ) as mock_backend:
            mock_config.return_value = MagicMock(qdrant_host="localhost", qdrant_port=6333)
            mock_backend_instance = MagicMock()
            mock_backend_instance.health_check.return_value = True
            mock_backend.return_value = mock_backend_instance

            result = runner.invoke(cli, ["setup-qdrant"])

            assert result.exit_code == 0
            assert "Qdrant is running" in result.output
            assert "localhost:6333" in result.output

    def test_setup_qdrant_not_running(self, runner: CliRunner) -> None:
        """Waypoint 12: Verify setup-qdrant provides instructions when not running."""
        with patch("recall.cli.main.load_config") as mock_config, patch(
            "recall.cli.main.QdrantBackend"
        ) as mock_backend:
            mock_config.return_value = MagicMock(qdrant_host="localhost", qdrant_port=6333)
            mock_backend.side_effect = Exception("Connection refused")

            result = runner.invoke(cli, ["setup-qdrant"])

            assert result.exit_code == 1
            assert "Qdrant not accessible" in result.output
            assert "docker run" in result.output
            assert "docker-compose" in result.output

    def test_ingest_auto_detects_content_type(
        self, runner: CliRunner, mock_components: dict
    ) -> None:
        """Waypoint 12: Verify ingest auto-detects content type when not specified."""
        result = runner.invoke(
            cli,
            ["ingest", "# Markdown content", "-s", "test-session"],
        )

        assert result.exit_code == 0
        assert "auto-detected" in result.output
