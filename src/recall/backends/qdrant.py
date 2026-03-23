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

"""Qdrant vector database backend."""

import logging
import uuid
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Fusion,
    FusionQuery,
    PointStruct,
    Prefetch,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from recall.core.store import Chunk

logger = logging.getLogger(__name__)


def _extract_dense_vector(vector: Any) -> list[float]:
    """Extract dense vector from either unnamed (list) or named (dict) format."""
    if isinstance(vector, dict):
        return vector.get("dense", vector)
    return vector


class QdrantBackend:
    """Qdrant storage backend for UnifiedVectorStore."""

    def __init__(
        self,
        host: str | None = None,
        port: int = 6333,
        path: str | None = None,
    ) -> None:
        """
        Initialize Qdrant backend.

        Supports both embedded and network modes:
        - Embedded: path="~/.recall/qdrant" (default, recommended)
        - Network: host="localhost", port=6333

        Args:
            host: Qdrant host (for network mode)
            port: Qdrant port (for network mode)
            path: Local storage path (for embedded mode)

        Raises:
            BlockingIOError: If embedded database is already in use by another process
            ValueError: If neither path nor host is provided
        """
        self.mode: str
        self.path: str | None
        self.host: str | None
        self.port: int | None
        self._legacy_collections: set[str] = set()

        if path:
            # Embedded mode (local storage)
            import os

            expanded_path = os.path.expanduser(path)
            try:
                self.client = QdrantClient(path=expanded_path)
                self.mode = "embedded"
                self.path = expanded_path
                self.host = None
                self.port = None
            except BlockingIOError as e:
                raise BlockingIOError(
                    f"Qdrant database at '{expanded_path}' is already in use by another process. "
                    "This can happen when:\n"
                    "  - Multiple Claude Code windows are open\n"
                    "  - Another instance of Recall is running\n"
                    "Solution: Close other instances or use a different storage path via RECALL_QDRANT_PATH"
                ) from e
        elif host:
            # Network mode (Docker or remote)
            self.client = QdrantClient(host=host, port=port)
            self.mode = "network"
            self.host = host
            self.port = port
            self.path = None
        else:
            raise ValueError("Must provide either 'path' (embedded) or 'host' (network)")

    def health_check(self) -> bool:
        """
        Check if Qdrant is accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    def is_legacy_collection(self, collection_name: str) -> bool:
        """Check if a collection uses unnamed vectors (legacy schema)."""
        return collection_name in self._legacy_collections

    def _detect_legacy(self, collection_name: str) -> bool:
        """
        Detect if an existing collection uses unnamed vectors.

        Unnamed vectors: config.params.vectors is a VectorParams object
        Named vectors: config.params.vectors is a dict of VectorParams
        """
        try:
            info = self.client.get_collection(collection_name=collection_name)
            vectors_config = info.config.params.vectors
            return isinstance(vectors_config, VectorParams)
        except Exception:
            return False

    def ensure_collection(
        self, collection_name: str, dimension: int, sparse: bool = False
    ) -> None:
        """
        Ensure collection exists with correct dimension.

        New collections are created with named vectors ("dense") and
        optional sparse vector support. Existing unnamed-vector collections
        operate in legacy mode (dense-only, no sparse).

        Args:
            collection_name: Collection name
            dimension: Embedding dimension
            sparse: Whether to enable sparse vector support
        """
        collections = self.client.get_collections().collections
        existing = [c.name for c in collections]

        if collection_name not in existing:
            # Create new collection with named vectors
            sparse_config = {"sparse": SparseVectorParams()} if sparse else None
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config={"dense": VectorParams(size=dimension, distance=Distance.COSINE)},
                sparse_vectors_config=sparse_config,
            )
        else:
            # Existing collection — detect schema type
            if self._detect_legacy(collection_name):
                self._legacy_collections.add(collection_name)
                logger.warning(
                    "Collection '%s' uses legacy unnamed vectors. "
                    "Sparse/hybrid search disabled. "
                    "Run 'recall migrate-schema' to upgrade.",
                    collection_name,
                )

    @staticmethod
    def _hash_to_uuid(hash_str: str) -> str:
        """
        Convert SHA256 hash to UUID.

        Args:
            hash_str: SHA256 hash string

        Returns:
            UUID string
        """
        # Use first 32 chars of hash as UUID hex
        return str(uuid.UUID(hex=hash_str[:32]))

    def upsert_chunks(self, collection_name: str, chunks: list[Chunk]) -> None:
        """
        Upsert chunks to collection.

        Handles both legacy (unnamed) and named vector schemas.
        Sparse vectors are included when available and collection supports them.

        Args:
            collection_name: Collection name
            chunks: Chunks to upsert
        """
        legacy = self.is_legacy_collection(collection_name)
        points = []
        for chunk in chunks:
            assert chunk.embedding is not None  # Type narrowing
            # Store metadata in payload
            payload = {
                "content": chunk.content,
                "original_id": chunk.id,
                "metadata": chunk.metadata,
            }

            if legacy:
                # Legacy: unnamed vector (list)
                vector: Any = chunk.embedding.tolist()
            else:
                # Named: {"dense": [...], "sparse": SparseVector(...)}
                vector = {"dense": chunk.embedding.tolist()}
                if chunk.sparse_vector is not None:
                    vector["sparse"] = chunk.sparse_vector

            points.append(
                PointStruct(
                    id=self._hash_to_uuid(chunk.id),
                    vector=vector,
                    payload=payload,
                )
            )

        self.client.upsert(collection_name=collection_name, points=points)

    def search(self, collection_name: str, query_vector: Any, top_k: int = 5) -> list[Chunk]:
        """
        Search for similar chunks (dense-only).

        Handles both legacy and named vector schemas.

        Args:
            collection_name: Collection name
            query_vector: Query embedding vector
            top_k: Number of results

        Returns:
            List of similar chunks
        """
        legacy = self.is_legacy_collection(collection_name)

        if legacy:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector.tolist(),
                limit=top_k,
                with_vectors=True,
            )
        else:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=("dense", query_vector.tolist()),
                limit=top_k,
                with_vectors=True,
            )

        return self._results_to_chunks(results)

    def hybrid_search(
        self,
        collection_name: str,
        query_vector: Any,
        sparse_query: SparseVector,
        top_k: int = 5,
    ) -> list[Chunk]:
        """
        Hybrid search combining dense vectors + sparse keyword vectors.

        Uses Qdrant's Reciprocal Rank Fusion (RRF) to merge results
        from both dense (semantic) and sparse (keyword) searches.

        Falls back to dense-only search for legacy collections.

        Args:
            collection_name: Collection name
            query_vector: Dense query embedding vector
            sparse_query: Sparse query vector (from SparseEncoder)
            top_k: Number of results

        Returns:
            List of similar chunks ranked by RRF fusion
        """
        if self.is_legacy_collection(collection_name):
            return self.search(collection_name, query_vector, top_k)

        # Use a two-stage approach: first get keyword matches via sparse search,
        # then re-rank using dense similarity. This ensures keyword-matching
        # chunks always appear in results while dense similarity breaks ties.
        sparse_candidates = top_k * 10

        results = self.client.query_points(
            collection_name=collection_name,
            prefetch=[
                Prefetch(query=sparse_query, using="sparse", limit=sparse_candidates),
            ],
            query=query_vector.tolist(),
            using="dense",
            limit=top_k,
            with_vectors=True,
            with_payload=True,
        ).points

        return self._results_to_chunks(results)

    def _results_to_chunks(self, results: list[Any]) -> list[Chunk]:
        """Convert Qdrant search/query results to Chunk objects."""
        chunks = []
        for result in results:
            chunk_id = result.payload.get("original_id", str(result.id))  # type: ignore[union-attr]
            metadata = result.payload.get("metadata", {})  # type: ignore[union-attr]

            if result.vector is None:
                raise ValueError(
                    "Qdrant did not return vectors in search results. "
                    "Ensure with_vectors=True is set."
                )

            dense_vector = _extract_dense_vector(result.vector)
            embedding = np.array(dense_vector, dtype=np.float32).reshape(-1)

            chunk = Chunk(
                content=result.payload["content"],  # type: ignore[index]
                embedding=embedding,
                chunk_id=chunk_id,
                metadata=metadata,
            )
            chunks.append(chunk)

        return chunks

    def get_all_chunks(
        self, collection_name: str, limit: int = 100, paginate: bool = False
    ) -> list[Chunk]:
        """
        Get all chunks from collection (for chronological queries and migration).

        Args:
            collection_name: Collection name
            limit: Maximum number of chunks per scroll page (or total if paginate=False)
            paginate: If True, scroll through ALL points in the collection

        Returns:
            List of chunks with embeddings
        """
        chunks: list[Chunk] = []
        next_offset = None

        while True:
            # Use scroll to get points without vector search
            points, next_offset = self.client.scroll(
                collection_name=collection_name,
                limit=limit,
                offset=next_offset,
                with_vectors=True,
            )

            for point in points:
                # Extract chunk data from point
                chunk_id = point.payload.get("original_id", str(point.id))  # type: ignore[union-attr]
                metadata = point.payload.get("metadata", {})  # type: ignore[union-attr]

                # Convert vector to numpy array (handles both named and unnamed)
                if point.vector is None:
                    raise ValueError(
                        "Qdrant did not return vectors in scroll results. "
                        "Ensure with_vectors=True is set."
                    )
                dense_vector = _extract_dense_vector(point.vector)
                embedding = np.array(dense_vector, dtype=np.float32).reshape(-1)

                chunk = Chunk(
                    content=point.payload["content"],  # type: ignore[index]
                    embedding=embedding,
                    chunk_id=chunk_id,
                    metadata=metadata,
                )
                chunks.append(chunk)

            # Stop if not paginating or no more pages
            if not paginate or next_offset is None:
                break

        return chunks

    def count(self, collection_name: str) -> int:
        """
        Get count of chunks in collection.

        Args:
            collection_name: Collection name

        Returns:
            Number of chunks
        """
        info = self.client.get_collection(collection_name=collection_name)
        return info.points_count or 0

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete a collection.

        Args:
            collection_name: Collection to delete
        """
        self.client.delete_collection(collection_name=collection_name)
