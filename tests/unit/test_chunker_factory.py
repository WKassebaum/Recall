"""
Waypoint 9: Chunker factory tests.

Validates auto-detection and routing to appropriate chunkers.
"""

import json

import pytest

from semvecmem.chunking.factory import ChunkerFactory


class TestChunkerFactory:
    """Waypoint 9 tests - Chunker factory validation."""

    @pytest.fixture
    def factory(self) -> ChunkerFactory:
        """Create chunker factory."""
        return ChunkerFactory(max_chunk_size=500)

    def test_detect_json_by_extension(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify .json extension detected."""
        assert factory.detect_type("", "config.json") == "json"

    def test_detect_markdown_by_extension(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify .md extension detected."""
        assert factory.detect_type("", "README.md") == "markdown"
        assert factory.detect_type("", "notes.markdown") == "markdown"

    def test_detect_python_by_extension(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify .py extension detected."""
        assert factory.detect_type("", "script.py") == "python"

    def test_detect_json_by_content(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify JSON detected from content."""
        content = json.dumps({"key": "value", "nested": {"data": 123}})
        assert factory.detect_type(content) == "json"

    def test_detect_markdown_by_content(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify Markdown detected from patterns."""
        content = """# Title

## Section

- List item
- Another item

[Link](https://example.com)
"""
        assert factory.detect_type(content) == "markdown"

    def test_detect_python_by_content(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify Python detected from code patterns."""
        content = """import sys

def main():
    print("Hello")

class MyClass:
    pass
"""
        assert factory.detect_type(content) == "python"

    def test_detect_prose_fallback(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify prose is fallback for plain text."""
        content = "This is just plain text without special patterns."
        assert factory.detect_type(content) == "prose"

    def test_chunk_with_explicit_type(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify explicit content type override works."""
        content = "Some content"
        chunks = factory.chunk(content, content_type="markdown")

        assert len(chunks) >= 1

    def test_chunk_json_content(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify JSON content routed to JSONChunker."""
        data = {"key1": "value1", "key2": "value2"}
        content = json.dumps(data)

        chunks = factory.chunk(content)

        assert len(chunks) == 1
        assert json.loads(chunks[0].content) == data

    def test_chunk_markdown_content(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify Markdown routed to MarkdownChunker."""
        content = """# Title

## Section 1

Content here.

## Section 2

More content.
"""
        chunks = factory.chunk(content)

        assert len(chunks) >= 1
        all_content = "\n".join(c.content for c in chunks)
        assert "# Title" in all_content

    def test_chunk_python_content(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify Python routed to PythonChunker."""
        content = """def example():
    return 42

class Example:
    pass
"""
        chunks = factory.chunk(content)

        assert len(chunks) >= 1
        all_content = "\n".join(c.content for c in chunks)
        assert "def example" in all_content

    def test_chunk_prose_content(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify prose routed to ProseChunker."""
        content = (
            "This is plain text. It has multiple sentences. Each one should be handled correctly."
        )
        chunks = factory.chunk(content)

        assert len(chunks) >= 1
        assert "plain text" in chunks[0].content

    def test_empty_content(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify empty content returns empty list."""
        chunks = factory.chunk("")
        assert len(chunks) == 0

    def test_extension_priority_over_content(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify file extension takes priority."""
        # Content looks like JSON but extension is .md
        content = '{"key": "value"}'
        detected = factory.detect_type(content, "file.md")

        assert detected == "markdown"

    def test_agent_memory_scenario(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify realistic agent memory chunking."""
        # Mix of prose and code
        memory = """We decided to use Redis for session storage.

Implementation:

```python
import redis
client = redis.Redis(host='localhost')
```

This provides fast access with persistence.
"""
        chunks = factory.chunk(memory)

        assert len(chunks) >= 1
        # Should detect as Markdown (has code block)
        all_content = "\n".join(c.content for c in chunks)
        assert "Redis" in all_content

    def test_tool_response_scenario(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify tool response JSON chunking."""
        response = {
            "tool": "search",
            "results": [{"file": "auth.py", "line": 42}],
            "status": "success",
        }
        content = json.dumps(response)

        chunks = factory.chunk(content)

        assert len(chunks) == 1
        parsed = json.loads(chunks[0].content)
        assert parsed["tool"] == "search"

    def test_ambiguous_content(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify ambiguous content handled gracefully."""
        # Content that could be multiple types
        content = "import json\n# Title\nSome text"

        # Should detect as Python (import statement)
        detected = factory.detect_type(content)
        assert detected == "python"

    def test_markdown_requires_multiple_indicators(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify Markdown needs multiple patterns."""
        # Single indicator (just a header-like line) shouldn't trigger
        content = "# This could be a comment"
        detected = factory.detect_type(content)

        # Should be prose (only 1 indicator)
        assert detected == "prose"

        # Multiple indicators should trigger
        content_with_multiple = "# Title\n\n- List item\n- Another"
        detected_multiple = factory.detect_type(content_with_multiple)
        assert detected_multiple == "markdown"

    def test_deterministic_chunking(self, factory: ChunkerFactory) -> None:
        """Waypoint 9: Verify same input produces same chunks."""
        content = "Test content for determinism."

        chunks1 = factory.chunk(content)
        chunks2 = factory.chunk(content)

        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.content == c2.content
            assert c1.id == c2.id
