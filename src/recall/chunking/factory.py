# Copyright 2025 William Kassebaum
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Chunker factory with automatic content-type detection."""

import json
import re

from recall.chunking.base import Chunker
from recall.chunking.json_chunker import JSONChunker
from recall.chunking.markdown import MarkdownChunker
from recall.chunking.prose import ProseChunker
from recall.chunking.python import PythonChunker
from recall.core.store import Chunk


class ChunkerFactory:
    """
    Factory for selecting appropriate chunker based on content type.

    Auto-detects content type and routes to specialized chunkers.
    """

    def __init__(
        self,
        max_chunk_size: int = 2500,
        chunk_overlap: int = 300,
    ) -> None:
        """
        Initialize chunker factory.

        Args:
            max_chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap characters for prose chunking
        """
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

        # Initialize chunkers
        self._prose_chunker = ProseChunker(max_chunk_size, chunk_overlap)
        self._json_chunker = JSONChunker(max_chunk_size)
        self._markdown_chunker = MarkdownChunker(max_chunk_size)
        self._python_chunker = PythonChunker()

    def chunk(
        self, content: str, file_path: str = "", content_type: str | None = None
    ) -> list[Chunk]:
        """
        Chunk content using appropriate strategy.

        Args:
            content: Content to chunk
            file_path: Optional file path for metadata and type detection
            content_type: Optional explicit content type override

        Returns:
            List of chunks
        """
        if not content.strip():
            return []

        # Determine content type
        detected_type = content_type if content_type else self.detect_type(content, file_path)

        # Route to appropriate chunker
        chunker = self._get_chunker(detected_type)
        return chunker.chunk(content, file_path)

    def detect_type(self, content: str, file_path: str = "") -> str:
        """
        Auto-detect content type.

        Args:
            content: Content to analyze
            file_path: Optional file path for extension-based detection

        Returns:
            Content type string: 'json', 'markdown', 'python', or 'prose'
        """
        # Extension-based detection (highest priority)
        if file_path:
            ext = file_path.lower().split(".")[-1]
            if ext == "py":
                return "python"
            if ext in {"md", "markdown"}:
                return "markdown"
            if ext == "json":
                return "json"

        # JSON detection
        if self._is_json(content):
            return "json"

        # Markdown detection (headers, lists, code blocks)
        if self._is_markdown(content):
            return "markdown"

        # Python code detection
        if self._is_python(content):
            return "python"

        # Default to prose for text
        return "prose"

    def _get_chunker(self, content_type: str) -> Chunker:
        """Get chunker for content type."""
        if content_type == "json":
            return self._json_chunker
        elif content_type == "markdown":
            return self._markdown_chunker
        elif content_type == "python":
            return self._python_chunker
        else:
            return self._prose_chunker

    def _is_json(self, content: str) -> bool:
        """Check if content is valid JSON."""
        try:
            json.loads(content)
            return True
        except (json.JSONDecodeError, ValueError):
            return False

    def _is_markdown(self, content: str) -> bool:
        """Check if content appears to be Markdown."""
        # Check for Markdown patterns
        has_headers = bool(re.search(r"^#{1,6}\s+.+$", content, re.MULTILINE))
        has_code_blocks = "```" in content
        has_lists = bool(re.search(r"^[-*+]\s+", content, re.MULTILINE))
        has_links = bool(re.search(r"\[.+\]\(.+\)", content))

        # Code blocks are a strong indicator - accept with just 1 more indicator
        # or if it's the only indicator but has both opening and closing blocks
        if has_code_blocks:
            # Check if there are complete code blocks (both ``` and ```)
            complete_blocks = content.count("```") >= 2
            if complete_blocks:
                return True

        # Consider it Markdown if it has multiple indicators
        indicators = sum([has_headers, has_code_blocks, has_lists, has_links])
        return indicators >= 2

    def _is_python(self, content: str) -> bool:
        """Check if content appears to be Python code."""
        # Check for Python-specific patterns
        has_def = bool(re.search(r"^\s*def\s+\w+\s*\(", content, re.MULTILINE))
        has_class = bool(re.search(r"^\s*class\s+\w+", content, re.MULTILINE))
        has_import = bool(re.search(r"^\s*(?:from|import)\s+", content, re.MULTILINE))
        has_decorators = bool(re.search(r"^\s*@\w+", content, re.MULTILINE))

        # Consider it Python if it has code-like patterns
        indicators = sum([has_def, has_class, has_import, has_decorators])
        return indicators >= 1
