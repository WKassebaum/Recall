"""
Waypoint 3: Ollama embedder integration test.

Validates Ollama connectivity and embedding generation.

NOTE: These tests are skipped because we're using sentence-transformers
instead of Ollama for embeddings. Ollama is only used for LLM reasoning.
"""

import numpy as np
import pytest

from recall.embedders.ollama import OllamaEmbedder

pytestmark = pytest.mark.skip(reason="Using sentence-transformers for embeddings, not Ollama")


class TestOllamaEmbedder:
    """Waypoint 3 tests - Ollama embedder validation."""

    @pytest.fixture
    def embedder(self) -> OllamaEmbedder:
        """Create Ollama embedder."""
        return OllamaEmbedder(
            model="snowflake-arctic-embed:latest",
            host="localhost",
            port=11434,
        )

    def test_ollama_health_check(self, embedder: OllamaEmbedder) -> None:
        """Waypoint 3: Verify Ollama is accessible."""
        assert embedder.health_check(), (
            "Ollama health check failed. "
            "Ensure Ollama is running with: brew services start ollama"
        )

    def test_embedding_generation(self, embedder: OllamaEmbedder) -> None:
        """Waypoint 3: Verify embeddings are generated correctly."""
        text = "def authenticate_user(username, password):"
        embedding = embedder.encode(text)

        # Verify embedding properties
        assert isinstance(embedding, np.ndarray)
        assert embedding.dtype == np.float32
        assert len(embedding.shape) == 1
        assert len(embedding) > 0

    def test_dimension_detection(self, embedder: OllamaEmbedder) -> None:
        """Waypoint 3: Verify dimension is detected correctly."""
        # Arctic embed should be 1024D
        assert embedder.dimension > 0
        assert embedder.dimension == 1024, (
            f"Expected arctic-embed to be 1024D, got {embedder.dimension}D. "
            f"Verify model is snowflake-arctic-embed:latest"
        )

    def test_determinism(self, embedder: OllamaEmbedder) -> None:
        """Waypoint 3: Verify embeddings are consistent for same input."""
        text = "class DatabaseConnection:"
        emb1 = embedder.encode(text)
        emb2 = embedder.encode(text)

        # Should be identical (Ollama is deterministic by default)
        assert np.allclose(emb1, emb2, atol=1e-6)

    def test_different_texts_different_embeddings(self, embedder: OllamaEmbedder) -> None:
        """Waypoint 3: Verify different texts produce different embeddings."""
        text1 = "authentication code"
        text2 = "database connection"

        emb1 = embedder.encode(text1)
        emb2 = embedder.encode(text2)

        # Embeddings should be different
        assert not np.allclose(emb1, emb2, atol=0.1)

    def test_model_name_property(self, embedder: OllamaEmbedder) -> None:
        """Waypoint 3: Verify model name is tracked correctly."""
        assert embedder.name == "ollama/snowflake-arctic-embed:latest"
