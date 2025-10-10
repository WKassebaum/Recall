"""Prose/text chunking using NLTK sentence tokenization."""

import nltk

from recall.core.store import Chunk


class ProseChunker:
    """
    Chunk prose/text using sentence boundaries.

    Uses NLTK's punkt tokenizer for sentence splitting with overlap
    for context preservation.
    """

    def __init__(self, max_chunk_size: int = 2500, chunk_overlap: int = 300) -> None:
        """
        Initialize prose chunker.

        Args:
            max_chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap characters for context
        """
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

        # Download NLTK data if not present
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt", quiet=True)
        try:
            nltk.data.find("tokenizers/punkt_tab")
        except LookupError:
            nltk.download("punkt_tab", quiet=True)

    def chunk(self, content: str, file_path: str = "") -> list[Chunk]:
        """
        Chunk prose into semantic units based on sentences.

        Args:
            content: Text content to chunk
            file_path: Optional file path for metadata

        Returns:
            List of chunks split by sentence boundaries with overlap
        """
        # Split into sentences
        sentences = nltk.sent_tokenize(content)

        if not sentences:
            return []

        chunks: list[Chunk] = []
        current_chunk = ""
        overlap_sentences: list[str] = []

        for sentence in sentences:
            # Try adding sentence to current chunk
            potential_chunk = f"{current_chunk} {sentence}".strip() if current_chunk else sentence

            # Check if adding this sentence would exceed max size
            if len(potential_chunk) > self.max_chunk_size and current_chunk:
                # Save current chunk
                chunk = Chunk(content=current_chunk)
                chunks.append(chunk)

                # Start new chunk with overlap
                overlap_text = " ".join(overlap_sentences)
                current_chunk = f"{overlap_text} {sentence}".strip() if overlap_text else sentence

                # Update overlap buffer (keep last N sentences for context)
                overlap_sentences = [sentence]
            else:
                current_chunk = potential_chunk
                overlap_sentences.append(sentence)

                # Maintain overlap buffer size
                while len(" ".join(overlap_sentences)) > self.chunk_overlap:
                    overlap_sentences.pop(0)

        # Add final chunk
        if current_chunk.strip():
            chunk = Chunk(content=current_chunk)
            chunks.append(chunk)

        return chunks
