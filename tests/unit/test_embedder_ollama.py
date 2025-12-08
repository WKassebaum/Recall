"""Tests for the Ollama embedder."""

import json

import numpy as np
import pytest
from unittest.mock import MagicMock, patch


class TestOllamaEmbedder:
    """Test OllamaEmbedder class."""

    def test_init_default_values(self):
        """Verify initialization with default values."""
        from recall.embedders.ollama import OllamaEmbedder

        embedder = OllamaEmbedder()

        assert embedder.name == "ollama/snowflake-arctic-embed:latest"
        assert embedder._host == "localhost"
        assert embedder._port == 11434
        assert embedder._base_url == "http://localhost:11434"

    def test_init_custom_values(self):
        """Verify initialization with custom values."""
        from recall.embedders.ollama import OllamaEmbedder

        embedder = OllamaEmbedder(model="nomic-embed", host="192.168.1.100", port=8080)

        assert embedder.name == "ollama/nomic-embed"
        assert embedder._host == "192.168.1.100"
        assert embedder._port == 8080
        assert embedder._base_url == "http://192.168.1.100:8080"

    def test_dimension_detected_on_first_call(self):
        """Verify dimension is detected on first call."""
        with patch("recall.embedders.ollama.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"embedding": [0.1] * 768}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            from recall.embedders.ollama import OllamaEmbedder

            embedder = OllamaEmbedder()
            dim = embedder.dimension

            assert dim == 768
            # Verify encode was called with "test"
            mock_post.assert_called_once()

    def test_dimension_cached(self):
        """Verify dimension is cached after first detection."""
        with patch("recall.embedders.ollama.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"embedding": [0.1] * 768}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            from recall.embedders.ollama import OllamaEmbedder

            embedder = OllamaEmbedder()
            _ = embedder.dimension
            _ = embedder.dimension  # Second call

            # Only one encode call for dimension detection
            assert mock_post.call_count == 1

    def test_health_check_success(self):
        """Verify health check returns True when Ollama is accessible."""
        with patch("recall.embedders.ollama.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            from recall.embedders.ollama import OllamaEmbedder

            embedder = OllamaEmbedder()
            result = embedder.health_check()

            assert result is True
            mock_get.assert_called_once_with("http://localhost:11434/api/tags", timeout=5.0)

    def test_health_check_failure_status_code(self):
        """Verify health check returns False on non-200 status."""
        with patch("recall.embedders.ollama.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            from recall.embedders.ollama import OllamaEmbedder

            embedder = OllamaEmbedder()
            result = embedder.health_check()

            assert result is False

    def test_health_check_failure_exception(self):
        """Verify health check returns False on connection error."""
        with patch("recall.embedders.ollama.httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")

            from recall.embedders.ollama import OllamaEmbedder

            embedder = OllamaEmbedder()
            result = embedder.health_check()

            assert result is False

    def test_encode_success(self):
        """Verify encode returns correct embedding."""
        with patch("recall.embedders.ollama.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"embedding": [0.5] * 384}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            from recall.embedders.ollama import OllamaEmbedder

            embedder = OllamaEmbedder()
            result = embedder.encode("test text")

            assert isinstance(result, np.ndarray)
            assert result.dtype == np.float32
            assert result.shape == (384,)
            np.testing.assert_array_almost_equal(result, [0.5] * 384)

    def test_encode_connection_error(self):
        """Verify encode raises ConnectionError on connect failure."""
        import httpx

        with patch("recall.embedders.ollama.httpx.post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            from recall.embedders.ollama import OllamaEmbedder

            embedder = OllamaEmbedder()

            with pytest.raises(ConnectionError) as exc_info:
                embedder.encode("test text")

            assert "Failed to connect to Ollama" in str(exc_info.value)
            assert "brew services start ollama" in str(exc_info.value)

    def test_encode_http_status_error(self):
        """Verify encode raises RuntimeError on HTTP error."""
        import httpx

        with patch("recall.embedders.ollama.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Error", request=MagicMock(), response=mock_response
            )

            from recall.embedders.ollama import OllamaEmbedder

            embedder = OllamaEmbedder()

            with pytest.raises(RuntimeError) as exc_info:
                embedder.encode("test text")

            assert "Ollama returned error" in str(exc_info.value)

    def test_encode_json_decode_error(self):
        """Verify encode raises RuntimeError on JSON parse failure."""
        with patch("recall.embedders.ollama.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.side_effect = json.JSONDecodeError("Error", "", 0)

            mock_post.return_value = mock_response

            from recall.embedders.ollama import OllamaEmbedder

            embedder = OllamaEmbedder()

            with pytest.raises(RuntimeError) as exc_info:
                embedder.encode("test text")

            assert "Failed to parse Ollama response" in str(exc_info.value)

    def test_encode_missing_embedding_key(self):
        """Verify encode raises RuntimeError when embedding key missing."""
        with patch("recall.embedders.ollama.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {"result": "no embedding"}

            mock_post.return_value = mock_response

            from recall.embedders.ollama import OllamaEmbedder

            embedder = OllamaEmbedder()

            with pytest.raises(RuntimeError) as exc_info:
                embedder.encode("test text")

            assert "Failed to parse Ollama response" in str(exc_info.value)
            assert "ollama pull" in str(exc_info.value)
