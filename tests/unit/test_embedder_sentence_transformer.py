"""Tests for the SentenceTransformer embedder."""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch


class TestSentenceTransformerEmbedder:
    """Test SentenceTransformerEmbedder class."""

    def test_init_with_default_model(self):
        """Verify initialization with default model."""
        with patch("recall.embedders.sentence_transformer.SentenceTransformer") as mock_st:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 1024
            mock_st.return_value = mock_model

            from recall.embedders.sentence_transformer import SentenceTransformerEmbedder

            embedder = SentenceTransformerEmbedder()

            assert embedder.name == "Snowflake/snowflake-arctic-embed-m"
            assert embedder.dimension == 1024
            mock_st.assert_called_once_with(
                "Snowflake/snowflake-arctic-embed-m", trust_remote_code=True
            )

    def test_init_with_custom_model(self):
        """Verify initialization with custom model."""
        with patch("recall.embedders.sentence_transformer.SentenceTransformer") as mock_st:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_st.return_value = mock_model

            from recall.embedders.sentence_transformer import SentenceTransformerEmbedder

            embedder = SentenceTransformerEmbedder("all-MiniLM-L6-v2")

            assert embedder.name == "all-MiniLM-L6-v2"
            assert embedder.dimension == 384

    def test_init_dimension_none_raises_error(self):
        """Verify error when model returns None dimension."""
        with patch("recall.embedders.sentence_transformer.SentenceTransformer") as mock_st:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = None
            mock_st.return_value = mock_model

            from recall.embedders.sentence_transformer import SentenceTransformerEmbedder

            with pytest.raises(ValueError, match="Could not determine dimension"):
                SentenceTransformerEmbedder("bad-model")

    def test_encode_returns_float32(self):
        """Verify encode returns float32 array."""
        with patch("recall.embedders.sentence_transformer.SentenceTransformer") as mock_st:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            # Return float64 array to test conversion
            mock_model.encode.return_value = np.array([0.1] * 384, dtype=np.float64)
            mock_st.return_value = mock_model

            from recall.embedders.sentence_transformer import SentenceTransformerEmbedder

            embedder = SentenceTransformerEmbedder()
            result = embedder.encode("test text")

            assert result.dtype == np.float32
            assert result.shape == (384,)

    def test_encode_flattens_2d_array(self):
        """Verify encode flattens 2D array output."""
        with patch("recall.embedders.sentence_transformer.SentenceTransformer") as mock_st:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            # Return 2D array
            mock_model.encode.return_value = np.array([[0.1] * 384], dtype=np.float32)
            mock_st.return_value = mock_model

            from recall.embedders.sentence_transformer import SentenceTransformerEmbedder

            embedder = SentenceTransformerEmbedder()
            result = embedder.encode("test text")

            assert len(result.shape) == 1
            assert result.shape == (384,)

    def test_encode_converts_list_to_array(self):
        """Verify encode converts list to numpy array."""
        with patch("recall.embedders.sentence_transformer.SentenceTransformer") as mock_st:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            # Return list instead of ndarray
            mock_model.encode.return_value = [0.1] * 384
            mock_st.return_value = mock_model

            from recall.embedders.sentence_transformer import SentenceTransformerEmbedder

            embedder = SentenceTransformerEmbedder()
            result = embedder.encode("test text")

            assert isinstance(result, np.ndarray)
            assert result.dtype == np.float32

    def test_name_property(self):
        """Verify name property returns model name."""
        with patch("recall.embedders.sentence_transformer.SentenceTransformer") as mock_st:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 768
            mock_st.return_value = mock_model

            from recall.embedders.sentence_transformer import SentenceTransformerEmbedder

            embedder = SentenceTransformerEmbedder("nomic-ai/nomic-embed-text-v1.5")

            assert embedder.name == "nomic-ai/nomic-embed-text-v1.5"

    def test_dimension_property(self):
        """Verify dimension property returns correct dimension."""
        with patch("recall.embedders.sentence_transformer.SentenceTransformer") as mock_st:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 768
            mock_st.return_value = mock_model

            from recall.embedders.sentence_transformer import SentenceTransformerEmbedder

            embedder = SentenceTransformerEmbedder("bge-small-en-v1.5")

            assert embedder.dimension == 768
