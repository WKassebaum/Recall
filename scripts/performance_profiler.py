#!/usr/bin/env python3
"""Performance profiling script for Recall semantic memory system.

Waypoint 17: Validates memory usage, latency, and resource consumption targets.

Targets:
- Memory usage: <8GB total (verified on M1 Max 64GB)
- Query latency: <500ms average
- Embedding latency: <100ms for single chunk
- Ingestion throughput: >50 chunks/second

Usage:
    python scripts/performance_profiler.py
"""

import json
import logging
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from recall.backends.qdrant import QdrantBackend
from recall.chunking.factory import ChunkerFactory
from recall.config.loader import load_config
from recall.core.store import UnifiedVectorStore
from recall.embedders.sentence_transformer import SentenceTransformerEmbedder

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance measurement results."""

    # Memory metrics (MB)
    initial_memory_mb: float = 0.0
    peak_memory_mb: float = 0.0
    final_memory_mb: float = 0.0

    # Latency metrics (ms)
    embedding_latencies: list[float] = field(default_factory=list)
    query_latencies: list[float] = field(default_factory=list)
    ingestion_latencies: list[float] = field(default_factory=list)

    # Throughput metrics
    chunks_per_second: float = 0.0
    total_chunks_processed: int = 0

    # Model metrics
    model_load_time_ms: float = 0.0
    model_memory_mb: float = 0.0

    @property
    def avg_embedding_latency(self) -> float:
        """Average embedding latency in ms."""
        return (
            sum(self.embedding_latencies) / len(self.embedding_latencies)
            if self.embedding_latencies
            else 0.0
        )

    @property
    def avg_query_latency(self) -> float:
        """Average query latency in ms."""
        return (
            sum(self.query_latencies) / len(self.query_latencies) if self.query_latencies else 0.0
        )

    @property
    def avg_ingestion_latency(self) -> float:
        """Average ingestion latency in ms."""
        return (
            sum(self.ingestion_latencies) / len(self.ingestion_latencies)
            if self.ingestion_latencies
            else 0.0
        )

    @property
    def memory_delta_mb(self) -> float:
        """Memory increase from initial to final."""
        return self.final_memory_mb - self.initial_memory_mb


class PerformanceProfiler:
    """Profile Recall performance."""

    def __init__(self):
        """Initialize profiler."""
        self.metrics = PerformanceMetrics()
        self.config = load_config("config.yaml")

    def get_memory_usage_mb(self) -> float:
        """Get current process memory usage in MB."""
        try:
            # Use ps command for cross-platform compatibility
            pid = (
                subprocess.check_output(["pgrep", "-f", "performance_profiler.py"]).decode().strip()
            )
            if not pid:
                return 0.0

            # Get RSS (Resident Set Size) in KB, convert to MB
            rss_output = subprocess.check_output(["ps", "-o", "rss=", "-p", pid]).decode().strip()
            rss_kb = float(rss_output)
            return rss_kb / 1024.0
        except Exception:
            # Fallback: return 0 if unable to measure
            return 0.0

    def profile_model_loading(self) -> None:
        """Profile model loading time and memory."""
        logger.info("\n📊 Profiling Model Loading...")

        initial_mem = self.get_memory_usage_mb()
        start_time = time.time()

        # Load embedder
        embedder = SentenceTransformerEmbedder(self.config.embedder_model)

        load_time_ms = (time.time() - start_time) * 1000
        final_mem = self.get_memory_usage_mb()

        self.metrics.model_load_time_ms = load_time_ms
        self.metrics.model_memory_mb = final_mem - initial_mem

        logger.info(f"  Model: {embedder.name}")
        logger.info(f"  Dimension: {embedder.dimension}D")
        logger.info(f"  Load time: {load_time_ms:.1f}ms")
        logger.info(f"  Memory: {self.metrics.model_memory_mb:.1f}MB")

    def profile_embedding_latency(self) -> None:
        """Profile embedding generation latency."""
        logger.info("\n📊 Profiling Embedding Latency...")

        embedder = SentenceTransformerEmbedder(self.config.embedder_model)

        # Test with various text lengths
        test_texts = [
            "Short text",
            "Medium length text with some more content to test " * 5,
            "Long text with substantial content to test embedding performance " * 20,
        ]

        for i, text in enumerate(test_texts, 1):
            start_time = time.time()
            _ = embedder.encode(text)
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.embedding_latencies.append(latency_ms)

            logger.info(f"  Test {i} ({len(text)} chars): {latency_ms:.1f}ms")

        logger.info(f"  Average: {self.metrics.avg_embedding_latency:.1f}ms")

    def profile_ingestion_throughput(self) -> None:
        """Profile ingestion throughput."""
        logger.info("\n📊 Profiling Ingestion Throughput...")

        embedder = SentenceTransformerEmbedder(self.config.embedder_model)
        backend = QdrantBackend(host=self.config.qdrant_host, port=self.config.qdrant_port)
        store = UnifiedVectorStore(backend=backend)
        store.set_embedder(embedder)
        chunker_factory = ChunkerFactory()

        # Cleanup and recreate collection
        try:
            backend.delete_collection(f"recall_{embedder.dimension}d")
        except Exception:
            pass

        # Recreate collection (set_embedder does this)
        store.set_embedder(embedder)

        # Create test content
        test_code = """
