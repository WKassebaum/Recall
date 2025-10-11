"""Qdrant vector database backend."""

import uuid
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from recall.core.store import Chunk


class QdrantBackend:
    """Qdrant storage backend for UnifiedVectorStore."""

    def __init__(self, host: str = "localhost", port: int = 6333) -> None:
        """
        Initialize Qdrant backend.

        Args:
            host: Qdrant host
            port: Qdrant port
        """
        self.client = QdrantClient(host=host, port=port)
        self.host = host
        self.port = port

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

    def ensure_collection(self, collection_name: str, dimension: int) -> None:
        """
        Ensure collection exists with correct dimension.

        Args:
            collection_name: Collection name
            dimension: Embedding dimension
        """
        collections = self.client.get_collections().collections
        existing = [c.name for c in collections]

        if collection_name not in existing:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
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

        Args:
            collection_name: Collection name
            chunks: Chunks to upsert
        """
        points = []
        for chunk in chunks:
            assert chunk.embedding is not None  # Type narrowing
            # Store metadata in payload
            payload = {
                "content": chunk.content,
                "original_id": chunk.id,
                "metadata": chunk.metadata,
            }
            points.append(
                PointStruct(
                    id=self._hash_to_uuid(chunk.id),
                    vector=chunk.embedding.tolist(),
                    payload=payload,
                )
            )

        self.client.upsert(collection_name=collection_name, points=points)

    def search(self, collection_name: str, query_vector: Any, top_k: int = 5) -> list[Chunk]:
        """
        Search for similar chunks.

        Args:
            collection_name: Collection name
            query_vector: Query embedding vector
            top_k: Number of results

        Returns:
            List of similar chunks
        """
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector.tolist(),
            limit=top_k,
            with_vectors=True,  # Ensure vectors are returned for re-ranking
        )

        chunks = []
        for result in results:
            # Use original_id from payload if available, otherwise use Qdrant ID
            chunk_id = result.payload.get("original_id", str(result.id))  # type: ignore[union-attr]
            # Retrieve metadata from payload
            metadata = result.payload.get("metadata", {})  # type: ignore[union-attr]
            # Convert vector to properly shaped numpy array
            if result.vector is None:
                raise ValueError(
                    "Qdrant did not return vectors in search results. "
                    "Ensure with_vectors=True is set in search call."
                )
            embedding = np.array(result.vector, dtype=np.float32).reshape(-1)
            chunk = Chunk(
                content=result.payload["content"],  # type: ignore[index]
                embedding=embedding,
                chunk_id=chunk_id,
                metadata=metadata,
            )
            chunks.append(chunk)

        return chunks

    def get_all_chunks(self, collection_name: str, limit: int = 100) -> list[Chunk]:
        """
        Get all chunks from collection (for chronological queries).

        Args:
            collection_name: Collection name
            limit: Maximum number of chunks to retrieve

        Returns:
            List of chunks with embeddings
        """
        # Use scroll to get points without vector search
        points, _ = self.client.scroll(
            collection_name=collection_name, limit=limit, with_vectors=True
        )

        chunks = []
        for point in points:
            # Extract chunk data from point
            chunk_id = point.payload.get("original_id", str(point.id))  # type: ignore[union-attr]
            metadata = point.payload.get("metadata", {})  # type: ignore[union-attr]

            # Convert vector to numpy array
            if point.vector is None:
                raise ValueError(
                    "Qdrant did not return vectors in scroll results. "
                    "Ensure with_vectors=True is set."
                )
            embedding = np.array(point.vector, dtype=np.float32).reshape(-1)

            chunk = Chunk(
                content=point.payload["content"],  # type: ignore[index]
                embedding=embedding,
                chunk_id=chunk_id,
                metadata=metadata,
            )
            chunks.append(chunk)

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
