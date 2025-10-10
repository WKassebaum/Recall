"""Base chunker protocol."""

from typing import Protocol

from recall.core.store import Chunk


class Chunker(Protocol):
    """Protocol for content chunkers."""

    def chunk(self, content: str, file_path: str = "") -> list[Chunk]:
        """
        Chunk content into semantic units.

        Args:
            content: Content to chunk
            file_path: Optional file path for metadata

        Returns:
            List of chunks
        """
        ...
