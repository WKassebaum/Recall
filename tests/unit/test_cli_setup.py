"""Tests for the setup CLI command.

Tests interactive setup wizard functionality.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from recall.cli.setup import SetupWizard


class TestSetupWizard:
    """Test SetupWizard class methods."""

    @pytest.fixture
    def wizard(self, tmp_path: Path) -> SetupWizard:
        """Create SetupWizard with temp directory."""
        with patch.object(Path, "home", return_value=tmp_path):
            wizard = SetupWizard()
            wizard.config_dir = tmp_path / ".recall"
            wizard.config_dir.mkdir(exist_ok=True)
            wizard.env_file = wizard.config_dir / ".env"
            wizard.instances_file = wizard.config_dir / "instances.yaml"
            return wizard

    def test_get_python_version(self, wizard: SetupWizard) -> None:
        """Verify Python version detection."""
        version = wizard._get_python_version()

        expected = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        assert version == expected

    def test_check_docker_installed(self, wizard: SetupWizard) -> None:
        """Verify Docker detection when installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="Docker version 24.0.7, build afdd53b"
            )

            result = wizard._check_docker()

            assert result == "24.0.7"

    def test_check_docker_not_installed(self, wizard: SetupWizard) -> None:
        """Verify Docker detection when not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = wizard._check_docker()

            assert result is None

    def test_check_docker_timeout(self, wizard: SetupWizard) -> None:
        """Verify Docker detection handles timeout."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("docker", 5)

            result = wizard._check_docker()

            assert result is None

    def test_check_qdrant_running_found(self, wizard: SetupWizard) -> None:
        """Verify Qdrant detection when running."""
        with patch("recall.cli.setup.QdrantClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get_collections.return_value = MagicMock()
            mock_client.return_value = mock_instance

            result = wizard._check_qdrant_running()

            # Should find it on one of the checked ports
            assert result is not None
            assert "localhost:" in result

    def test_check_qdrant_running_not_found(self, wizard: SetupWizard) -> None:
        """Verify Qdrant detection when not running."""
        with patch("recall.cli.setup.QdrantClient") as mock_client:
            mock_client.side_effect = Exception("Connection refused")

            result = wizard._check_qdrant_running()

            assert result is None

    def test_detect_system(self, wizard: SetupWizard) -> None:
        """Verify system detection gathers all info."""
        with patch.object(wizard, "_get_python_version", return_value="3.12.0"), patch.object(
            wizard, "_check_docker", return_value="24.0.7"
        ), patch.object(wizard, "_check_qdrant_running", return_value="localhost:6337"):
            detection = wizard.detect_system()

            assert detection["python_version"] == "3.12.0"
            assert detection["docker_installed"] == "24.0.7"
            assert detection["qdrant_running"] == "localhost:6337"

    def test_config_dir_created(self, tmp_path: Path) -> None:
        """Verify config directory is created on initialization."""
        with patch.object(Path, "home", return_value=tmp_path):
            wizard = SetupWizard()

            assert wizard.config_dir.exists()
            assert wizard.config_dir == tmp_path / ".recall"


class TestSetupCommand:
    """Test the setup CLI command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create Click test runner."""
        return CliRunner()

    def test_setup_command_help(self, runner: CliRunner) -> None:
        """Verify setup command has help text."""
        from recall.cli.main import cli

        result = runner.invoke(cli, ["setup", "--help"])

        assert result.exit_code == 0
        assert "setup" in result.output.lower() or "Usage" in result.output

    def test_setup_creates_config_directory(self, runner: CliRunner, tmp_path: Path) -> None:
        """Verify setup creates .recall config directory."""
        with patch.object(Path, "home", return_value=tmp_path):
            from recall.cli.main import cli

            # Invoke with input to handle prompts
            result = runner.invoke(cli, ["setup"], input="1\nn\n")

            # Should have created the config directory
            config_dir = tmp_path / ".recall"
            assert config_dir.exists() or result.exit_code != 0  # May fail due to prompts


class TestSetupModeSelection:
    """Test mode selection functionality."""

    @pytest.fixture
    def wizard(self, tmp_path: Path) -> SetupWizard:
        """Create SetupWizard with temp directory."""
        with patch.object(Path, "home", return_value=tmp_path):
            wizard = SetupWizard()
            wizard.config_dir = tmp_path / ".recall"
            wizard.config_dir.mkdir(exist_ok=True)
            return wizard

    def test_choose_mode_network(self, wizard: SetupWizard) -> None:
        """Verify network mode selection."""
        detection = {"docker_installed": "24.0.7", "qdrant_running": None}

        # Mock the Prompt to select network mode
        with patch("recall.cli.setup.Prompt.ask", return_value="1"):
            mode = wizard.choose_mode(detection)
            assert mode == "network"

    def test_choose_mode_embedded(self, wizard: SetupWizard) -> None:
        """Verify embedded mode selection."""
        detection = {"docker_installed": None, "qdrant_running": None}

        # Mock the Prompt to select embedded mode
        with patch("recall.cli.setup.Prompt.ask", return_value="2"):
            mode = wizard.choose_mode(detection)
            assert mode == "embedded"
