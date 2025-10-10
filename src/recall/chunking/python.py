"""Python code chunking using tree-sitter."""

from tree_sitter import Language, Parser
from tree_sitter_python import language as python_language

from recall.core.store import Chunk


class PythonChunker:
    """
    Chunk Python code into semantic units.

    Uses tree-sitter to extract functions, classes, and methods.
    """

    def __init__(self) -> None:
        """Initialize Python chunker."""
        self.language = Language(python_language())
        self.parser = Parser(self.language)

    def chunk(self, content: str, file_path: str = "") -> list[Chunk]:
        """
        Chunk Python code into semantic units.

        Args:
            content: Python source code
            file_path: Optional file path for metadata

        Returns:
            List of code chunks (functions, classes, methods)
        """
        tree = self.parser.parse(content.encode("utf-8"))
        chunks: list[Chunk] = []

        # Extract top-level functions and classes
        root_node = tree.root_node
        for node in root_node.children:
            if node.type in ("function_definition", "class_definition"):
                chunk_content = content[node.start_byte : node.end_byte]
                chunk = Chunk(content=chunk_content)
                chunks.append(chunk)

        return chunks

    def chunk_code(self, code: str, file_path: str = "") -> list[Chunk]:
        """
        Chunk Python code into semantic units (deprecated alias).

        Args:
            code: Python source code
            file_path: Optional file path for metadata

        Returns:
            List of code chunks (functions, classes, methods)
        """
        return self.chunk(code, file_path)

    def chunk_file(self, file_path: str) -> list[Chunk]:
        """
        Chunk a Python file.

        Args:
            file_path: Path to Python file

        Returns:
            List of code chunks

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        with open(file_path, encoding="utf-8") as f:
            code = f.read()

        return self.chunk_code(code, file_path)
