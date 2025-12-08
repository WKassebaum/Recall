"""Tests for the migrate-mode CLI command."""

import sys
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


class TestModeMigration:
    """Test ModeMigration class."""

    def test_init_embedded_to_network(self):
        """Verify initialization for embedded to network migration."""
        with patch("recall.cli.migrate_mode.QdrantBackend") as mock_backend:
            mock_backend.return_value = MagicMock()

            from recall.cli.migrate_mode import ModeMigration

            migration = ModeMigration(
                source_mode="embedded",
                target_mode="network",
                source_path="~/.recall/qdrant",
                target_host="localhost",
                target_port=6337,
            )

            assert migration.source_mode == "embedded"
            assert migration.target_mode == "network"
            # Should have created two backends
            assert mock_backend.call_count == 2

    def test_init_network_to_embedded(self):
        """Verify initialization for network to embedded migration."""
        with patch("recall.cli.migrate_mode.QdrantBackend") as mock_backend:
            mock_backend.return_value = MagicMock()

            from recall.cli.migrate_mode import ModeMigration

            migration = ModeMigration(
                source_mode="network",
                target_mode="embedded",
                source_host="localhost",
                source_port=6333,
                target_path="~/.recall/qdrant-new",
            )

            assert migration.source_mode == "network"
            assert migration.target_mode == "embedded"
            assert mock_backend.call_count == 2

    def test_migrate_no_collections(self):
        """Verify migrate handles empty source."""
        with patch("recall.cli.migrate_mode.QdrantBackend") as mock_backend:
            mock_source = MagicMock()
            mock_source.client.get_collections.return_value = MagicMock(collections=[])
            mock_target = MagicMock()
            mock_backend.side_effect = [mock_source, mock_target]

            from recall.cli.migrate_mode import ModeMigration

            migration = ModeMigration(source_mode="embedded", target_mode="network")
            stats = migration.migrate()

            assert stats == {"total": 0, "migrated": 0, "failed": 0}

    def test_migrate_dry_run(self):
        """Verify dry run mode doesn't modify data."""
        with patch("recall.cli.migrate_mode.QdrantBackend") as mock_backend:
            mock_collection = MagicMock()
            mock_collection.name = "recall_768d"

            mock_collection_info = MagicMock()
            mock_collection_info.points_count = 100
            mock_collection_info.config.params.vectors.size = 768
            mock_collection_info.config.params.vectors.distance = "Cosine"

            mock_source = MagicMock()
            mock_source.client.get_collections.return_value = MagicMock(
                collections=[mock_collection]
            )
            mock_source.client.get_collection.return_value = mock_collection_info

            mock_target = MagicMock()
            mock_backend.side_effect = [mock_source, mock_target]

            from recall.cli.migrate_mode import ModeMigration

            migration = ModeMigration(source_mode="embedded", target_mode="network")
            stats = migration.migrate(dry_run=True)

            # Dry run should not create or upsert
            mock_target.client.create_collection.assert_not_called()
            mock_target.client.upsert.assert_not_called()
            assert stats["migrated"] == 100

    def test_migrate_connection_failure(self):
        """Verify migrate handles source connection failure."""
        with patch("recall.cli.migrate_mode.QdrantBackend") as mock_backend:
            mock_source = MagicMock()
            mock_source.client.get_collections.side_effect = Exception("Connection refused")
            mock_target = MagicMock()
            mock_backend.side_effect = [mock_source, mock_target]

            from recall.cli.migrate_mode import ModeMigration

            migration = ModeMigration(source_mode="embedded", target_mode="network")

            with pytest.raises(Exception, match="Connection refused"):
                migration.migrate()


