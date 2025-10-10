"""Mock embedder for testing."""

import hashlib

import numpy as np
import numpy.typing as npt


class MockEmbedder:
    """
    Mock embedder for testing.

    Generates deterministic embeddings based on content hash.
    """

    def __init__(self, dimension: int, model_name: str = "mock"):
        """
        Initialize mock embedder.

        Args:
            dimension: Embedding dimension
            model_name: Model name for identification
        """
        self._dimension = dimension
        self._name = model_name

    @property
    def name(self) -> str:
        """Model name."""
        return self._name

    @property
    def dimension(self) -> int:
        """Embedding dimension."""
        return self._dimension

    def encode(self, text: str) -> npt.NDArray[np.float32]:
        """
        Generate deterministic embedding from text.

        Uses content hash to generate reproducible embeddings.

        Args:
            text: Text to encode

        Returns:
            Embedding vector of shape (dimension,)
        """
        # Use hash to generate deterministic values
        hash_bytes = hashlib.sha256(text.encode()).digest()

        # Convert to array of floats in range [0, 1]
        values = np.frombuffer(hash_bytes, dtype=np.uint8).astype(np.float32) / 255.0

        # Tile or truncate to desired dimension
        if len(values) < self._dimension:
            # Repeat values to reach dimension
            repeats = (self._dimension + len(values) - 1) // len(values)
            values = np.tile(values, repeats)[: self._dimension]
        else:
            values = values[: self._dimension]

        # Normalize to unit length (typical for embeddings)
        norm = np.linalg.norm(values)
        if norm > 0:
            values = values / norm

        return values
