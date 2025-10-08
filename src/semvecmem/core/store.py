"""Unified Vector Store with dimension verification."""

import hashlib

import numpy as np
import numpy.typing as npt

from semvecmem.embedders.base import EmbedderModel


class DimensionMismatchError(Exception):
    """Raised when embedding dimension doesn't match expected dimension."""

    pass


class Chunk:
    """Code chunk with embedding."""

    def __init__(
        self,
        content: str,
        embedding: npt.NDArray[np.float32] | None = None,
        chunk_id: str | None = None,
    ):
        """
        Initialize chunk.

        Args:
            content: Chunk content
            embedding: Optional embedding vector
            chunk_id: Optional chunk ID (auto-generated if not provided)
        """
        self.content = content
        self.embedding = embedding
        self.id = chunk_id or self._generate_id(content)

    @staticmethod
    def _generate_id(content: str) -> str:
        """Generate deterministic chunk ID from content."""
        return hashlib.sha256(content.encode()).hexdigest()


class UnifiedVectorStore:
    """
    Unified vector store with automatic dimension routing.

    Abstracts multi-collection complexity from users by automatically
    routing to the correct collection based on embedder dimension.
    """

    def __init__(self) -> None:
        """Initialize unified vector store (POC - no actual backend)."""
        self.active_embedder: EmbedderModel | None = None
        self.active_dimension: int | None = None
        self.active_collection: str | None = None

        # POC: Simple in-memory storage
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
        if self.active_collection not in self._storage:
            self._storage[self.active_collection] = []

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

        # Replace existing if ID exists
        existing_ids = {c.id for c in self._storage[self.active_collection]}
        if chunk.id in existing_ids:
            self._storage[self.active_collection] = [
                c for c in self._storage[self.active_collection] if c.id != chunk.id
            ]
        self._storage[self.active_collection].append(chunk)

    def search(self, query: str, top_k: int = 5) -> list[Chunk]:
        """
        Search for similar chunks.

        Args:
            query: Query text
            top_k: Number of results to return

        Returns:
            List of similar chunks

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
        chunks = self._storage.get(self.active_collection, [])
        if not chunks:
            return []

        # Rank and return top_k
        return self._rank_chunks(query_vector, chunks, top_k)

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

    def _rank_chunks(
        self, query_vector: npt.NDArray[np.float32], chunks: list[Chunk], top_k: int
    ) -> list[Chunk]:
        """Rank chunks by cosine similarity."""
        scores = []
        for chunk in chunks:
            # Cosine similarity
            assert chunk.embedding is not None  # Type narrowing
            sim = np.dot(query_vector, chunk.embedding) / (
                np.linalg.norm(query_vector) * np.linalg.norm(chunk.embedding)
            )
            scores.append((chunk, float(sim)))

        # Sort by similarity (descending) and return top_k
        scores.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk, _score in scores[:top_k]]

    def count(self) -> int:
        """Get count of chunks in active collection."""
        if not self.active_collection:
            return 0
        return len(self._storage.get(self.active_collection, []))
