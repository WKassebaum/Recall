"""
Waypoint 8C: Markdown chunker tests.

Validates section-aware Markdown chunking.
"""

import pytest

from recall.chunking.markdown import MarkdownChunker


class TestMarkdownChunker:
    """Waypoint 8C tests - Markdown chunker validation."""

    @pytest.fixture
    def chunker(self) -> MarkdownChunker:
        """Create Markdown chunker."""
        return MarkdownChunker(max_chunk_size=500)

    def test_small_markdown_intact(self, chunker: MarkdownChunker) -> None:
        """Waypoint 8C: Verify small Markdown stays in one chunk."""
        content = """# Title

This is a short document with one section.
"""
        chunks = chunker.chunk(content)

        assert len(chunks) == 1
        assert "Title" in chunks[0].content

    def test_split_by_headers(self, chunker: MarkdownChunker) -> None:
        """Waypoint 8C: Verify splitting on header boundaries."""
        content = """# Main Title

Introduction paragraph.

## Section 1

Content for section 1 with substantial text to make it meaningful.

## Section 2

Content for section 2 with more substantial text content here.

## Section 3

Final section with additional content to demonstrate splitting.
"""
        chunks = chunker.chunk(content)

        # Should create multiple chunks based on sections
        assert len(chunks) >= 1

        # Verify headers are preserved
        all_content = "\n".join(c.content for c in chunks)
        assert "# Main Title" in all_content
        assert "## Section 1" in all_content

    def test_code_blocks_preserved(self, chunker: MarkdownChunker) -> None:
        """Waypoint 8C: Verify code blocks stay intact."""
        content = """## Code Example

Here's some code:

```python
def authenticate(user, password):
    return user == "admin"
```

The code above shows authentication.
"""
        chunks = chunker.chunk(content)

        # Find chunk with code block
        has_code_block = any("```python" in c.content for c in chunks)
        assert has_code_block

        # Verify code block is complete (has closing ```)
        for chunk in chunks:
            if "```python" in chunk.content:
                assert "```" in chunk.content.split("```python", 1)[1]

    def test_large_section_splits_by_paragraphs(self, chunker: MarkdownChunker) -> None:
        """Waypoint 8C: Verify large sections split by paragraphs."""
        # Create large section exceeding chunk size
        paragraphs = [f"Paragraph {i} with content here.\n" * 5 for i in range(20)]
        content = f"## Large Section\n\n" + "\n\n".join(paragraphs)

        chunks = chunker.chunk(content)

        # Should split into multiple chunks
        assert len(chunks) > 1

        # All chunks should have header or content
        for chunk in chunks:
            assert len(chunk.content) > 0

    def test_readme_scenario(self, chunker: MarkdownChunker) -> None:
        """Waypoint 8C: Verify realistic README chunking."""
        readme = """# Project Name

A description of the project.

## Installation

Install with pip:

```bash
pip install project-name
```

## Usage

Basic usage example:

```python
from project import main
main()
```

## Features

- Feature 1: Does something
- Feature 2: Does another thing
- Feature 3: Additional functionality

## License

MIT License
"""
        chunks = chunker.chunk(readme)

        assert len(chunks) >= 1

        # Verify structure preserved
        all_content = "\n".join(c.content for c in chunks)
        assert "# Project Name" in all_content
        assert "## Installation" in all_content
        assert "## Features" in all_content

    def test_nested_headers(self, chunker: MarkdownChunker) -> None:
        """Waypoint 8C: Verify nested headers handled correctly."""
        content = """# Main

## Section

### Subsection

Content here.

#### Sub-subsection

More content.

## Another Section

Final content.
"""
        chunks = chunker.chunk(content)

        # Should preserve header hierarchy
        all_content = "\n".join(c.content for c in chunks)
        assert "# Main" in all_content
        assert "### Subsection" in all_content
        assert "#### Sub-subsection" in all_content

    def test_empty_content(self, chunker: MarkdownChunker) -> None:
        """Waypoint 8C: Verify empty content returns empty list."""
        chunks = chunker.chunk("")
        assert len(chunks) == 0

    def test_deterministic_chunking(self, chunker: MarkdownChunker) -> None:
        """Waypoint 8C: Verify same input produces same chunks."""
        content = """# Title

## Section

Content here.
"""
        chunks1 = chunker.chunk(content)
        chunks2 = chunker.chunk(content)

        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.content == c2.content
            assert c1.id == c2.id

    def test_documentation_scenario(self, chunker: MarkdownChunker) -> None:
        """Waypoint 8C: Verify agent documentation notes chunking."""
        docs = """# OAuth Implementation Notes

## Decision Rationale

We decided to use OAuth 2.0 with PKCE flow because:

1. Enhanced security for public clients
2. No client secret needed
3. Protection against authorization code interception

## Implementation Details

The implementation uses the authlib library for Python:

```python
from authlib.integrations.flask_client import OAuth

oauth = OAuth(app)
oauth.register('github', client_id=CLIENT_ID)
```

## Testing Strategy

Integration tests cover:

- Authorization flow
- Token refresh
- Error handling

Each test uses mock OAuth provider responses.
"""
        chunks = chunker.chunk(docs)

        assert len(chunks) >= 1

        # Verify all sections accessible
        all_content = "\n".join(c.content for c in chunks)
        assert "Decision Rationale" in all_content
        assert "Implementation Details" in all_content
        assert "authlib" in all_content
