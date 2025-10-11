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

"""Unified Vector Store with dimension verification."""

import hashlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

from recall.embedders.base import EmbedderModel

if TYPE_CHECKING:
    from recall.backends.qdrant import QdrantBackend


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
        self.active_collection = f"recall_{self.active_dimension}d"

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
        self,
        query: str | None = None,
        top_k: int = 5,
        filter: dict[str, str] | None = None,
        retrieval_mode: str = "semantic",
        time_range: tuple[str, str | None] | None = None,
        event_types: list[str] | None = None,
        sort_by: str = "score",
    ) -> list[SearchResult]:
        """
        Search for chunks using semantic similarity OR temporal queries.

        SEMANTIC MODE (default):
          - Search by meaning using vector similarity
          - Returns results ranked by similarity score
          - Requires query parameter

        CHRONOLOGICAL MODE:
          - Search by time range and optional filters
          - Returns results in time order (oldest to newest)
          - Query parameter optional (filters if provided)

        HYBRID MODE:
          - Combines semantic relevance + temporal filtering
          - Returns semantically relevant results from time range
          - Sorted by score or time (configurable)

        Args:
            query: Query text (required for semantic/hybrid, optional for chronological)
            top_k: Number of results to return
            filter: Optional metadata filter (e.g., {"session_id": "abc123"})
            retrieval_mode: "semantic" (default), "chronological", or "hybrid"
            time_range: Optional time range filter ("YYYY-MM-DD", "YYYY-MM-DD" or None)
            event_types: Optional event type filter (e.g., ["decision", "milestone"])
            sort_by: "score" (default) or "time" - how to order results

        Returns:
            List of search results with scores and metadata

        Raises:
            ValueError: If no active embedder set, or invalid mode/parameters
            DimensionMismatchError: If query embedding dimension doesn't match
        """
        self._ensure_embedder_set()

        # Validate parameters
        if retrieval_mode == "semantic" and not query:
            raise ValueError("Semantic mode requires query parameter")
        if retrieval_mode not in ["semantic", "chronological", "hybrid"]:
            raise ValueError(
                f"Invalid retrieval_mode: {retrieval_mode}. "
                "Must be 'semantic', 'chronological', or 'hybrid'"
            )

        # Get all chunks from collection
        assert self.active_collection is not None  # Type narrowing

        if self.backend:
            # Get more chunks if using filters (may need to filter many)
            fetch_limit = top_k * 10 if (time_range or event_types or filter) else top_k
            if query and retrieval_mode != "chronological":
                # Semantic or hybrid - use vector search
                assert self.active_embedder is not None  # Type narrowing
                query_vector = self.active_embedder.encode(query)
                self._verify_query_dimension(query_vector)
                chunks = self.backend.search(self.active_collection, query_vector, fetch_limit)
            else:
                # Chronological - get all chunks (will filter and sort)
                chunks = self.backend.get_all_chunks(self.active_collection, fetch_limit)
        else:
            # Use in-memory storage
            chunks = self._storage.get(self.active_collection, [])
            if not chunks:
                return []

        # Apply metadata filters
        if filter:
            chunks = self._apply_filter(chunks, filter)

        # Apply temporal filter
        if time_range:
            chunks = self._apply_time_filter(chunks, time_range)

        # Apply event type filter
        if event_types:
            chunks = self._apply_event_type_filter(chunks, event_types)

        # Sort and rank based on mode
        if retrieval_mode == "chronological" or sort_by == "time":
            # Sort by timestamp (chronological)
            results = self._sort_chronologically(chunks, top_k)
            # Add similarity scores if query provided
            if query:
                assert self.active_embedder is not None  # Type narrowing
                query_vector = self.active_embedder.encode(query)
                results = self._add_similarity_scores(results, query_vector)
            return results
        elif retrieval_mode == "semantic" or retrieval_mode == "hybrid":
            # Rank by similarity
            assert query is not None  # Type narrowing
            assert self.active_embedder is not None  # Type narrowing
            query_vector = self.active_embedder.encode(query)
            return self._rank_chunks(query_vector, chunks, top_k)
        else:
            return []

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

    def _apply_time_filter(
        self, chunks: list[Chunk], time_range: tuple[str, str | None]
    ) -> list[Chunk]:
        """
        Apply temporal filter to chunks.

        Args:
            chunks: Chunks to filter
            time_range: (start_time, end_time) where end_time can be None for open-ended

        Returns:
            Chunks within time range
        """
        from datetime import datetime, timezone

        start_time_str, end_time_str = time_range
        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        end_time = (
            datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
            if end_time_str
            else datetime.max.replace(tzinfo=timezone.utc)
        )

        filtered = []
        for chunk in chunks:
            ingested_at_str = chunk.metadata.get("ingested_at")
            if not ingested_at_str:
                continue  # Skip chunks without timestamps

            ingested_at = datetime.fromisoformat(ingested_at_str.replace("Z", "+00:00"))
            if start_time <= ingested_at <= end_time:
                filtered.append(chunk)

        return filtered

    def _apply_event_type_filter(self, chunks: list[Chunk], event_types: list[str]) -> list[Chunk]:
        """
        Apply event type filter to chunks.

        Args:
            chunks: Chunks to filter
            event_types: List of event types to include

        Returns:
            Chunks matching event types
        """
        filtered = []
        for chunk in chunks:
            event_type = chunk.metadata.get("event_type")
            if event_type in event_types:
                filtered.append(chunk)
        return filtered

    def _sort_chronologically(self, chunks: list[Chunk], top_k: int) -> list[SearchResult]:
        """
        Sort chunks chronologically and return SearchResult.

        Args:
            chunks: Chunks to sort
            top_k: Number of results to return

        Returns:
            SearchResult list sorted by time (oldest to newest)
        """
        from datetime import datetime

        # Sort by ingested_at timestamp
        sorted_chunks = sorted(
            chunks,
            key=lambda c: datetime.fromisoformat(
                c.metadata.get("ingested_at", "1970-01-01T00:00:00+00:00").replace("Z", "+00:00")
            ),
        )

        # Convert to SearchResult (score=0.0 for chronological)
        results = []
        for chunk in sorted_chunks[:top_k]:
            result = SearchResult(
                content=chunk.content,
                score=0.0,  # No similarity score in chronological mode
                chunk_id=chunk.id,
                metadata=chunk.metadata,
            )
            results.append(result)

        return results

    def _add_similarity_scores(
        self, results: list[SearchResult], query_vector: npt.NDArray[np.float32]
    ) -> list[SearchResult]:
        """
        Add similarity scores to chronologically-sorted results.

        Args:
            results: SearchResult list with score=0.0
            query_vector: Query embedding for similarity calculation

        Returns:
            Same results with updated similarity scores
        """
        # Need to get chunks to calculate similarity
        # For now, return results as-is (scores remain 0.0)
        # TODO: Store embeddings in SearchResult for hybrid queries
        return results

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
