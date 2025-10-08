"""Sentence-Transformers embedder integration."""

import numpy as np
import numpy.typing as npt
from sentence_transformers import SentenceTransformer


class SentenceTransformerEmbedder:
    """
    Sentence-Transformers embedder wrapper.

    Uses HuggingFace models with automatic GPU acceleration (Metal on macOS).
    """

    def __init__(self, model_name: str = "Snowflake/snowflake-arctic-embed-m") -> None:
        """
        Initialize Sentence-Transformer embedder.

        Args:
            model_name: HuggingFace model name
        """
        self._model_name = model_name
        self._model = SentenceTransformer(model_name)
        dim = self._model.get_sentence_embedding_dimension()
        if dim is None:
            raise ValueError(f"Could not determine dimension for model {model_name}")
        self._dimension = dim

    @property
    def name(self) -> str:
        """Model name."""
        return self._model_name

    @property
    def dimension(self) -> int:
        """Embedding dimension."""
        return self._dimension

    def encode(self, text: str) -> npt.NDArray[np.float32]:
        """
        Encode text to embedding vector.

        Args:
            text: Text to encode

        Returns:
            Embedding vector of shape (dimension,)
        """
        # SentenceTransformer.encode returns ndarray
        embedding = self._model.encode(text, convert_to_numpy=True)

        # Ensure it's the right dtype and shape
        if not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding, dtype=np.float32)
        elif embedding.dtype != np.float32:
            embedding = embedding.astype(np.float32)

        # Ensure 1D shape
        if len(embedding.shape) > 1:
            embedding = embedding.flatten()

        return embedding
