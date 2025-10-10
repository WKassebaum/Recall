"""Ollama embedder integration."""

import json
from typing import Any

import httpx
import numpy as np
import numpy.typing as npt


class OllamaEmbedder:
    """
    Ollama embedder wrapper.

    Integrates with local Ollama instance for GPU-accelerated embeddings.
    """

    def __init__(
        self,
        model: str = "snowflake-arctic-embed:latest",
        host: str = "localhost",
        port: int = 11434,
    ) -> None:
        """
        Initialize Ollama embedder.

        Args:
            model: Ollama model name
            host: Ollama host
            port: Ollama port
        """
        self._model = model
        self._host = host
        self._port = port
        self._base_url = f"http://{host}:{port}"
        self._dimension: int | None = None
        self._name = f"ollama/{model}"

    @property
    def name(self) -> str:
        """Model name."""
        return self._name

    @property
    def dimension(self) -> int:
        """Embedding dimension."""
        if self._dimension is None:
            # Detect dimension on first call
            test_embedding = self.encode("test")
            self._dimension = len(test_embedding)
        return self._dimension

    def health_check(self) -> bool:
        """
        Check if Ollama is accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = httpx.get(f"{self._base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    def encode(self, text: str) -> npt.NDArray[np.float32]:
        """
        Encode text to embedding vector.

        Args:
            text: Text to encode

        Returns:
            Embedding vector of shape (dimension,)

        Raises:
            ConnectionError: If Ollama is not accessible
            RuntimeError: If embedding generation fails
        """
        try:
            response = httpx.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self._model, "prompt": text},
                timeout=30.0,
            )
            response.raise_for_status()

            data: dict[str, Any] = response.json()
            embedding = np.array(data["embedding"], dtype=np.float32)

            return embedding

        except httpx.ConnectError as e:
            raise ConnectionError(
                f"Failed to connect to Ollama at {self._base_url}. "
                f"Ensure Ollama is running with: brew services start ollama"
            ) from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Ollama returned error {e.response.status_code}: {e.response.text}"
            ) from e
        except (KeyError, json.JSONDecodeError) as e:
            raise RuntimeError(
                f"Failed to parse Ollama response. "
                f"Ensure model {self._model} is installed: ollama pull {self._model}"
            ) from e