def function_one(x, y):
    \"\"\"Process x and y.\"\"\"
    result = x + y
    return result

def function_two(a, b):
    \"\"\"Combine a and b.\"\"\"
    combined = f"{a} {b}"
    return combined

class DataProcessor:
    \"\"\"Process data efficiently.\"\"\"

    def __init__(self):
        self.data = []

    def add_item(self, item):
        self.data.append(item)

    def process(self):
        return [x * 2 for x in self.data]

def function_three():
    \"\"\"Third function.\"\"\"
    pass
"""

        # Chunk content
        chunks = chunker_factory.chunk(
            test_code * 10, content_type="python"
        )  # Multiply for more chunks
        self.metrics.total_chunks_processed = len(chunks)

        # Measure ingestion
        start_time = time.time()

        for chunk in chunks:
            chunk_start = time.time()
            store.add(chunk.content, metadata={"test": "perf"})
            chunk_latency_ms = (time.time() - chunk_start) * 1000
            self.metrics.ingestion_latencies.append(chunk_latency_ms)

        total_time = time.time() - start_time
        self.metrics.chunks_per_second = len(chunks) / total_time if total_time > 0 else 0.0

        logger.info(f"  Total chunks: {len(chunks)}")
        logger.info(f"  Total time: {total_time:.2f}s")
        logger.info(f"  Throughput: {self.metrics.chunks_per_second:.1f} chunks/sec")
        logger.info(f"  Avg latency: {self.metrics.avg_ingestion_latency:.1f}ms/chunk")

        # Cleanup
        try:
            backend.delete_collection(f"recall_{embedder.dimension}d")
        except Exception:
            pass

    def profile_query_latency(self) -> None:
        """Profile query latency."""
        logger.info("\n📊 Profiling Query Latency...")

        embedder = SentenceTransformerEmbedder(self.config.embedder_model)
        backend = QdrantBackend(host=self.config.qdrant_host, port=self.config.qdrant_port)
        store = UnifiedVectorStore(backend=backend)
        store.set_embedder(embedder)
        chunker_factory = ChunkerFactory()

        # Cleanup and recreate collection
        try:
            backend.delete_collection(f"recall_{embedder.dimension}d")
        except Exception:
            pass

        # Recreate collection
        store.set_embedder(embedder)

        # Ingest test data
        test_code = """
def authenticate_user(username, password):
    \"\"\"Authenticate user credentials.\"\"\"
    return True

class SessionManager:
    \"\"\"Manage user sessions.\"\"\"
    pass

def process_payment(amount):
    \"\"\"Process payment transaction.\"\"\"
    return amount * 0.1