class TestMigrateModeCommand:
    """Test migrate-mode CLI command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create Click test runner."""
        return CliRunner()

    def test_same_mode_error(self, runner: CliRunner):
        """Verify error when source and target modes are the same."""
        from recall.cli.migrate_mode import migrate_mode

        result = runner.invoke(migrate_mode, ["--from-mode", "embedded", "--to-mode", "embedded"])

        assert result.exit_code == 1
        assert "Source and target modes are the same" in result.output

    def test_dry_run_flag(self, runner: CliRunner):
        """Verify dry run flag works."""
        with patch("recall.cli.migrate_mode.ModeMigration") as mock_migration_class:
            mock_migration = MagicMock()
            mock_migration.migrate.return_value = {"total": 10, "migrated": 10, "failed": 0}
            mock_migration_class.return_value = mock_migration

            from recall.cli.migrate_mode import migrate_mode

            result = runner.invoke(
                migrate_mode,
                ["--from-mode", "embedded", "--to-mode", "network", "--dry-run"],
            )

            # Dry run doesn't require confirmation
            mock_migration.migrate.assert_called_once_with(dry_run=True)
            assert result.exit_code == 0

    def test_migration_cancelled(self, runner: CliRunner):
        """Verify migration can be cancelled."""
        from recall.cli.migrate_mode import migrate_mode

        # Answer 'n' to confirmation prompt
        result = runner.invoke(
            migrate_mode,
            ["--from-mode", "embedded", "--to-mode", "network"],
            input="n\n",
        )

        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()

    def test_migration_confirmed(self, runner: CliRunner):
        """Verify migration proceeds when confirmed."""
        with patch("recall.cli.migrate_mode.ModeMigration") as mock_migration_class:
            mock_migration = MagicMock()
            mock_migration.migrate.return_value = {"total": 10, "migrated": 10, "failed": 0}
            mock_migration_class.return_value = mock_migration

            from recall.cli.migrate_mode import migrate_mode

            # Answer 'y' to confirmation prompt
            result = runner.invoke(
                migrate_mode,
                ["--from-mode", "embedded", "--to-mode", "network"],
                input="y\n",
            )

            mock_migration.migrate.assert_called_once_with(dry_run=False)
            assert result.exit_code == 0

    def test_migration_failed_points(self, runner: CliRunner):
        """Verify exit code 1 when migration has failures."""
        with patch("recall.cli.migrate_mode.ModeMigration") as mock_migration_class:
            mock_migration = MagicMock()
            mock_migration.migrate.return_value = {"total": 10, "migrated": 5, "failed": 5}
            mock_migration_class.return_value = mock_migration

            from recall.cli.migrate_mode import migrate_mode

            result = runner.invoke(
                migrate_mode,
                ["--from-mode", "embedded", "--to-mode", "network"],
                input="y\n",
            )

            assert result.exit_code == 1

    def test_migration_exception(self, runner: CliRunner):
        """Verify exit code 1 on exception during migrate()."""
        with patch("recall.cli.migrate_mode.ModeMigration") as mock_migration_class:
            mock_migration = MagicMock()
            mock_migration.migrate.side_effect = Exception("Backend error")
            mock_migration_class.return_value = mock_migration

            from recall.cli.migrate_mode import migrate_mode

            result = runner.invoke(
                migrate_mode,
                ["--from-mode", "embedded", "--to-mode", "network"],
                input="y\n",
            )

            assert result.exit_code == 1
            assert "Migration failed" in result.output

    def test_custom_ports(self, runner: CliRunner):
        """Verify custom port options work."""
        with patch("recall.cli.migrate_mode.ModeMigration") as mock_migration_class:
            mock_migration = MagicMock()
            mock_migration.migrate.return_value = {"total": 0, "migrated": 0, "failed": 0}
            mock_migration_class.return_value = mock_migration

            from recall.cli.migrate_mode import migrate_mode

            result = runner.invoke(
                migrate_mode,
                [
                    "--from-mode",
                    "network",
                    "--to-mode",
                    "embedded",
                    "--source-port",
                    "6337",
                    "--target-path",
                    "/tmp/qdrant-new",
                    "--dry-run",
                ],
            )

            assert result.exit_code == 0
            # Check ModeMigration was called with correct args
            call_kwargs = mock_migration_class.call_args[1]
            assert call_kwargs["source_port"] == 6337
            assert call_kwargs["target_path"] == "/tmp/qdrant-new"
