"""
Waypoint 5: Python chunking tests.

Validates tree-sitter based Python code chunking.
"""

import pytest

from recall.chunking.python import PythonChunker


class TestPythonChunker:
    """Waypoint 5 tests - Python chunker validation."""

    @pytest.fixture
    def chunker(self) -> PythonChunker:
        """Create Python chunker."""
        return PythonChunker()

    def test_chunk_single_function(self, chunker: PythonChunker) -> None:
        """Waypoint 5: Verify single function is chunked correctly."""
        code = """
def authenticate_user(username, password):
    \"\"\"Authenticate a user.\"\"\"
    return username == "admin" and password == "secret"
"""
        chunks = chunker.chunk_code(code)

        assert len(chunks) == 1
        assert "authenticate_user" in chunks[0].content
        assert "username" in chunks[0].content

    def test_chunk_multiple_functions(self, chunker: PythonChunker) -> None:
        """Waypoint 5: Verify multiple functions are chunked separately."""
        code = """
def login(user):
    \"\"\"Login user.\"\"\"
    return True

def logout(user):
    \"\"\"Logout user.\"\"\"
    return True
"""
        chunks = chunker.chunk_code(code)

        assert len(chunks) == 2
        assert "login" in chunks[0].content
        assert "logout" in chunks[1].content

    def test_chunk_class(self, chunker: PythonChunker) -> None:
        """Waypoint 5: Verify classes are chunked as complete units."""
        code = """
class UserManager:
    \"\"\"Manage users.\"\"\"

    def __init__(self):
        self.users = []

    def add_user(self, user):
        self.users.append(user)
"""
        chunks = chunker.chunk_code(code)

        assert len(chunks) == 1
        assert "UserManager" in chunks[0].content
        assert "__init__" in chunks[0].content
        assert "add_user" in chunks[0].content

    def test_chunk_mixed_content(self, chunker: PythonChunker) -> None:
        """Waypoint 5: Verify functions and classes are both chunked."""
        code = """
def standalone_function():
    pass

class MyClass:
    def method(self):
        pass

def another_function():
    pass
"""
        chunks = chunker.chunk_code(code)

        assert len(chunks) == 3
        contents = "".join(c.content for c in chunks)
        assert "standalone_function" in contents
        assert "MyClass" in contents
        assert "another_function" in contents

    def test_chunk_ids_deterministic(self, chunker: PythonChunker) -> None:
        """Waypoint 5: Verify chunk IDs are deterministic."""
        code = """
def test_function():
    return 42
"""
        chunks1 = chunker.chunk_code(code)
        chunks2 = chunker.chunk_code(code)

        assert chunks1[0].id == chunks2[0].id

    def test_empty_code(self, chunker: PythonChunker) -> None:
        """Waypoint 5: Verify empty code returns empty list."""
        chunks = chunker.chunk_code("")
        assert len(chunks) == 0

    def test_no_functions_or_classes(self, chunker: PythonChunker) -> None:
        """Waypoint 5: Verify code with only imports/variables returns empty."""
        code = """
import os
import sys

CONSTANT = 42
variable = "value"
"""
        chunks = chunker.chunk_code(code)
        # Only top-level functions and classes, no imports/variables
        assert len(chunks) == 0
