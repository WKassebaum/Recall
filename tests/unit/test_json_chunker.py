"""
Waypoint 8B: JSON chunker tests.

Validates intelligent JSON chunking with structure preservation.
"""

import json

import pytest

from recall.chunking.json_chunker import JSONChunker


class TestJSONChunker:
    """Waypoint 8B tests - JSON chunker validation."""

    @pytest.fixture
    def chunker(self) -> JSONChunker:
        """Create JSON chunker."""
        return JSONChunker(max_chunk_size=500)

    def test_small_json_kept_intact(self, chunker: JSONChunker) -> None:
        """Waypoint 8B: Verify small JSON stays in one chunk."""
        data = {"name": "test", "value": 42}
        content = json.dumps(data)

        chunks = chunker.chunk(content)

        assert len(chunks) == 1
        assert json.loads(chunks[0].content) == data

    def test_large_json_dict_splits(self, chunker: JSONChunker) -> None:
        """Waypoint 8B: Verify large JSON dict splits by keys."""
        # Create JSON larger than chunk size (500 chars)
        data = {f"key_{i}": f"value_with_substantial_content_{i}" * 10 for i in range(20)}
        content = json.dumps(data)

        chunks = chunker.chunk(content)

        # Should split into multiple chunks
        assert len(chunks) > 1

        # Verify all chunks are valid JSON
        for chunk in chunks:
            parsed = json.loads(chunk.content)
            assert isinstance(parsed, dict)

        # Verify all keys are preserved
        all_keys = set()
        for chunk in chunks:
            parsed = json.loads(chunk.content)
            all_keys.update(parsed.keys())

        assert all_keys == set(data.keys())

    def test_json_list_chunking(self, chunker: JSONChunker) -> None:
        """Waypoint 8B: Verify JSON lists split by items."""
        # Create large list
        data = [{"id": i, "data": "x" * 50} for i in range(30)]
        content = json.dumps(data)

        chunks = chunker.chunk(content)

        # Should split into multiple chunks
        assert len(chunks) > 1

        # Verify all chunks are valid JSON lists
        for chunk in chunks:
            parsed = json.loads(chunk.content)
            assert isinstance(parsed, list)

        # Verify all items preserved
        all_items = []
        for chunk in chunks:
            parsed = json.loads(chunk.content)
            all_items.extend(parsed)

        assert len(all_items) == len(data)

    def test_invalid_json_treated_as_text(self, chunker: JSONChunker) -> None:
        """Waypoint 8B: Verify invalid JSON is treated as plain text."""
        content = "not valid json {broken"

        chunks = chunker.chunk(content)

        assert len(chunks) == 1
        assert chunks[0].content == content

    def test_tool_call_response_scenario(self, chunker: JSONChunker) -> None:
        """Waypoint 8B: Verify realistic tool call response chunking."""
        tool_response = {
            "tool": "search_codebase",
            "query": "authentication",
            "results": [
                {
                    "file": "auth.py",
                    "line": 42,
                    "snippet": "def authenticate(user, password):",
                },
                {
                    "file": "login.py",
                    "line": 15,
                    "snippet": "if authenticate(username, pwd):",
                },
            ],
            "metadata": {"took_ms": 150, "total_results": 2},
        }

        content = json.dumps(tool_response, indent=2)
        chunks = chunker.chunk(content)

        # Small enough to stay in one chunk
        assert len(chunks) == 1

        # Verify structure preserved
        parsed = json.loads(chunks[0].content)
        assert parsed["tool"] == "search_codebase"
        assert len(parsed["results"]) == 2

    def test_config_snippet_scenario(self, chunker: JSONChunker) -> None:
        """Waypoint 8B: Verify configuration JSON chunking."""
        config = {
            "embedder": {"model": "arctic", "dimension": 768},
            "qdrant": {"host": "localhost", "port": 6333},
            "chunking": {"max_size": 512, "overlap": 50},
        }

        content = json.dumps(config, indent=2)
        chunks = chunker.chunk(content)

        # Small config stays intact
        assert len(chunks) == 1

        # Verify valid JSON
        parsed = json.loads(chunks[0].content)
        assert parsed["embedder"]["model"] == "arctic"

    def test_deterministic_chunking(self, chunker: JSONChunker) -> None:
        """Waypoint 8B: Verify same JSON produces same chunks."""
        data = {"key1": "value1", "key2": "value2"}
        content = json.dumps(data)

        chunks1 = chunker.chunk(content)
        chunks2 = chunker.chunk(content)

        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.content == c2.content
            assert c1.id == c2.id

    def test_nested_json_structure(self, chunker: JSONChunker) -> None:
        """Waypoint 8B: Verify nested JSON is preserved."""
        data = {
            "user": {
                "name": "test",
                "roles": ["admin", "developer"],
                "settings": {"theme": "dark", "notifications": True},
            }
        }

        content = json.dumps(data)
        chunks = chunker.chunk(content)

        assert len(chunks) == 1

        # Verify nesting preserved
        parsed = json.loads(chunks[0].content)
        assert parsed["user"]["settings"]["theme"] == "dark"
        assert "admin" in parsed["user"]["roles"]
