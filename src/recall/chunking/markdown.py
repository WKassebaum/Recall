"""Markdown chunking with section awareness."""

import re

from recall.core.store import Chunk


class MarkdownChunker:
    """
    Chunk Markdown content by sections and headers.

    Preserves document structure by splitting on header boundaries
    while keeping code blocks intact.
    """

    def __init__(self, max_chunk_size: int = 2500) -> None:
        """
        Initialize Markdown chunker.

        Args:
            max_chunk_size: Maximum characters per chunk
        """
        self.max_chunk_size = max_chunk_size

    def chunk(self, content: str, file_path: str = "") -> list[Chunk]:
        """
        Chunk Markdown by sections.

        Args:
            content: Markdown content to chunk
            file_path: Optional file path for metadata

        Returns:
            List of chunks split by section boundaries
        """
        if not content.strip():
            return []

        # Split by headers while preserving them
        sections = self._split_by_headers(content)

        if not sections:
            # No headers found - treat as single section
            return self._chunk_large_section(content)

        chunks: list[Chunk] = []
        current_section = ""

        for section in sections:
            # Try combining with current section
            combined = f"{current_section}\n\n{section}".strip() if current_section else section

            # Check if combined section exceeds max size
            if len(combined) > self.max_chunk_size and current_section:
                # Save current section
                chunks.extend(self._chunk_large_section(current_section))

                # Start new section
                current_section = section
            else:
                current_section = combined

        # Add final section
        if current_section.strip():
            chunks.extend(self._chunk_large_section(current_section))

        return chunks

    def _split_by_headers(self, content: str) -> list[str]:
        """
        Split content by Markdown headers.

        Args:
            content: Markdown content

        Returns:
            List of sections (each starts with a header or is before first header)
        """
        # Match headers: # Title, ## Section, ### Subsection, etc.
        header_pattern = re.compile(r"^#{1,6}\s+.+$", re.MULTILINE)

        sections: list[str] = []
        last_end = 0

        for match in header_pattern.finditer(content):
            # Add content before this header (if any)
            if match.start() > last_end:
                before = content[last_end : match.start()].strip()
                if before:
                    sections.append(before)

            # Find end of this section (next header or end of content)
            next_match = header_pattern.search(content, match.end())
            section_end = next_match.start() if next_match else len(content)

            # Add section (including header)
            section = content[match.start() : section_end].strip()
            if section:
                sections.append(section)

            last_end = section_end

        return sections

    def _chunk_large_section(self, section: str) -> list[Chunk]:
        """
        Chunk a large section that exceeds max size.

        Args:
            section: Section content

        Returns:
            List of chunks
        """
        if len(section) <= self.max_chunk_size:
            return [Chunk(content=section)]

        # Split by paragraphs (double newline)
        paragraphs = section.split("\n\n")

        chunks: list[Chunk] = []
        current_chunk = ""

        for para in paragraphs:
            # Try adding paragraph to current chunk
            potential = f"{current_chunk}\n\n{para}".strip() if current_chunk else para

            if len(potential) > self.max_chunk_size and current_chunk:
                # Save current chunk
                chunks.append(Chunk(content=current_chunk))

                # Start new chunk
                current_chunk = para
            else:
                current_chunk = potential

        # Add final chunk
        if current_chunk.strip():
            chunks.append(Chunk(content=current_chunk))

        return chunks
