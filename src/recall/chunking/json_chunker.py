"""JSON/structured data chunking."""

import json
from typing import Any

from recall.core.store import Chunk


class JSONChunker:
    """
    Chunk JSON/structured data intelligently.

    - Small JSON: Keep intact
    - Large JSON: Split by top-level keys
    - Maintains valid JSON structure in each chunk
    """

    def __init__(self, max_chunk_size: int = 2500) -> None:
        """
        Initialize JSON chunker.

        Args:
            max_chunk_size: Maximum characters per chunk
        """
        self.max_chunk_size = max_chunk_size

    def chunk(self, content: str, file_path: str = "") -> list[Chunk]:
        """
        Chunk JSON content intelligently.

        Args:
            content: JSON string to chunk
            file_path: Optional file path for metadata

        Returns:
            List of chunks with valid JSON
        """
        # Try to parse as JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Not valid JSON - treat as text
            return [Chunk(content=content)]

        # If small enough, keep intact
        if len(content) <= self.max_chunk_size:
            return [Chunk(content=content)]

        # Handle different JSON structures
        if isinstance(data, dict):
            return self._chunk_dict(data)
        elif isinstance(data, list):
            return self._chunk_list(data)
        else:
            # Primitive type - keep as is
            return [Chunk(content=content)]

    def _chunk_dict(self, data: dict[str, Any]) -> list[Chunk]:
        """Chunk dictionary by top-level keys."""
        chunks: list[Chunk] = []
        current_dict: dict[str, Any] = {}
        current_size = 2  # Account for {}

        for key, value in data.items():
            # Serialize this key-value pair
            kv_json = json.dumps({key: value}, indent=2)
            kv_size = len(kv_json)

            # Check if adding this would exceed chunk size
            if current_size + kv_size > self.max_chunk_size and current_dict:
                # Save current chunk
                chunk_json = json.dumps(current_dict, indent=2)
                chunks.append(Chunk(content=chunk_json))

                # Start new chunk
                current_dict = {key: value}
                current_size = len(kv_json)
            else:
                current_dict[key] = value
                current_size += kv_size

        # Add final chunk
        if current_dict:
            chunk_json = json.dumps(current_dict, indent=2)
            chunks.append(Chunk(content=chunk_json))

        return chunks

    def _chunk_list(self, data: list[Any]) -> list[Chunk]:
        """Chunk list by grouping items."""
        chunks: list[Chunk] = []
        current_list: list[Any] = []
        current_size = 2  # Account for []

        for item in data:
            # Serialize this item
            item_json = json.dumps(item, indent=2)
            item_size = len(item_json)

            # Check if adding this would exceed chunk size
            if current_size + item_size > self.max_chunk_size and current_list:
                # Save current chunk
                chunk_json = json.dumps(current_list, indent=2)
                chunks.append(Chunk(content=chunk_json))

                # Start new chunk
                current_list = [item]
                current_size = len(item_json)
            else:
                current_list.append(item)
                current_size += item_size + 2  # +2 for comma and space

        # Add final chunk
        if current_list:
            chunk_json = json.dumps(current_list, indent=2)
            chunks.append(Chunk(content=chunk_json))

        return chunks
