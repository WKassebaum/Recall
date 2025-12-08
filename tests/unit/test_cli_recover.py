"""Tests for the recover CLI command.

Tests auto-recovery functionality for Qdrant corruption.
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from recall.cli import recover


class TestRecoverHealthChecks:
    """Test health check functions."""

    def test_check_qdrant_health_success(self) -> None:
        """Verify health check succeeds when Qdrant is running."""
        with patch("recall.cli.recover.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = recover.check_qdrant_health("localhost", 6337)

            assert result is True
            mock_get.assert_called()

    def test_check_qdrant_health_fallback_to_collections(self) -> None:
        """Verify health check falls back to /collections endpoint."""
        with patch("recall.cli.recover.requests.get") as mock_get:
            # First call to /health returns 500, second to /collections returns 200
            mock_health_response = MagicMock()
            mock_health_response.status_code = 500
            mock_collections_response = MagicMock()
            mock_collections_response.status_code = 200
            mock_get.side_effect = [mock_health_response, mock_collections_response]

            result = recover.check_qdrant_health("localhost", 6337)

            assert result is True
            assert mock_get.call_count == 2

    def test_check_qdrant_health_failure(self) -> None:
        """Verify health check fails when Qdrant is not running."""
        with patch("recall.cli.recover.requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")

            result = recover.check_qdrant_health("localhost", 6337)

            assert result is False

    def test_check_docker_container_status_running(self) -> None:
        """Verify container status detection when running."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Up 2 hours", returncode=0)

            result = recover.check_docker_container_status("recall-qdrant-6337")

            assert result == "running"

    def test_check_docker_container_status_exited(self) -> None:
        """Verify container status detection when exited."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Exited (0) 5 minutes ago", returncode=0)

            result = recover.check_docker_container_status("recall-qdrant-6337")

            assert result == "exited"

    def test_check_docker_container_status_not_found(self) -> None:
        """Verify container status detection when container doesn't exist."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=0)

            result = recover.check_docker_container_status("recall-qdrant-6337")

            assert result == "not_found"

    def test_check_docker_container_status_unknown(self) -> None:
        """Verify container status detection for unknown status."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Restarting", returncode=0)

            result = recover.check_docker_container_status("recall-qdrant-6337")

            assert result == "unknown"

    def test_check_docker_container_status_error(self) -> None:
        """Verify container status detection handles subprocess error."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "docker")

            result = recover.check_docker_container_status("recall-qdrant-6337")

            assert result == "not_found"

    def test_check_collection_accessible_success(self) -> None:
        """Verify collection accessibility check succeeds."""
        with patch.object(recover, "QdrantClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get_collection.return_value = MagicMock(points_count=100)
            mock_client.return_value = mock_instance

            result = recover.check_collection_accessible("localhost", 6337, "recall_768d")

            assert result is True
            mock_instance.get_collection.assert_called_with(collection_name="recall_768d")

    def test_check_collection_accessible_failure(self) -> None:
        """Verify collection accessibility check fails on corruption."""
        with patch("recall.cli.recover.QdrantClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get_collection.side_effect = Exception("Segment corrupted")
            mock_client.return_value = mock_instance

            result = recover.check_collection_accessible("localhost", 6337, "recall_768d")

            assert result is False

    def test_check_collection_accessible_not_exists(self) -> None:
        """Verify collection accessibility returns True for non-existent collection."""
        from qdrant_client.http import exceptions as qdrant_exceptions

        with patch("recall.cli.recover.QdrantClient") as mock_client:
            mock_instance = MagicMock()
            # UnexpectedResponse means collection doesn't exist (not an error)
            mock_instance.get_collection.side_effect = qdrant_exceptions.UnexpectedResponse(
                status_code=404,
                reason_phrase="Not Found",
                content=b"Collection not found",
                headers={},
            )
            mock_client.return_value = mock_instance

            result = recover.check_collection_accessible(
                "localhost", 6337, "nonexistent_collection"
            )

            # Non-existent collection is OK (returns True)
            assert result is True


class TestGetLatestBackup:
    """Test get_latest_backup function."""

    def test_get_latest_backup_from_symlink(self, tmp_path) -> None:
        """Verify getting backup from latest-good-backup symlink."""
        # Create a backup file
        backup_file = tmp_path / "backup-20251010.tar.gz"
        backup_file.write_text("backup data")

        # Create the symlink
        symlink = tmp_path / "latest-good-backup.tar.gz"
        symlink.symlink_to(backup_file)

        result = recover.get_latest_backup(tmp_path)

        assert result is not None
        assert result == backup_file.resolve()

    def test_get_latest_backup_from_automated_recent(self, tmp_path) -> None:
        """Verify getting backup from automated/recent directory."""
        # Create automated/recent directory
        recent_dir = tmp_path / "automated" / "recent"
        recent_dir.mkdir(parents=True)

        # Create backup files with different modification times
        backup1 = recent_dir / "backup-older.tar.gz"
        backup1.write_text("old backup")

        import time

        time.sleep(0.01)  # Ensure different mtime

        backup2 = recent_dir / "backup-newer.tar.gz"
        backup2.write_text("new backup")

        result = recover.get_latest_backup(tmp_path)

        assert result is not None
        assert result.name == "backup-newer.tar.gz"

    def test_get_latest_backup_from_root(self, tmp_path) -> None:
        """Verify getting backup from backup root directory."""
        # Create backup file in root (no automated/recent directory)
        backup_file = tmp_path / "root-backup.tar.gz"
        backup_file.write_text("backup data")

        result = recover.get_latest_backup(tmp_path)

        assert result is not None
        assert result.name == "root-backup.tar.gz"

    def test_get_latest_backup_none_found(self, tmp_path) -> None:
        """Verify None returned when no backups found."""
        result = recover.get_latest_backup(tmp_path)

        assert result is None

    def test_get_latest_backup_no_symlink_uses_root(self, tmp_path) -> None:
        """Verify fallback to root when no symlink exists."""
        # Create only a backup in root (no symlink)
        backup_file = tmp_path / "fallback-backup.tar.gz"
        backup_file.write_text("fallback data")

        result = recover.get_latest_backup(tmp_path)

        assert result is not None
        assert result.name == "fallback-backup.tar.gz"


class TestRecoverCommand:
    """Test the recover CLI command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create Click test runner."""
        return CliRunner()

    def test_recover_healthy_system(self, runner: CliRunner) -> None:
        """Verify recover command when system is healthy."""
        with patch("recall.cli.recover.check_qdrant_health") as mock_health, patch(
            "recall.cli.recover.check_docker_container_status"
        ) as mock_docker, patch(
            "recall.cli.recover.check_collection_accessible"
        ) as mock_collection:
            mock_health.return_value = True
            mock_docker.return_value = "running"
            mock_collection.return_value = True

            # Import the command
            from recall.cli.main import cli

            result = runner.invoke(cli, ["recover"])

            # Should exit successfully when healthy (reports "All health checks passed")
            assert result.exit_code == 0
            assert "All health checks passed" in result.output
