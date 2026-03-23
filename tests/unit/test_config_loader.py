"""
Waypoint 4: Configuration loader tests.

Validates YAML configuration loading and parsing.
"""

from pathlib import Path

import pytest

from recall.config.loader import Config, load_config


class TestConfigLoader:
    """Waypoint 4 tests - Configuration loader validation."""

    @pytest.fixture
    def config_path(self) -> Path:
        """Get path to project config.yaml."""
        return Path("config.yaml")

    def test_config_file_exists(self, config_path: Path) -> None:
        """Waypoint 4: Verify config file exists."""
        assert config_path.exists(), "config.yaml should exist in project root"

    def test_load_config(self, config_path: Path) -> None:
        """Waypoint 4: Verify configuration loads successfully."""
        config = load_config(config_path)
        assert isinstance(config, Config)

    def test_embedder_model_loaded(self, config_path: Path) -> None:
        """Waypoint 4: Verify embedder model is configured."""
        config = load_config(config_path)
        assert config.embedder_model == "nomic-ai/nomic-embed-text-v1.5"

    def test_qdrant_config_loaded(self, config_path: Path) -> None:
        """Waypoint 4: Verify Qdrant configuration is loaded."""
        config = load_config(config_path)
        assert config.qdrant_host == "localhost"
        assert config.qdrant_port == 6333

    def test_chunking_config_loaded(self, config_path: Path) -> None:
        """Waypoint 4: Verify chunking configuration is loaded."""
        config = load_config(config_path)
        assert config.max_chunk_size == 512
        assert config.chunk_overlap == 50
        assert "python" in config.supported_languages

    def test_fallback_config_loaded(self, config_path: Path) -> None:
        """Waypoint 4: Verify fallback configuration is loaded."""
        config = load_config(config_path)
        assert config.fallback_enabled is True
        assert config.fallback_model == "all-MiniLM-L6-v2"

    def test_auto_create_collections(self, config_path: Path) -> None:
        """Waypoint 4: Verify auto-create collections setting."""
        config = load_config(config_path)
        assert config.auto_create_collections is True

    def test_file_not_found_error(self) -> None:
        """Waypoint 4: Verify proper error when config file missing."""
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.yaml")
