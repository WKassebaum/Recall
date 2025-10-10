"""Tests for embedding migration tool.

Waypoint 13: Migration tool validation (CC ≤ 8, coverage >80%)
Waypoint 14: Failure injection tests (MOST CRITICAL)
"""

from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from recall.cli.migrate import (
    CanaryValidator,
    MigrationError,
    MigrationStats,
    MigrationTool,
)
from recall.core.store import Chunk


class TestMigrationStats:
    """Test MigrationStats dataclass."""

    def test_stats_initialization(self) -> None:
        """Verify stats initialize with correct defaults."""
        stats = MigrationStats()
        assert stats.total_chunks == 0
        assert stats.migrated_chunks == 0
        assert stats.failed_chunks == 0
        assert stats.canary_passed is False

    def test_success_rate_calculation(self) -> None:
        """Verify success rate calculation."""
        stats = MigrationStats(total_chunks=100, migrated_chunks=90)
        assert stats.success_rate == 0.9

    def test_success_rate_with_zero_chunks(self) -> None:
        """Verify success rate returns 0 when no chunks."""
        stats = MigrationStats()
        assert stats.success_rate == 0.0

    def test_duration_calculation(self) -> None:
        """Verify duration calculation."""
        stats = MigrationStats(start_time=100.0, end_time=150.0)
        assert stats.duration == 50.0


class TestCanaryValidator:
    """Waypoint 13: Test canary validation logic."""

    def test_validator_initialization(self) -> None:
        """Verify validator initializes correctly."""
        validator = CanaryValidator(sample_size=5, min_success_rate=0.7)
        assert validator.sample_size == 5
        assert validator.min_success_rate == 0.7

    def test_canary_passes_with_valid_chunks(self) -> None:
        """Waypoint 13: Verify canary passes with valid data."""
        validator = CanaryValidator(sample_size=3, min_success_rate=0.8)

        # Create mock chunks
        chunks = [
            Chunk(content="chunk 1", chunk_id="id1"),
            Chunk(content="chunk 2", chunk_id="id2"),
            Chunk(content="chunk 3", chunk_id="id3"),
        ]

        # Mock embedder
        mock_embedder = MagicMock()
        mock_embedder.dimension = 384
        mock_embedder.encode.return_value = np.random.rand(384).astype(np.float32)

        passed, message = validator.validate(chunks, mock_embedder)

        assert passed is True
        assert "Canary passed" in message
        assert "100.0%" in message

    def test_canary_fails_with_low_success_rate(self) -> None:
        """Waypoint 14: CRITICAL - Verify canary fails when success rate too low."""
        validator = CanaryValidator(sample_size=3, min_success_rate=0.8)

        chunks = [
            Chunk(content="chunk 1", chunk_id="id1"),
            Chunk(content="chunk 2", chunk_id="id2"),
            Chunk(content="chunk 3", chunk_id="id3"),
        ]

        # Mock embedder that fails 2/3 times
        mock_embedder = MagicMock()
        mock_embedder.dimension = 384
        mock_embedder.encode.side_effect = [
            np.random.rand(384).astype(np.float32),  # Success
            Exception("Embedding failed"),  # Fail
            Exception("Embedding failed"),  # Fail
        ]

        passed, message = validator.validate(chunks, mock_embedder)

        assert passed is False
        assert "Canary failed" in message
        assert "33.3%" in message

    def test_canary_fails_with_dimension_mismatch(self) -> None:
        """Waypoint 14: CRITICAL - Verify canary detects dimension mismatches."""
        validator = CanaryValidator(sample_size=2, min_success_rate=0.8)

        chunks = [
            Chunk(content="chunk 1", chunk_id="id1"),
            Chunk(content="chunk 2", chunk_id="id2"),
        ]

        # Mock embedder returning wrong dimension
        mock_embedder = MagicMock()
        mock_embedder.dimension = 384
        mock_embedder.encode.return_value = np.random.rand(768).astype(
            np.float32
        )  # Wrong dimension

        passed, message = validator.validate(chunks, mock_embedder)

        assert passed is False
        assert "Canary failed" in message

    def test_canary_handles_empty_chunks(self) -> None:
        """Waypoint 14: CRITICAL - Verify canary handles empty input."""
        validator = CanaryValidator()

        mock_embedder = MagicMock()
        passed, message = validator.validate([], mock_embedder)

        assert passed is False
        assert "No chunks to validate" in message

    def test_canary_uses_sample_size_limit(self) -> None:
        """Waypoint 13: Verify canary only tests sample_size chunks."""
        validator = CanaryValidator(sample_size=2)

        chunks = [Chunk(content=f"chunk {i}", chunk_id=f"id{i}") for i in range(10)]

        mock_embedder = MagicMock()
        mock_embedder.dimension = 384
        mock_embedder.encode.return_value = np.random.rand(384).astype(np.float32)

        validator.validate(chunks, mock_embedder)

        # Should only encode 2 chunks (sample_size)
        assert mock_embedder.encode.call_count == 2