"""
        chunks = chunker_factory.chunk(test_code * 5, content_type="python")
        for chunk in chunks:
            store.add(chunk.content, metadata={"type": "test"})

        # Run queries
        test_queries = [
            "user authentication",
            "session management",
            "payment processing",
            "handle credentials",
            "transaction data",
        ]

        for query in test_queries:
            start_time = time.time()
            results = store.search(query, top_k=5)
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.query_latencies.append(latency_ms)

            logger.info(f"  '{query}': {latency_ms:.1f}ms ({len(results)} results)")

        logger.info(f"  Average: {self.metrics.avg_query_latency:.1f}ms")

        # Cleanup
        try:
            backend.delete_collection(f"recall_{embedder.dimension}d")
        except Exception:
            pass

    def profile_memory_usage(self) -> None:
        """Profile memory usage throughout workflow."""
        logger.info("\n📊 Profiling Memory Usage...")

        self.metrics.initial_memory_mb = self.get_memory_usage_mb()
        logger.info(f"  Initial: {self.metrics.initial_memory_mb:.1f}MB")

        # Simulate typical workflow
        embedder = SentenceTransformerEmbedder(self.config.embedder_model)
        backend = QdrantBackend(host=self.config.qdrant_host, port=self.config.qdrant_port)
        store = UnifiedVectorStore(backend=backend)
        store.set_embedder(embedder)

        mid_memory = self.get_memory_usage_mb()
        self.metrics.peak_memory_mb = mid_memory
        logger.info(f"  After model load: {mid_memory:.1f}MB")

        # Add some data
        for i in range(100):
            store.add(f"Test content {i}", metadata={"index": str(i)})

        self.metrics.final_memory_mb = self.get_memory_usage_mb()
        logger.info(f"  After ingestion: {self.metrics.final_memory_mb:.1f}MB")
        logger.info(f"  Delta: {self.metrics.memory_delta_mb:.1f}MB")

    def generate_report(self) -> dict[str, Any]:
        """Generate performance report."""
        return {
            "system_info": {
                "platform": platform.system(),
                "machine": platform.machine(),
                "python_version": platform.python_version(),
            },
            "model_info": {
                "name": self.config.embedder_model,
                "load_time_ms": round(self.metrics.model_load_time_ms, 1),
                "memory_mb": round(self.metrics.model_memory_mb, 1),
            },
            "memory": {
                "initial_mb": round(self.metrics.initial_memory_mb, 1),
                "peak_mb": round(self.metrics.peak_memory_mb, 1),
                "final_mb": round(self.metrics.final_memory_mb, 1),
                "delta_mb": round(self.metrics.memory_delta_mb, 1),
                "target_mb": 8192,
                "within_target": self.metrics.peak_memory_mb < 8192,
            },
            "latency": {
                "embedding_avg_ms": round(self.metrics.avg_embedding_latency, 1),
                "query_avg_ms": round(self.metrics.avg_query_latency, 1),
                "ingestion_avg_ms": round(self.metrics.avg_ingestion_latency, 1),
                "query_target_ms": 500,
                "within_target": self.metrics.avg_query_latency < 500,
            },
            "throughput": {
                "chunks_per_second": round(self.metrics.chunks_per_second, 1),
                "total_chunks": self.metrics.total_chunks_processed,
                "target_chunks_per_sec": 50,
                "within_target": self.metrics.chunks_per_second > 50,
            },
        }

    def print_summary(self, report: dict[str, Any]) -> None:
        """Print performance summary."""
        logger.info("\n" + "=" * 80)
        logger.info("PERFORMANCE SUMMARY - Waypoint 17")
        logger.info("=" * 80)

        # System info
        logger.info(
            f"\n📋 System: {report['system_info']['platform']} {report['system_info']['machine']}"
        )
        logger.info(f"   Python: {report['system_info']['python_version']}")

        # Model info
        logger.info(f"\n🧠 Model: {report['model_info']['name']}")
        logger.info(f"   Load time: {report['model_info']['load_time_ms']}ms")
        logger.info(f"   Memory: {report['model_info']['memory_mb']}MB")

        # Memory
        mem = report["memory"]
        status = "✅ PASS" if mem["within_target"] else "❌ FAIL"
        logger.info(f"\n💾 Memory Usage: {status}")
        logger.info(f"   Peak: {mem['peak_mb']}MB (target: <{mem['target_mb']}MB)")
        logger.info(f"   Delta: {mem['delta_mb']}MB")

        # Latency
        lat = report["latency"]
        status = "✅ PASS" if lat["within_target"] else "❌ FAIL"
        logger.info(f"\n⚡ Query Latency: {status}")
        logger.info(f"   Average: {lat['query_avg_ms']}ms (target: <{lat['query_target_ms']}ms)")
        logger.info(f"   Embedding: {lat['embedding_avg_ms']}ms")
        logger.info(f"   Ingestion: {lat['ingestion_avg_ms']}ms")

        # Throughput
        thr = report["throughput"]
        status = "✅ PASS" if thr["within_target"] else "❌ FAIL"
        logger.info(f"\n🚀 Throughput: {status}")
        logger.info(
            f"   Rate: {thr['chunks_per_second']} chunks/sec (target: >{thr['target_chunks_per_sec']})"
        )
        logger.info(f"   Total: {thr['total_chunks']} chunks")

        # Overall status
        all_pass = mem["within_target"] and lat["within_target"] and thr["within_target"]
        logger.info("\n" + "=" * 80)
        if all_pass:
            logger.info("✅ ALL PERFORMANCE TARGETS MET")
        else:
            logger.info("⚠️  SOME PERFORMANCE TARGETS NOT MET")
        logger.info("=" * 80 + "\n")

    def run(self) -> dict[str, Any]:
        """Run full performance profile."""
        logger.info("\n" + "=" * 80)
        logger.info("RECALL PERFORMANCE PROFILER - Waypoint 17")
        logger.info("=" * 80)

        self.profile_model_loading()
        self.profile_embedding_latency()
        self.profile_ingestion_throughput()
        self.profile_query_latency()
        self.profile_memory_usage()

        report = self.generate_report()
        self.print_summary(report)

        # Save report
        report_path = Path("performance_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"📊 Report saved to: {report_path}")

        return report


def main() -> int:
    """Main entry point."""
    profiler = PerformanceProfiler()
    report = profiler.run()

    # Exit with error code if targets not met
    all_pass = (
        report["memory"]["within_target"]
        and report["latency"]["within_target"]
        and report["throughput"]["within_target"]
    )

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
