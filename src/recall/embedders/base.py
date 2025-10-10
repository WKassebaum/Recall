"""Base embedder interface."""

from typing import Protocol

import numpy as np
import numpy.typing as npt


class EmbedderModel(Protocol):
    """Protocol for embedding models."""

    @property
    def name(self) -> str:
        """Model name."""
        ...

    @property
    def dimension(self) -> int:
        """Embedding dimension."""
        ...

    def encode(self, text: str) -> npt.NDArray[np.float32]:
        """
        Encode text to embedding vector.

        Args:
            text: Text to encode

        Returns:
            Embedding vector of shape (dimension,)
        """
        ...