class TestMigrationTool:
    """Waypoint 13-14: Test migration tool with failure injection."""

    @pytest.fixture
    def mock_components(self) -> dict:
        """Create mocked components for testing."""
        with patch("recall.cli.migrate.load_config") as mock_config, patch(
            "recall.cli.migrate.SentenceTransformerEmbedder"
        ) as mock_embedder_class, patch(
            "recall.cli.migrate.QdrantBackend"
        ) as mock_backend_class, patch(
            "recall.cli.migrate.UnifiedVectorStore"
        ) as mock_store_class:
            # Configure config
            mock_config.return_value = MagicMock(qdrant_host="localhost", qdrant_port=6333)

            # Configure embedders
            mock_source_embedder = MagicMock()
            mock_source_embedder.dimension = 384
            mock_source_embedder.encode.return_value = np.random.rand(384).astype(np.float32)

            mock_target_embedder = MagicMock()
            mock_target_embedder.dimension = 768
            mock_target_embedder.encode.return_value = np.random.rand(768).astype(np.float32)

            mock_embedder_class.side_effect = [
                mock_source_embedder,
                mock_target_embedder,
            ]

            # Configure backend
            mock_backend = MagicMock()
            mock_backend_class.return_value = mock_backend

            # Configure store
            mock_store = MagicMock()
            mock_store.count.return_value = 10
            mock_store.search.return_value = [
                MagicMock(
                    content=f"chunk {i}",
                    chunk_id=f"id{i}",
                    metadata={"session": "test"},
                )
                for i in range(10)
            ]
            mock_store_class.return_value = mock_store

            yield {
                "config": mock_config,
                "embedder_class": mock_embedder_class,
                "backend": mock_backend,
                "store": mock_store,
                "source_embedder": mock_source_embedder,
                "target_embedder": mock_target_embedder,
            }

    def test_migration_tool_initialization(self) -> None:
        """Waypoint 13: Verify tool initializes correctly."""
        tool = MigrationTool(
            source_model="model-a",
            target_model="model-b",
            canary_size=5,
            batch_size=50,
        )

        assert tool.source_model == "model-a"
        assert tool.target_model == "model-b"
        assert tool.canary_size == 5
        assert tool.batch_size == 50
        assert tool.stats.canary_sample_size == 5

    def test_successful_migration(self, mock_components: dict) -> None:
        """Waypoint 13: Verify successful migration flow."""
        tool = MigrationTool(source_model="model-a", target_model="model-b", canary_size=3)

        stats = tool.migrate(dry_run=False)

        assert stats.total_chunks == 10
        assert stats.migrated_chunks == 10
        assert stats.failed_chunks == 0
        assert stats.canary_passed is True
        assert stats.success_rate == 1.0

    def test_dry_run_migration(self, mock_components: dict) -> None:
        """Waypoint 13: Verify dry run doesn't migrate data."""
        tool = MigrationTool(source_model="model-a", target_model="model-b", canary_size=3)

        stats = tool.migrate(dry_run=True)

        assert stats.canary_passed is True
        assert stats.migrated_chunks == 0  # Dry run shouldn't migrate

    def test_migration_fails_on_canary_failure(self, mock_components: dict) -> None:
        """Waypoint 14: CRITICAL - Verify migration aborts when canary fails."""
        # Make target embedder fail
        mock_components["target_embedder"].encode.side_effect = Exception("Embedding failed")

        tool = MigrationTool(source_model="model-a", target_model="model-b", canary_size=3)

        with pytest.raises(MigrationError, match="Canary validation failed"):
            tool.migrate()

    def test_migration_fails_with_no_source_chunks(self, mock_components: dict) -> None:
        """Waypoint 14: CRITICAL - Verify migration fails gracefully with no data."""
        # Make store return 0 chunks
        mock_components["store"].count.return_value = 0
        mock_components["store"].search.return_value = []

        tool = MigrationTool(source_model="model-a", target_model="model-b")

        with pytest.raises(MigrationError, match="No chunks found"):
            tool.migrate()

    def test_partial_migration_failure(self, mock_components: dict) -> None:
        """Waypoint 14: CRITICAL - Verify tool handles partial failures."""
        # Make embedder fail on some chunks
        mock_components["target_embedder"].encode.side_effect = [
            np.random.rand(768).astype(np.float32),  # Canary samples succeed
            np.random.rand(768).astype(np.float32),
            np.random.rand(768).astype(np.float32),
            np.random.rand(768).astype(np.float32),  # Success
            Exception("Embedding failed"),  # Fail
            np.random.rand(768).astype(np.float32),  # Success
            Exception("Embedding failed"),  # Fail
            np.random.rand(768).astype(np.float32),  # Success
            np.random.rand(768).astype(np.float32),  # Success
            np.random.rand(768).astype(np.float32),  # Success
            np.random.rand(768).astype(np.float32),  # Success
            np.random.rand(768).astype(np.float32),  # Success
            np.random.rand(768).astype(np.float32),  # Success
        ]

        tool = MigrationTool(source_model="model-a", target_model="model-b", canary_size=3)

        stats = tool.migrate()

        assert stats.total_chunks == 10
        assert stats.migrated_chunks == 8  # 2 failed
        assert stats.failed_chunks == 2
        assert stats.success_rate == 0.8

    def test_migration_progress_callback(self, mock_components: dict) -> None:
        """Waypoint 13: Verify progress callback is called."""
        messages = []

        def callback(msg: str) -> None:
            messages.append(msg)

        tool = MigrationTool(
            source_model="model-a",
            target_model="model-b",
            progress_callback=callback,
        )

        tool.migrate(dry_run=True)

        assert len(messages) > 0
        assert any("Initializing" in msg for msg in messages)
        assert any("Testing migration" in msg for msg in messages)

    def test_migration_with_batch_processing(self, mock_components: dict) -> None:
        """Waypoint 13: Verify batching works correctly."""
        tool = MigrationTool(
            source_model="model-a",
            target_model="model-b",
            batch_size=3,  # Small batch for testing
        )

        stats = tool.migrate()

        # With 10 chunks and batch_size=3, should process 4 batches
        assert stats.migrated_chunks == 10

    def test_migration_backend_initialization_failure(self, mock_components: dict) -> None:
        """Waypoint 14: CRITICAL - Verify graceful failure on backend error."""
        # Make backend initialization fail
        with patch("recall.cli.migrate.QdrantBackend", side_effect=Exception("Connection failed")):
            tool = MigrationTool(source_model="model-a", target_model="model-b")

            with pytest.raises(MigrationError, match="Migration failed"):
                tool.migrate()

    def test_migration_handles_corrupted_chunk_data(self, mock_components: dict) -> None:
        """Waypoint 14: CRITICAL - Verify canary prevents migration with corrupted data."""
        # Return chunks with missing/invalid data
        mock_components["store"].search.return_value = [
            MagicMock(content=None, chunk_id="id1", metadata={}),  # Corrupted
            MagicMock(content="valid", chunk_id="id2", metadata={"session": "test"}),
        ]
        mock_components["store"].count.return_value = 2

        # Make embedder fail on None content
        def embed_side_effect(content):
            if content is None:
                raise ValueError("Cannot embed None content")
            return np.random.rand(768).astype(np.float32)

        mock_components["target_embedder"].encode.side_effect = embed_side_effect

        tool = MigrationTool(source_model="model-a", target_model="model-b")

        # Canary should detect corrupted data and prevent migration
        with pytest.raises(MigrationError, match="Canary validation failed"):
            tool.migrate()
