"""Unified Vector Store with dimension verification."""

import hashlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

from semvecmem.embedders.base import EmbedderModel

if TYPE_CHECKING:
    from semvecmem.backends.qdrant import QdrantBackend


class DimensionMismatchError(Exception):
    """Raised when embedding dimension doesn't match expected dimension."""

    pass


class Chunk:
    """Code chunk with embedding and metadata."""

    def __init__(
        self,
        content: str,
        embedding: npt.NDArray[np.float32] | None = None,
        chunk_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ):
        """
        Initialize chunk.

        Args:
            content: Chunk content
            embedding: Optional embedding vector
            chunk_id: Optional chunk ID (auto-generated if not provided)
            metadata: Optional metadata (session_id, timestamps, tags, etc.)
        """
        self.content = content
        self.embedding = embedding
        self.id = chunk_id or self._generate_id(content)
        self.metadata = metadata or {}

    @staticmethod
    def _generate_id(content: str) -> str:
        """Generate deterministic chunk ID from content."""
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class SearchResult:
    """Search result with score and metadata."""

    content: str
    score: float
    chunk_id: str
    metadata: dict[str, str] = field(default_factory=dict)


class UnifiedVectorStore:
    """
    Unified vector store with automatic dimension routing.

    Abstracts multi-collection complexity from users by automatically
    routing to the correct collection based on embedder dimension.
    """

    def __init__(self, backend: "QdrantBackend | None" = None) -> None:
        """
        Initialize unified vector store.

        Args:
            backend: Optional Qdrant backend (uses in-memory if None)
        """
        self.active_embedder: EmbedderModel | None = None
        self.active_dimension: int | None = None
        self.active_collection: str | None = None
        self.backend = backend

        # In-memory storage (used if no backend provided)
        self._storage: dict[str, list[Chunk]] = {}

    def set_embedder(self, embedder: EmbedderModel) -> None:
        """
        Set active embedder and route to appropriate collection.

        Args:
            embedder: Embedder model to use
        """
        self.active_embedder = embedder
        self.active_dimension = embedder.dimension
        self.active_collection = f"semvecmem_{self.active_dimension}d"

        # Ensure collection exists
        if self.backend:
            self.backend.ensure_collection(self.active_collection, self.active_dimension)
        elif self.active_collection not in self._storage:
            self._storage[self.active_collection] = []

    def add(self, content: str, metadata: dict[str, str] | None = None) -> str:
        """
        Add single chunk with metadata (convenience method).

        Args:
            content: Content to store
            metadata: Optional metadata (session_id, tags, timestamps, etc.)

        Returns:
            Chunk ID of stored chunk

        Raises:
            ValueError: If no active embedder set
            DimensionMismatchError: If chunk dimension doesn't match active dimension
        """
        chunk = Chunk(content=content, metadata=metadata)
        self.upsert([chunk])
        return chunk.id

    def upsert(self, chunks: list[Chunk]) -> None:
        """
        Upsert chunks with dimension verification.

        Args:
            chunks: Chunks to upsert

        Raises:
            ValueError: If no active embedder set
            DimensionMismatchError: If chunk dimension doesn't match active dimension
        """
        self._ensure_embedder_set()

        for chunk in chunks:
            self._prepare_chunk(chunk)
            self._store_chunk(chunk)

    def _ensure_embedder_set(self) -> None:
        """Ensure embedder is set before operations."""
        if not self.active_embedder:
            raise ValueError("No active embedder set. Call set_embedder() first.")

    def _prepare_chunk(self, chunk: Chunk) -> None:
        """Prepare chunk by generating embedding and verifying dimension."""
        # Generate embedding if not present
        if chunk.embedding is None:
            assert self.active_embedder is not None  # Type narrowing
            chunk.embedding = self.active_embedder.encode(chunk.content)

        # Verify dimension
        self._verify_dimension(chunk.embedding)

    def _verify_dimension(self, embedding: npt.NDArray[np.float32]) -> None:
        """Verify embedding dimension matches active dimension."""
        if len(embedding) != self.active_dimension:
            assert self.active_embedder is not None  # Type narrowing
            raise DimensionMismatchError(
                f"Chunk embedding dimension mismatch. "
                f"Expected {self.active_dimension}D "
                f"(from {self.active_embedder.name}), "
                f"got {len(embedding)}D. "
                f"\n\nTo migrate to a different model/dimension, use:\n"
                f"  semvecmem migrate-embeddings --to {self.active_embedder.name}"
            )

    def _store_chunk(self, chunk: Chunk) -> None:
        """Store chunk, replacing if ID exists."""
        assert self.active_collection is not None  # Type narrowing

        if self.backend:
            # Use Qdrant backend
            self.backend.upsert_chunks(self.active_collection, [chunk])
        else:
            # Use in-memory storage
            existing_ids = {c.id for c in self._storage[self.active_collection]}
            if chunk.id in existing_ids:
                self._storage[self.active_collection] = [
                    c for c in self._storage[self.active_collection] if c.id != chunk.id
                ]
            self._storage[self.active_collection].append(chunk)

    def search(
        self, query: str, top_k: int = 5, filter: dict[str, str] | None = None
    ) -> list[SearchResult]:
        """
        Search for similar chunks with optional filtering.

        Args:
            query: Query text
            top_k: Number of results to return
            filter: Optional metadata filter (e.g., {"session_id": "abc123"})

        Returns:
            List of search results with scores and metadata

        Raises:
            ValueError: If no active embedder set
            DimensionMismatchError: If query embedding dimension doesn't match
        """
        self._ensure_embedder_set()

        # Encode and verify query
        assert self.active_embedder is not None  # Type narrowing
        query_vector = self.active_embedder.encode(query)
        self._verify_query_dimension(query_vector)

        # Search
        assert self.active_collection is not None  # Type narrowing

        if self.backend:
            # Use Qdrant backend (TODO: implement backend filtering)
            chunks = self.backend.search(self.active_collection, query_vector, top_k * 2)
            # Apply filter in-memory for now
            filtered_chunks = self._apply_filter(chunks, filter) if filter else chunks
            return self._rank_chunks(query_vector, filtered_chunks, top_k)
        else:
            # Use in-memory storage
            chunks = self._storage.get(self.active_collection, [])
            if not chunks:
                return []
            # Apply filter
            filtered_chunks = self._apply_filter(chunks, filter) if filter else chunks
            return self._rank_chunks(query_vector, filtered_chunks, top_k)

    def _verify_query_dimension(self, query_vector: npt.NDArray[np.float32]) -> None:
        """Verify query embedding dimension matches active dimension."""
        if len(query_vector) != self.active_dimension:
            assert self.active_embedder is not None  # Type narrowing
            raise DimensionMismatchError(
                f"Query embedding dimension mismatch. "
                f"Expected {self.active_dimension}D "
                f"(from {self.active_embedder.name}), "
                f"got {len(query_vector)}D. "
                f"This indicates an embedder configuration error."
            )

    def _apply_filter(self, chunks: list[Chunk], filter: dict[str, str]) -> list[Chunk]:
        """
        Apply metadata filter to chunks.

        Args:
            chunks: Chunks to filter
            filter: Metadata filter (all conditions must match)

        Returns:
            Filtered chunks
        """
        filtered = []
        for chunk in chunks:
            # Check if all filter conditions match
            matches = all(chunk.metadata.get(key) == value for key, value in filter.items())
            if matches:
                filtered.append(chunk)
        return filtered

    def _rank_chunks(
        self, query_vector: npt.NDArray[np.float32], chunks: list[Chunk], top_k: int
    ) -> list[SearchResult]:
        """Rank chunks by cosine similarity and return SearchResult."""
        scores = []
        for chunk in chunks:
            # Cosine similarity
            assert chunk.embedding is not None  # Type narrowing
            # Flatten arrays to ensure 1D vectors
            query_flat = query_vector.flatten()
            chunk_flat = chunk.embedding.flatten()
            sim = np.dot(query_flat, chunk_flat) / (
                np.linalg.norm(query_flat) * np.linalg.norm(chunk_flat)
            )
            # Convert to Python float (handles both scalar and 0-d array)
            scores.append((chunk, float(np.asarray(sim).item())))

        # Sort by similarity (descending) and return top_k
        scores.sort(key=lambda x: x[1], reverse=True)

        # Convert to SearchResult
        results = []
        for chunk, score in scores[:top_k]:
            result = SearchResult(
                content=chunk.content,
                score=score,
                chunk_id=chunk.id,
                metadata=chunk.metadata,
            )
            results.append(result)

        return results

    def count(self) -> int:
        """Get count of chunks in active collection."""
        if not self.active_collection:
            return 0

        if self.backend:
            return self.backend.count(self.active_collection)
        else:
            return len(self._storage.get(self.active_collection, []))
