"""Sparse vector encoding for hybrid search."""

from typing import Protocol

from qdrant_client.models import SparseVector


class SparseEncoderProtocol(Protocol):
    """Protocol for sparse encoder interface used by store and MCP server."""

    def encode(self, text: str) -> SparseVector:
        ...

    def encode_query(self, keywords: str) -> SparseVector:
        ...
