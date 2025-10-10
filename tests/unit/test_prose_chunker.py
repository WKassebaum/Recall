"""
Waypoint 8A: Prose chunker tests.

Validates NLTK-based sentence splitting with overlap.
"""

import pytest

from recall.chunking.prose import ProseChunker


class TestProseChunker:
    """Waypoint 8A tests - Prose chunker validation."""

    @pytest.fixture
    def chunker(self) -> ProseChunker:
        """Create prose chunker with default settings."""
        return ProseChunker(max_chunk_size=500, chunk_overlap=100)

    def test_single_sentence(self, chunker: ProseChunker) -> None:
        """Waypoint 8A: Verify single sentence creates one chunk."""
        text = "This is a single sentence."
        chunks = chunker.chunk(text)

        assert len(chunks) == 1
        assert chunks[0].content == text

    def test_multiple_sentences_small(self, chunker: ProseChunker) -> None:
        """Waypoint 8A: Verify multiple short sentences stay in one chunk."""
        text = "First sentence. Second sentence. Third sentence."
        chunks = chunker.chunk(text)

        assert len(chunks) == 1
        assert "First sentence" in chunks[0].content
        assert "Third sentence" in chunks[0].content

    def test_chunk_splitting_by_size(self, chunker: ProseChunker) -> None:
        """Waypoint 8A: Verify long content splits into multiple chunks."""
        # Create text that exceeds chunk size (500 chars)
        sentences = [
            "This is sentence number one with some content to make it longer.",
            "This is sentence number two with additional content.",
            "This is sentence number three with even more content.",
            "This is sentence number four continuing the pattern.",
            "This is sentence number five adding more text.",
            "This is sentence number six with substantial content.",
            "This is sentence number seven maintaining the length.",
            "This is sentence number eight with consistent sizing.",
            "This is sentence number nine continuing forward.",
            "This is sentence number ten completing the sequence.",
        ]
        text = " ".join(sentences)

        chunks = chunker.chunk(text)

        # Should split into multiple chunks
        assert len(chunks) > 1

        # Verify all content is preserved
        all_content = " ".join(c.content for c in chunks)
        for sentence in sentences:
            assert sentence in all_content

    def test_overlap_between_chunks(self, chunker: ProseChunker) -> None:
        """Waypoint 8A: Verify chunks have overlap for context."""
        # Create specific sentences to track overlap
        text = (
            "Sentence A is the first one. "
            "Sentence B comes second. "
            "Sentence C is third. "
            "Sentence D appears fourth. "
            "Sentence E is fifth. "
            "Sentence F comes sixth. " * 10  # Repeat to force splitting
        )

        chunks = chunker.chunk(text)

        if len(chunks) > 1:
            # Check that consecutive chunks share some content
            for i in range(len(chunks) - 1):
                # Overlap should mean some sentences appear in both chunks
                chunk1_sentences = set(chunks[i].content.split(". "))
                chunk2_sentences = set(chunks[i + 1].content.split(". "))
                overlap = chunk1_sentences & chunk2_sentences
                assert len(overlap) > 0, "Chunks should have sentence overlap"

    def test_empty_content(self, chunker: ProseChunker) -> None:
        """Waypoint 8A: Verify empty content returns empty list."""
        chunks = chunker.chunk("")
        assert len(chunks) == 0

    def test_whitespace_only(self, chunker: ProseChunker) -> None:
        """Waypoint 8A: Verify whitespace-only content returns empty list."""
        chunks = chunker.chunk("   \n\n   ")
        assert len(chunks) == 0

    def test_agent_memory_scenario(self, chunker: ProseChunker) -> None:
        """Waypoint 8A: Verify realistic agent memory chunking."""
        memory = """
        We decided to use Redis for session storage because it provides fast
        in-memory access with persistence. The key considerations were:

        First, we needed sub-millisecond read/write latency for user sessions.
        MySQL and PostgreSQL couldn't meet this requirement under high load.

        Second, Redis supports automatic expiration of session keys, which
        simplifies our session management logic significantly.

        Third, Redis Cluster provides horizontal scalability if we need to
        scale beyond a single instance in the future.

        The implementation uses redis-py with connection pooling. Session data
        is serialized as JSON and stored with a 30-minute TTL.
        """

        chunks = chunker.chunk(memory)

        assert len(chunks) >= 1

        # Verify content is preserved
        all_content = " ".join(c.content for c in chunks)
        assert "Redis" in all_content
        assert "session storage" in all_content
        assert "redis-py" in all_content

    def test_deterministic_chunking(self, chunker: ProseChunker) -> None:
        """Waypoint 8A: Verify same input produces same chunks."""
        text = "First sentence here. Second sentence follows. Third completes it."

        chunks1 = chunker.chunk(text)
        chunks2 = chunker.chunk(text)

        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.content == c2.content
            assert c1.id == c2.id  # Same content = same ID

    def test_configurable_chunk_size(self) -> None:
        """Waypoint 8A: Verify chunk size is configurable."""
        small_chunker = ProseChunker(max_chunk_size=100, chunk_overlap=20)
        large_chunker = ProseChunker(max_chunk_size=1000, chunk_overlap=200)

        text = " ".join([f"Sentence number {i}." for i in range(50)])

        small_chunks = small_chunker.chunk(text)
        large_chunks = large_chunker.chunk(text)

        # Smaller chunk size should produce more chunks
        assert len(small_chunks) > len(large_chunks)
