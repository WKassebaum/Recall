"""Benchmark smoke tests - Quick validation without full model testing.

These tests validate the benchmark infrastructure works without
requiring full model downloads or long-running accuracy tests.
"""

import json
from pathlib import Path

import pytest

from tests.benchmark.benchmark_utils import AccuracyBenchmark, BenchmarkResults


@pytest.fixture
def benchmark_runner() -> AccuracyBenchmark:
    """Create benchmark runner with test corpus."""
    corpus_dir = Path(__file__).parent / "corpus"
    ground_truth_file = Path(__file__).parent / "ground_truth.json"
    return AccuracyBenchmark(corpus_dir, ground_truth_file)


def test_ground_truth_loads(benchmark_runner: AccuracyBenchmark) -> None:
    """Verify ground truth file loads correctly."""
    ground_truth = benchmark_runner.ground_truth

    assert "queries" in ground_truth
    assert "accuracy_targets" in ground_truth
    assert len(ground_truth["queries"]) >= 10

    # Verify query structure
    query = ground_truth["queries"][0]
    assert "id" in query
    assert "query" in query
    assert "expected_files" in query
    assert "min_relevance_score" in query


def test_corpus_files_discovered(benchmark_runner: AccuracyBenchmark) -> None:
    """Verify test corpus files are discovered."""
    corpus_files = benchmark_runner._load_corpus_files()

    assert len(corpus_files) > 0, "No corpus files found"

    # Check we have diverse content types
    content_types = {content_type for _, content_type in corpus_files}
    assert "python" in content_types
    assert "markdown" in content_types
    assert "json" in content_types

    print(f"\n✅ Found {len(corpus_files)} corpus files")
    print(f"   Content types: {', '.join(sorted(content_types))}")


def test_accuracy_targets_defined(benchmark_runner: AccuracyBenchmark) -> None:
    """Verify accuracy targets for all models."""
    targets = benchmark_runner.ground_truth["accuracy_targets"]

    required_models = [
        "snowflake/arctic-embed-m",
        "nomic-embed-text-v1.5",
        "bge-small-en-v1.5",
        "all-MiniLM-L6-v2",
    ]

    for model in required_models:
        assert model in targets, f"Missing accuracy target for {model}"
        assert "target_accuracy" in targets[model]
        assert "min_accuracy" in targets[model]

        # Verify targets are reasonable (between 0.7 and 1.0)
        assert 0.7 <= targets[model]["min_accuracy"] <= 1.0
        assert 0.7 <= targets[model]["target_accuracy"] <= 1.0


def test_benchmark_results_tracking() -> None:
    """Verify BenchmarkResults class works correctly."""
    results = BenchmarkResults("test-model")

    # Add some test results
    results.add_result(
        query_id="q1",
        matched=True,
        partial=False,
        latency=0.1,
        details={"found_file": "test.py", "found_score": 0.9},
    )

    results.add_result(
        query_id="q2",
        matched=True,
        partial=True,
        latency=0.15,
        details={"found_file": "test.py", "found_score": 0.6},
    )

    results.add_result(
        query_id="q3",
        matched=False,
        partial=False,
        latency=0.12,
        details={"found_file": None, "found_score": 0.0},
    )

    # Verify calculations
    assert results.total_queries == 3
    assert results.correct_matches == 1
    assert results.partial_matches == 1
    assert results.failed_matches == 1

    # Accuracy: 1.0 + 0.5 + 0.0 = 1.5 / 3 = 0.5
    assert results.accuracy == 0.5

    # Average latency: (100 + 150 + 120) / 3 ≈ 123.33ms
    assert 120 <= results.avg_latency <= 125


def test_corpus_content_readable(benchmark_runner: AccuracyBenchmark) -> None:
    """Verify corpus files are readable."""
    corpus_files = benchmark_runner._load_corpus_files()

    for file_path, content_type in corpus_files:
        assert file_path.exists(), f"Corpus file not found: {file_path}"
        content = file_path.read_text()
        assert len(content) > 0, f"Empty corpus file: {file_path}"

        # Verify content type matches file extension
        if content_type == "python":
            assert file_path.suffix == ".py"
        elif content_type == "markdown":
            assert file_path.suffix == ".md"
        elif content_type == "json":
            assert file_path.suffix == ".json"
            # Verify JSON is valid
            json.loads(content)

    print(f"\n✅ All {len(corpus_files)} corpus files are readable and valid")
