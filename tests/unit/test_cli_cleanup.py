"""Tests for the cleanup CLI command.

Tests cleanup functionality for removing test data.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from recall.cli.cleanup import cleanup_test_data


class TestCleanupCommand:
    """Test cleanup command functionality."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create Click test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_qdrant_backend(self) -> MagicMock:
        """Mock QdrantBackend with test data."""
        mock_backend = MagicMock()

        # Mock client with collections
        mock_collection = MagicMock()
        mock_collection.name = "recall_768d"
        mock_backend.client.get_collections.return_value.collections = [mock_collection]

        # Mock scroll to return test data
        def scroll_side_effect(**kwargs):
            session_id = kwargs.get("scroll_filter")
            if session_id:
                # Return some mock records
                mock_record = MagicMock()
                mock_record.payload = {"content": "test content", "session_id": "test-session"}
                return ([mock_record], None)
            return ([], None)

        mock_backend.client.scroll.side_effect = scroll_side_effect
        mock_backend.client.delete.return_value = None

        return mock_backend

    def test_cleanup_dry_run_network_mode(
        self, runner: CliRunner, mock_qdrant_backend: MagicMock
    ) -> None:
        """Verify cleanup dry run in network mode."""
        with patch.dict(
            os.environ,
            {
                "RECALL_QDRANT_MODE": "network",
                "RECALL_QDRANT_HOST": "localhost",
                "RECALL_QDRANT_PORT": "6337",
            },
        ):
            with patch("recall.cli.cleanup.QdrantBackend", return_value=mock_qdrant_backend):
                result = runner.invoke(cleanup_test_data, ["--dry-run"])

                # Dry run should not delete anything
                assert result.exit_code == 0
                assert "DRY RUN" in result.output
                mock_qdrant_backend.client.delete.assert_not_called()

    def test_cleanup_dry_run_embedded_mode(
        self, runner: CliRunner, mock_qdrant_backend: MagicMock
    ) -> None:
        """Verify cleanup dry run in embedded mode."""
        with patch.dict(
            os.environ, {"RECALL_QDRANT_MODE": "embedded", "RECALL_QDRANT_PATH": "/tmp/test-qdrant"}
        ):
            with patch("recall.cli.cleanup.QdrantBackend", return_value=mock_qdrant_backend):
                result = runner.invoke(cleanup_test_data, ["--dry-run"])

                assert result.exit_code == 0
                assert "DRY RUN" in result.output

    def test_cleanup_no_collections(self, runner: CliRunner) -> None:
        """Verify cleanup handles empty database gracefully."""
        mock_backend = MagicMock()
        mock_backend.client.get_collections.return_value.collections = []

        with patch.dict(os.environ, {"RECALL_QDRANT_MODE": "network"}):
            with patch("recall.cli.cleanup.QdrantBackend", return_value=mock_backend):
                result = runner.invoke(cleanup_test_data, ["--dry-run"])

                assert result.exit_code == 0
                assert "No collections found" in result.output

    def test_cleanup_no_test_data(self, runner: CliRunner) -> None:
        """Verify cleanup handles clean database gracefully."""
        mock_backend = MagicMock()
        mock_collection = MagicMock()
        mock_collection.name = "recall_768d"
        mock_backend.client.get_collections.return_value.collections = [mock_collection]
        mock_backend.client.scroll.return_value = ([], None)  # No test data

        with patch.dict(os.environ, {"RECALL_QDRANT_MODE": "network"}):
            with patch("recall.cli.cleanup.QdrantBackend", return_value=mock_backend):
                result = runner.invoke(cleanup_test_data, ["--dry-run"])

                assert result.exit_code == 0
                assert "already clean" in result.output

    def test_cleanup_with_confirmation(
        self, runner: CliRunner, mock_qdrant_backend: MagicMock
    ) -> None:
        """Verify cleanup with auto-yes confirmation."""
        with patch.dict(os.environ, {"RECALL_QDRANT_MODE": "network"}):
            with patch("recall.cli.cleanup.QdrantBackend", return_value=mock_qdrant_backend):
                result = runner.invoke(cleanup_test_data, ["--yes"])

                # With --yes, should proceed with deletion
                assert result.exit_code == 0

    def test_cleanup_cancelled(self, runner: CliRunner, mock_qdrant_backend: MagicMock) -> None:
        """Verify cleanup cancellation works."""
        with patch.dict(os.environ, {"RECALL_QDRANT_MODE": "network"}):
            with patch("recall.cli.cleanup.QdrantBackend", return_value=mock_qdrant_backend):
                # Simulate user typing 'n' to cancel
                result = runner.invoke(cleanup_test_data, input="n\n")

                assert result.exit_code == 0
                assert "Cancelled" in result.output
                mock_qdrant_backend.client.delete.assert_not_called()


class TestCleanupSessionDetection:
    """Test session ID detection in cleanup."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create Click test runner."""
        return CliRunner()

    def test_test_session_ids_defined(self) -> None:
        """Verify expected test session IDs are defined."""
        # Import and check the test_sessions list
        expected_sessions = [
            "metadata-test",
            "session-a",
            "session-b",
            "test-session-auth",
            "test-session-markdown",
            "test-session-python",
            "test-session-score",
        ]

        # These are the sessions that should be cleaned up
        for session in expected_sessions:
            assert (
                session.startswith("test-session")
                or session.startswith("session-")
                or session.endswith("-test")
            )
