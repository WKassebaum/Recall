"""
Waypoint 3: Sentence-Transformers embedder integration test.

Validates HuggingFace model loading and embedding generation.
"""

import numpy as np
import pytest

from recall.embedders.sentence_transformer import SentenceTransformerEmbedder


class TestSentenceTransformerEmbedder:
    """Waypoint 3 tests - Sentence-Transformers embedder validation."""

    @pytest.fixture
    def embedder(self) -> SentenceTransformerEmbedder:
        """Create Sentence-Transformer embedder."""
        return SentenceTransformerEmbedder(model_name="Snowflake/snowflake-arctic-embed-m")

    def test_model_loads(self, embedder: SentenceTransformerEmbedder) -> None:
        """Waypoint 3: Verify model loads from HuggingFace cache."""
        assert embedder.name == "Snowflake/snowflake-arctic-embed-m"
        assert embedder.dimension == 768

    def test_embedding_generation(self, embedder: SentenceTransformerEmbedder) -> None:
        """Waypoint 3: Verify embeddings are generated correctly."""
        text = "def authenticate_user(username, password):"
        embedding = embedder.encode(text)

        # Verify embedding properties
        assert isinstance(embedding, np.ndarray)
        assert embedding.dtype == np.float32
        assert len(embedding.shape) == 1
        assert len(embedding) == 768

    def test_dimension_detection(self, embedder: SentenceTransformerEmbedder) -> None:
        """Waypoint 3: Verify dimension is detected correctly."""
        # Arctic embed-m should be 768D
        assert embedder.dimension == 768

    def test_determinism(self, embedder: SentenceTransformerEmbedder) -> None:
        """Waypoint 3: Verify embeddings are consistent for same input."""
        text = "class DatabaseConnection:"
        emb1 = embedder.encode(text)
        emb2 = embedder.encode(text)

        # Should be identical (deterministic)
        assert np.allclose(emb1, emb2, atol=1e-6)

    def test_different_texts_different_embeddings(
        self, embedder: SentenceTransformerEmbedder
    ) -> None:
        """Waypoint 3: Verify different texts produce different embeddings."""
        text1 = "authentication code"
        text2 = "database connection"

        emb1 = embedder.encode(text1)
        emb2 = embedder.encode(text2)

        # Embeddings should be different
        cosine_sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        assert cosine_sim < 0.95  # Not too similar

    def test_normalized_embeddings(self, embedder: SentenceTransformerEmbedder) -> None:
        """Waypoint 3: Verify embeddings are normalized (sentence-transformers default)."""
        text = "test normalization"
        embedding = embedder.encode(text)

        norm = np.linalg.norm(embedding)
        assert np.isclose(norm, 1.0, atol=0.1)  # Should be close to unit length
