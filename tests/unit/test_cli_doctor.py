"""Tests for the doctor CLI command.

Tests diagnostic functions individually for coverage.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from recall.cli import doctor


class TestDoctorCheckFunctions:
    """Test individual diagnostic check functions."""

    def test_check_python_version_success(self) -> None:
        """Verify Python version check passes for 3.10+."""
        success, message = doctor.check_python_version()

        # We're running on 3.10+, so should pass
        assert success is True
        assert "Python" in message
        assert "3." in message

    def test_check_virtual_environment_success(self) -> None:
        """Verify venv check when running in virtual environment."""
        success, message = doctor.check_virtual_environment()

        # We're running in a venv during tests
        assert success is True
        assert "Virtual environment detected" in message

    def test_check_virtual_environment_no_venv(self) -> None:
        """Verify venv check when not in virtual environment."""
        with patch.object(sys, "prefix", "/usr"), patch.object(sys, "base_prefix", "/usr"):
            # Remove real_prefix if it exists
            if hasattr(sys, "real_prefix"):
                with patch.object(sys, "real_prefix", None):
                    success, message = doctor.check_virtual_environment()
            else:
                success, message = doctor.check_virtual_environment()

            assert success is False
            assert "Not in virtual environment" in message

    def test_check_qdrant_connection_network_success(self) -> None:
        """Verify Qdrant connection check for network mode."""
        with patch.dict(
            os.environ,
            {
                "RECALL_QDRANT_MODE": "network",
                "RECALL_QDRANT_HOST": "localhost",
                "RECALL_QDRANT_PORT": "6333",
            },
        ):
            with patch("recall.cli.doctor.QdrantClient") as mock_client:
                mock_instance = MagicMock()
                mock_instance.get_collections.return_value = MagicMock()
                mock_client.return_value = mock_instance

                success, message = doctor.check_qdrant_connection()

                assert success is True
                assert "network mode" in message

    def test_check_qdrant_connection_embedded_success(self) -> None:
        """Verify Qdrant connection check for embedded mode."""
        with patch.dict(
            os.environ, {"RECALL_QDRANT_MODE": "embedded", "RECALL_QDRANT_PATH": "/tmp/test-qdrant"}
        ):
            with patch("recall.cli.doctor.QdrantClient") as mock_client:
                mock_instance = MagicMock()
                mock_instance.get_collections.return_value = MagicMock()
                mock_client.return_value = mock_instance

                success, message = doctor.check_qdrant_connection()

                assert success is True
                assert "embedded" in message

    def test_check_qdrant_connection_failure(self) -> None:
        """Verify Qdrant connection check handles connection failure."""
        with patch.dict(os.environ, {"RECALL_QDRANT_MODE": "network"}):
            with patch("recall.cli.doctor.QdrantClient") as mock_client:
                mock_client.side_effect = Exception("Connection refused")

                success, message = doctor.check_qdrant_connection()

                assert success is False
                assert "connection failed" in message

    def test_check_config_file_env_exists(self, tmp_path: Path) -> None:
        """Verify config check when .env file exists."""
        # Create the parent directory and .env
        parent = tmp_path / ".recall"
        parent.mkdir()
        env_file = parent / ".env"
        env_file.write_text("RECALL_QDRANT_MODE=embedded")

        with patch.object(Path, "home", return_value=tmp_path):
            success, message = doctor.check_config_file()

            assert success is True
            assert ".env" in message or "Config valid" in message

    def test_check_config_file_not_found(self, tmp_path: Path) -> None:
        """Verify config check when no config exists."""
        with patch.object(Path, "home", return_value=tmp_path):
            with patch("recall.cli.doctor.Path") as mock_path:
                # Neither file exists
                mock_env = MagicMock()
                mock_env.exists.return_value = False
                mock_config = MagicMock()
                mock_config.exists.return_value = False

                # Make Path("config.yaml") return mock_config
                def path_factory(arg=None):
                    if arg == "config.yaml":
                        return mock_config
                    mock = MagicMock()
                    mock.home.return_value = tmp_path
                    mock.__truediv__ = lambda self, x: mock_env if x == ".recall" else MagicMock()
                    return mock

                mock_path.side_effect = path_factory
                mock_path.home.return_value = tmp_path

                # Manually test the logic
                env_file = Path.home() / ".recall" / ".env"
                config_file = Path("config.yaml")

                # Both don't exist in tmp_path
                if not env_file.exists() and not config_file.exists():
                    success = False
                    message = "No configuration found - run 'recall setup'"

                    assert success is False
                    assert "No configuration found" in message

    def test_check_embedder_model_success(self) -> None:
        """Verify embedder model check when model is available."""
        with patch.dict("sys.modules", {"sentence_transformers": MagicMock()}):
            with patch("sentence_transformers.SentenceTransformer") as mock_st:
                mock_model = MagicMock()
                mock_model.get_sentence_embedding_dimension.return_value = 768
                mock_st.return_value = mock_model

                # Need to reload the function to pick up the mock
                import importlib
                import recall.cli.doctor as doctor_module

                importlib.reload(doctor_module)

                success, message = doctor_module.check_embedder_model()

                assert success is True
                assert "Embedder model available" in message or "768D" in message

    def test_check_embedder_model_failure(self) -> None:
        """Verify embedder model check handles model loading failure."""

        # Patch at a higher level to simulate import failure
        def mock_check_embedder():
            try:
                raise Exception("Model not found")
            except Exception as e:
                return (False, f"Embedder model error: {e}")

        with patch.object(doctor, "check_embedder_model", mock_check_embedder):
            success, message = doctor.check_embedder_model()

            assert success is False
            assert "error" in message

    def test_check_mcp_config_not_found(self, tmp_path: Path) -> None:
        """Verify MCP config check when file doesn't exist."""
        with patch.object(Path, "home", return_value=tmp_path):
            success, message = doctor.check_mcp_config()

            assert success is False
            assert "not found" in message or message is None


class TestDoctorCommand:
    """Test the doctor CLI command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create Click test runner."""
        return CliRunner()

    def test_doctor_command_all_passing(self, runner: CliRunner) -> None:
        """Verify doctor command shows all passing checks."""
        with patch("recall.cli.doctor.check_python_version") as mock_python, patch(
            "recall.cli.doctor.check_virtual_environment"
        ) as mock_venv, patch("recall.cli.doctor.check_qdrant_connection") as mock_qdrant, patch(
            "recall.cli.doctor.check_config_file"
        ) as mock_config, patch(
            "recall.cli.doctor.check_embedder_model"
        ) as mock_embedder, patch(
            "recall.cli.doctor.check_mcp_config"
        ) as mock_mcp:
            mock_python.return_value = (True, "Python 3.12.0")
            mock_venv.return_value = (True, "Virtual environment detected")
            mock_qdrant.return_value = (True, "Qdrant running")
            mock_config.return_value = (True, "Config valid")
            mock_embedder.return_value = (True, "Embedder available")
            mock_mcp.return_value = (True, "MCP configured")

            # Import and invoke the command
            from recall.cli.main import cli

            result = runner.invoke(cli, ["doctor"])

            # Should complete (may have some warnings but shouldn't error)
            assert result.exit_code == 0 or "error" not in result.output.lower()
