"""Benchmark utilities for accuracy testing.

Shared classes and functions for embedding model benchmarks.
"""

import json
import time
from pathlib import Path
from typing import Any

from recall.backends.qdrant import QdrantBackend
from recall.chunking.factory import ChunkerFactory
from recall.config.loader import load_config
from recall.core.store import UnifiedVectorStore
from recall.embedders.sentence_transformer import SentenceTransformerEmbedder

# Map short model names to full HuggingFace paths
MODEL_NAME_MAP = {
    "snowflake/arctic-embed-m": "Snowflake/snowflake-arctic-embed-m",
    "nomic-embed-text-v1.5": "nomic-ai/nomic-embed-text-v1.5",
    "bge-small-en-v1.5": "BAAI/bge-small-en-v1.5",
    "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
}


class BenchmarkResults:
    """Track benchmark results for a model."""

    def __init__(self, model_name: str):
        """Initialize benchmark results.

        Args:
            model_name: Name of the embedding model
        """
        self.model_name = model_name
        self.total_queries = 0
        self.correct_matches = 0
        self.partial_matches = 0
        self.failed_matches = 0
        self.query_latencies: list[float] = []
        self.query_results: list[dict[str, Any]] = []

    @property
    def accuracy(self) -> float:
        """Calculate accuracy score (0-1)."""
        if self.total_queries == 0:
            return 0.0

        # Exact match = 1.0 points, partial match = 0.5 points
        points = self.correct_matches + (self.partial_matches * 0.5)
        return points / self.total_queries

    @property
    def avg_latency(self) -> float:
        """Calculate average query latency in milliseconds."""
        if not self.query_latencies:
            return 0.0
        return sum(self.query_latencies) / len(self.query_latencies) * 1000

    def add_result(
        self,
        query_id: str,
        matched: bool,
        partial: bool,
        latency: float,
        details: dict[str, Any],
    ) -> None:
        """Add query result.

        Args:
            query_id: Query identifier
            matched: True if expected file found in top results
            partial: True if matched but with lower score
            latency: Query latency in seconds
            details: Additional result details
        """
        self.total_queries += 1
        self.query_latencies.append(latency)

        if matched and not partial:
            self.correct_matches += 1
        elif matched and partial:
            self.partial_matches += 1
        else:
            self.failed_matches += 1

        self.query_results.append(
            {
                "query_id": query_id,
                "matched": matched,
                "partial": partial,
                "latency_ms": latency * 1000,
                **details,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert results to dictionary."""
        return {
            "model": self.model_name,
            "accuracy": self.accuracy,
            "avg_latency_ms": self.avg_latency,
            "total_queries": self.total_queries,
            "correct_matches": self.correct_matches,
            "partial_matches": self.partial_matches,
            "failed_matches": self.failed_matches,
            "query_results": self.query_results,
        }


class AccuracyBenchmark:
    """Run accuracy benchmarks for embedding models."""

    def __init__(self, corpus_dir: Path, ground_truth_file: Path):
        """Initialize benchmark runner.

        Args:
            corpus_dir: Directory containing test corpus
            ground_truth_file: Path to ground truth queries JSON
        """
        self.corpus_dir = corpus_dir
        self.ground_truth_file = ground_truth_file
        self.ground_truth = self._load_ground_truth()
        self.chunker_factory = ChunkerFactory()

    def _load_ground_truth(self) -> dict[str, Any]:
        """Load ground truth queries and expected results."""
        with open(self.ground_truth_file) as f:
            return json.load(f)

    def _load_corpus_files(self) -> list[tuple[Path, str]]:
        """Load all files from corpus directory.

        Returns:
            List of (file_path, content_type) tuples
        """
        files = []

        # Python files
        for py_file in self.corpus_dir.glob("python/*.py"):
            files.append((py_file, "python"))

        # Markdown files
        for md_file in self.corpus_dir.glob("markdown/*.md"):
            files.append((md_file, "markdown"))

        # JSON files
        for json_file in self.corpus_dir.glob("json/*.json"):
            files.append((json_file, "json"))

        return files

    def ingest_corpus(self, store: UnifiedVectorStore) -> int:
        """Ingest test corpus into vector store.

        Args:
            store: Vector store to ingest into

        Returns:
            Number of chunks ingested
        """
        corpus_files = self._load_corpus_files()
        total_chunks = 0

        for file_path, content_type in corpus_files:
            content = file_path.read_text()

            # Chunk content
            chunks = self.chunker_factory.chunk(content, content_type=content_type)

            # Add metadata with source file
            for chunk in chunks:
                metadata = {
                    "source_file": str(file_path.relative_to(self.corpus_dir.parent)),
                    "content_type": content_type,
                }
                store.add(chunk.content, metadata=metadata)
                total_chunks += 1

        return total_chunks

    def run_query(self, store: UnifiedVectorStore, query: dict[str, Any]) -> dict[str, Any]:
        """Run a single benchmark query.

        Args:
            store: Vector store to query
            query: Ground truth query definition

        Returns:
            Query result with accuracy metrics
        """
        start_time = time.time()
        results = store.search(query["query"], top_k=5)
        latency = time.time() - start_time

        # Check if expected file in results
        expected_files = query["expected_files"]
        expected_content = query.get("expected_content_matches", [])
        min_score = query.get("min_relevance_score", 0.7)

        matched = False
        partial = False
        found_file = None
        found_score = 0.0

        for result in results:
            source_file = result.metadata.get("source_file", "")

            # Check if this is an expected file
            for expected in expected_files:
                if expected in source_file:
                    matched = True
                    found_file = source_file
                    found_score = result.score

                    # Check if it's a partial match (lower score)
                    if result.score < min_score:
                        partial = True

                    break

            if matched:
                break

        return {
            "query_id": query["id"],
            "matched": matched,
            "partial": partial,
            "latency": latency,
            "found_file": found_file,
            "found_score": found_score,
            "expected_files": expected_files,
        }

    def benchmark_model(self, model_name: str) -> BenchmarkResults:
        """Run benchmark for a specific model.

        Args:
            model_name: Embedding model to test (short or full name)

        Returns:
            Benchmark results
        """
        print(f"\n📊 Benchmarking: {model_name}")

        # Resolve model name to full HuggingFace path
        resolved_name = MODEL_NAME_MAP.get(model_name, model_name)
        if resolved_name != model_name:
            print(f"  📦 Resolved to: {resolved_name}")

        # Initialize components
        config = load_config("config.yaml")
        embedder = SentenceTransformerEmbedder(resolved_name)
        backend = QdrantBackend(host=config.qdrant_host, port=config.qdrant_port)
        store = UnifiedVectorStore(backend=backend)
        store.set_embedder(embedder)

        # Ingest corpus
        print(f"  📂 Ingesting corpus...")
        num_chunks = self.ingest_corpus(store)
        print(f"  ✅ Ingested {num_chunks} chunks")

        # Run queries
        results = BenchmarkResults(model_name)
        queries = self.ground_truth["queries"]

        print(f"  🔍 Running {len(queries)} benchmark queries...")
        for query in queries:
            result = self.run_query(store, query)
            results.add_result(
                result["query_id"],
                result["matched"],
                result["partial"],
                result["latency"],
                {
                    "found_file": result["found_file"],
                    "found_score": result["found_score"],
                    "expected_files": result["expected_files"],
                },
            )

        print(f"  ✅ Accuracy: {results.accuracy:.1%}")
        print(f"  ⚡ Avg Latency: {results.avg_latency:.1f}ms")

        return results
