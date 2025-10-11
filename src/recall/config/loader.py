# Copyright 2025 William Kassebaum
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Configuration loader."""

from pathlib import Path
from typing import Any

import yaml


class Config:
    """SemVecMem configuration."""

    def __init__(self, config_data: dict[str, Any]) -> None:
        """
        Initialize configuration.

        Args:
            config_data: Parsed YAML configuration
        """
        self._data = config_data

    @classmethod
    def from_file(cls, config_path: str | Path) -> "Config":
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config.yaml

        Returns:
            Loaded configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path) as f:
            config_data = yaml.safe_load(f)

        return cls(config_data)

    @property
    def embedder_model(self) -> str:
        """Get embedder model name."""
        return str(
            self._data.get("embedder", {}).get("model", "Snowflake/snowflake-arctic-embed-m")
        )

    @property
    def fallback_enabled(self) -> bool:
        """Check if fallback is enabled."""
        return bool(self._data.get("fallback", {}).get("enabled", False))

    @property
    def fallback_model(self) -> str | None:
        """Get fallback model name."""
        if not self.fallback_enabled:
            return None
        model = self._data.get("fallback", {}).get("model")
        return str(model) if model else None

    @property
    def qdrant_host(self) -> str:
        """Get Qdrant host."""
        return str(self._data.get("qdrant", {}).get("host", "localhost"))

    @property
    def qdrant_port(self) -> int:
        """Get Qdrant port."""
        return int(self._data.get("qdrant", {}).get("port", 6333))

    @property
    def auto_create_collections(self) -> bool:
        """Check if collections should be auto-created."""
        return bool(self._data.get("collections", {}).get("auto_create", True))

    @property
    def max_chunk_size(self) -> int:
        """Get maximum chunk size in tokens."""
        return int(self._data.get("chunking", {}).get("max_chunk_size", 512))

    @property
    def chunk_overlap(self) -> int:
        """Get chunk overlap in tokens."""
        return int(self._data.get("chunking", {}).get("overlap", 50))

    @property
    def supported_languages(self) -> list[str]:
        """Get list of supported languages."""
        langs = self._data.get("chunking", {}).get(
            "languages", ["python", "javascript", "typescript"]
        )
        return [str(lang) for lang in langs]

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return str(self._data.get("logging", {}).get("level", "INFO"))


def load_config(config_path: str | Path = "config.yaml") -> Config:
    """
    Load configuration from file.

    Args:
        config_path: Path to config file (default: config.yaml)

    Returns:
        Loaded configuration
    """
    return Config.from_file(config_path)
