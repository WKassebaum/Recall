"""Embedding model accuracy benchmarks.

Waypoint 15: Benchmark validation (accuracy >85%)

This benchmark:
1. Ingests test corpus with each embedding model
2. Runs ground truth queries
3. Measures accuracy against expected results
4. Validates performance targets (latency <500ms, memory <8GB)
"""

from pathlib import Path
from typing import Optional

import pytest

from tests.benchmark.benchmark_utils import AccuracyBenchmark, BenchmarkResults


def try_benchmark_model(
    benchmark_runner: AccuracyBenchmark, model_name: str
) -> Optional[BenchmarkResults]:
    """Try to run benchmark for a model, returning None if dependencies are missing."""
    try:
        return benchmark_runner.benchmark_model(model_name)
    except ImportError as e:
        pytest.skip(f"Skipping {model_name} benchmark: missing dependency ({e})")
        return None
    except (ValueError, OSError) as e:
        pytest.skip(f"Skipping {model_name} benchmark: model not available ({e})")
        return None


@pytest.fixture
def benchmark_runner() -> AccuracyBenchmark:
    """Create benchmark runner with test corpus."""
    corpus_dir = Path(__file__).parent / "corpus"
    ground_truth_file = Path(__file__).parent / "ground_truth.json"
    return AccuracyBenchmark(corpus_dir, ground_truth_file)


@pytest.mark.benchmark
@pytest.mark.slow
def test_benchmark_arctic_embed_m(benchmark_runner: AccuracyBenchmark) -> None:
    """Waypoint 15: Benchmark Arctic model (primary, target: 87%)."""
    results = benchmark_runner.benchmark_model("snowflake/arctic-embed-m")

    # Get targets from ground truth
    targets = benchmark_runner.ground_truth["accuracy_targets"]["snowflake/arctic-embed-m"]

    # Verify accuracy meets minimum target
    assert (
        results.accuracy >= targets["min_accuracy"]
    ), f"Arctic accuracy {results.accuracy:.1%} < target {targets['min_accuracy']:.1%}"

    # Verify latency
    assert results.avg_latency < 500, f"Avg latency {results.avg_latency:.1f}ms exceeds 500ms"

    print(
        f"\n✅ Arctic Benchmark: {results.accuracy:.1%} (target: {targets['target_accuracy']:.1%})"
    )


@pytest.mark.benchmark
@pytest.mark.slow
def test_benchmark_nomic_embed_text(benchmark_runner: AccuracyBenchmark) -> None:
    """Waypoint 15: Benchmark Nomic model (long context, target: 86.2%).

    Note: Requires einops package. Test skips if dependency not available.
    """
    results = try_benchmark_model(benchmark_runner, "nomic-embed-text-v1.5")
    if results is None:
        return  # Skip handled by try_benchmark_model

    targets = benchmark_runner.ground_truth["accuracy_targets"]["nomic-embed-text-v1.5"]

    assert (
        results.accuracy >= targets["min_accuracy"]
    ), f"Nomic accuracy {results.accuracy:.1%} < target {targets['min_accuracy']:.1%}"

    assert results.avg_latency < 500

    print(f"\n✅ Nomic Benchmark: {results.accuracy:.1%} (target: {targets['target_accuracy']:.1%})")


@pytest.mark.benchmark
@pytest.mark.slow
def test_benchmark_bge_small(benchmark_runner: AccuracyBenchmark) -> None:
    """Waypoint 15: Benchmark BGE model (balanced, target: 84.7%)."""
    results = benchmark_runner.benchmark_model("bge-small-en-v1.5")

    targets = benchmark_runner.ground_truth["accuracy_targets"]["bge-small-en-v1.5"]

    assert (
        results.accuracy >= targets["min_accuracy"]
    ), f"BGE accuracy {results.accuracy:.1%} < target {targets['min_accuracy']:.1%}"

    assert results.avg_latency < 500

    print(f"\n✅ BGE Benchmark: {results.accuracy:.1%} (target: {targets['target_accuracy']:.1%})")


@pytest.mark.benchmark
@pytest.mark.slow
def test_benchmark_minilm(benchmark_runner: AccuracyBenchmark) -> None:
    """Waypoint 15: Benchmark MiniLM model (fallback, target: 78.1%)."""
    results = benchmark_runner.benchmark_model("all-MiniLM-L6-v2")

    targets = benchmark_runner.ground_truth["accuracy_targets"]["all-MiniLM-L6-v2"]

    assert (
        results.accuracy >= targets["min_accuracy"]
    ), f"MiniLM accuracy {results.accuracy:.1%} < target {targets['min_accuracy']:.1%}"

    assert results.avg_latency < 500

    print(
        f"\n✅ MiniLM Benchmark: {results.accuracy:.1%} (target: {targets['target_accuracy']:.1%})"
    )


@pytest.mark.benchmark
@pytest.mark.slow
def test_benchmark_all_models_comparison(benchmark_runner: AccuracyBenchmark) -> None:
    """Waypoint 15: Benchmark all models and generate comparison report.

    Note: Some models may be skipped if dependencies are missing.
    Arctic (primary model) is required to pass.
    """
    models = [
        "snowflake/arctic-embed-m",
        "nomic-embed-text-v1.5",
        "bge-small-en-v1.5",
        "all-MiniLM-L6-v2",
    ]

    all_results = []
    skipped_models = []
    for model in models:
        try:
            results = benchmark_runner.benchmark_model(model)
            all_results.append(results.to_dict())
        except ImportError as e:
            skipped_models.append((model, f"missing dependency ({e})"))
        except (ValueError, OSError) as e:
            skipped_models.append((model, f"model not available ({e})"))

    # Print comparison table
    print("\n" + "=" * 80)
    print("📊 BENCHMARK RESULTS - ALL MODELS")
    print("=" * 80)
    print(f"{'Model':<35} {'Accuracy':>10} {'Latency (ms)':>15} {'Status':>10}")
    print("-" * 80)

    for result in all_results:
        model_name = result["model"]
        accuracy = result["accuracy"]
        latency = result["avg_latency_ms"]

        # Get target
        targets = benchmark_runner.ground_truth["accuracy_targets"].get(model_name, {})
        min_target = targets.get("min_accuracy", 0.0)

        status = "✅ PASS" if accuracy >= min_target else "❌ FAIL"

        print(f"{model_name:<35} {accuracy:>9.1%} {latency:>14.1f} {status:>10}")

    # Print skipped models
    for model, reason in skipped_models:
        print(f"{model:<35} {'N/A':>10} {'N/A':>15} {'⏭️ SKIP':>10}")

    print("=" * 80)
    if skipped_models:
        print(f"Skipped {len(skipped_models)} model(s) due to missing dependencies")

    # Verify at least Arctic passes (required primary model)
    arctic_results = [r for r in all_results if r["model"] == "snowflake/arctic-embed-m"]
    assert arctic_results, "Arctic (primary model) must be available for benchmark"
    assert (
        arctic_results[0]["accuracy"] >= 0.85
    ), "Arctic (primary model) must meet 85% accuracy target"
