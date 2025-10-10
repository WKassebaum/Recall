"""Embedding migration tool with canary validation.

Waypoints 13-14: Safe migration between embedding models with failure testing.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass

import click

from recall.backends.qdrant import QdrantBackend
from recall.config.loader import load_config
from recall.core.store import Chunk, UnifiedVectorStore
from recall.embedders.base import EmbedderModel
from recall.embedders.sentence_transformer import SentenceTransformerEmbedder


@dataclass
class MigrationStats:
    """Track migration statistics."""

    total_chunks: int = 0
    migrated_chunks: int = 0
    failed_chunks: int = 0
    canary_sample_size: int = 0
    canary_passed: bool = False
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def duration(self) -> float:
        """Calculate migration duration in seconds."""
        if self.end_time == 0.0:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0-1)."""
        if self.total_chunks == 0:
            return 0.0
        return self.migrated_chunks / self.total_chunks


class MigrationError(Exception):
    """Raised when migration fails."""

    pass


class CanaryValidator:
    """Validate migration on sample data before full migration."""

    def __init__(
        self,
        sample_size: int = 10,
        min_success_rate: float = 0.8,
    ):
        """Initialize canary validator.

        Args:
            sample_size: Number of chunks to test
            min_success_rate: Minimum success rate to pass (0-1)
        """
        self.sample_size = sample_size
        self.min_success_rate = min_success_rate

    def validate(
        self,
        source_chunks: list[Chunk],
        target_embedder: EmbedderModel,
        progress_callback: Callable[[str], None] | None = None,
    ) -> tuple[bool, str]:
        """Run canary validation on sample chunks.

        Args:
            source_chunks: Sample chunks to test
            target_embedder: New embedder to test
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (passed, message)
        """
        if not source_chunks:
            return False, "No chunks to validate"

        sample = source_chunks[: self.sample_size]
        if progress_callback:
            progress_callback(f"🧪 Testing migration on {len(sample)} sample chunks...")

        success_count = 0
        for chunk in sample:
            try:
                # Re-embed with new model
                new_embedding = target_embedder.encode(chunk.content)

                # Verify embedding has correct dimension
                if len(new_embedding) != target_embedder.dimension:
                    continue

                success_count += 1
            except Exception:
                continue

        success_rate = success_count / len(sample)

        if success_rate >= self.min_success_rate:
            return True, f"Canary passed: {success_rate:.1%} success rate"
        else:
            return (
                False,
                f"Canary failed: {success_rate:.1%} success rate "
                f"(minimum: {self.min_success_rate:.1%})",
            )


class MigrationTool:
    """Migrate embeddings between models with canary validation."""

    def __init__(
        self,
        source_model: str,
        target_model: str,
        canary_size: int = 10,
        batch_size: int = 100,
        progress_callback: Callable[[str], None] | None = None,
    ):
        """Initialize migration tool.

        Args:
            source_model: Current embedding model name
            target_model: New embedding model name
            canary_size: Number of chunks for canary validation
            batch_size: Chunks to process per batch
            progress_callback: Optional callback for progress updates
        """
        self.source_model = source_model
        self.target_model = target_model
        self.canary_size = canary_size
        self.batch_size = batch_size
        self.progress_callback = progress_callback

        self.stats = MigrationStats()
        self.stats.canary_sample_size = canary_size

    def _log(self, message: str) -> None:
        """Log message via callback or print."""
        if self.progress_callback:
            self.progress_callback(message)
        else:
            click.echo(message)

    def migrate(self, dry_run: bool = False) -> MigrationStats:
        """Execute migration with canary validation.

        Args:
            dry_run: If True, only validate without migrating

        Returns:
            Migration statistics

        Raises:
            MigrationError: If migration fails
        """
        self.stats.start_time = time.time()

        try:
            # 1. Initialize components
            self._log("🔧 Initializing migration...")
            source_embedder, target_embedder, backend = self._initialize_components()

            # 2. Load source chunks
            self._log(f"📦 Loading chunks from {self.source_model}...")
            source_chunks = self._load_source_chunks(backend, source_embedder)
            self.stats.total_chunks = len(source_chunks)
            self._log(f"Found {self.stats.total_chunks} chunks to migrate")

            if self.stats.total_chunks == 0:
                raise MigrationError("No chunks found in source collection")

            # 3. Canary validation
            canary_passed, canary_message = self._run_canary_validation(
                source_chunks, target_embedder
            )
            self._log(f"{'✅' if canary_passed else '❌'} {canary_message}")

            if not canary_passed:
                raise MigrationError(f"Canary validation failed: {canary_message}")

            self.stats.canary_passed = True

            if dry_run:
                self._log("🏁 Dry run complete - no data migrated")
                self.stats.end_time = time.time()
                return self.stats

            # 4. Full migration
            self._log(f"🚀 Starting full migration ({self.stats.total_chunks} chunks)...")
            self._migrate_chunks(source_chunks, target_embedder, backend)

            self.stats.end_time = time.time()
            self._log(
                f"✅ Migration complete: {self.stats.migrated_chunks}/{self.stats.total_chunks} "
                f"chunks ({self.stats.duration:.1f}s)"
            )

            return self.stats

        except Exception as e:
            self.stats.end_time = time.time()
            raise MigrationError(f"Migration failed: {e}") from e

    def _initialize_components(
        self,
    ) -> tuple[EmbedderModel, EmbedderModel, QdrantBackend]:
        """Initialize source/target embedders and backend."""
        config = load_config("config.yaml")

        source_embedder = SentenceTransformerEmbedder(self.source_model)
        target_embedder = SentenceTransformerEmbedder(self.target_model)

        backend = QdrantBackend(host=config.qdrant_host, port=config.qdrant_port)

        return source_embedder, target_embedder, backend

    def _load_source_chunks(self, backend: QdrantBackend, embedder: EmbedderModel) -> list[Chunk]:
        """Load all chunks from source collection."""
        # Create temporary store to access source collection
        store = UnifiedVectorStore(backend=backend)
        store.set_embedder(embedder)

        # Retrieve all chunks (search with empty query returns all)
        total_chunks = store.count()
        if total_chunks == 0:
            return []

        # Use search to retrieve chunks (not ideal, but works for POC)
        # In production, would use backend.get_all_chunks() method
        results = store.search("", top_k=total_chunks)

        chunks = []
        for result in results:
            chunk = Chunk(
                content=result.content,
                chunk_id=result.chunk_id,
                metadata=result.metadata,
            )
            chunks.append(chunk)

        return chunks

    def _run_canary_validation(
        self, source_chunks: list[Chunk], target_embedder: EmbedderModel
    ) -> tuple[bool, str]:
        """Run canary validation on sample chunks."""
        validator = CanaryValidator(
            sample_size=self.canary_size,
            min_success_rate=0.8,
        )

        return validator.validate(source_chunks, target_embedder, self.progress_callback)

    def _migrate_chunks(
        self,
        source_chunks: list[Chunk],
        target_embedder: EmbedderModel,
        backend: QdrantBackend,
    ) -> None:
        """Migrate all chunks to target collection."""
        # Create target store
        target_store = UnifiedVectorStore(backend=backend)
        target_store.set_embedder(target_embedder)

        # Process in batches
        for i in range(0, len(source_chunks), self.batch_size):
            batch = source_chunks[i : i + self.batch_size]
            self._migrate_batch(batch, target_embedder, target_store)

    def _migrate_batch(
        self,
        batch: list[Chunk],
        target_embedder: EmbedderModel,
        target_store: UnifiedVectorStore,
    ) -> None:
        """Migrate a batch of chunks."""
        for chunk in batch:
            try:
                # Re-embed with new model
                new_embedding = target_embedder.encode(chunk.content)

                # Create new chunk with new embedding
                new_chunk = Chunk(
                    content=chunk.content,
                    embedding=new_embedding,
                    chunk_id=chunk.id,
                    metadata=chunk.metadata,
                )

                # Upsert to target collection
                target_store.upsert([new_chunk])
                self.stats.migrated_chunks += 1

            except Exception as e:
                self.stats.failed_chunks += 1
                self._log(f"⚠️  Failed to migrate chunk {chunk.id}: {e}")

            # Progress update every 10 chunks
            if self.stats.migrated_chunks % 10 == 0:
                progress = (self.stats.migrated_chunks / self.stats.total_chunks) * 100
                self._log(
                    f"Progress: {progress:.1f}% ({self.stats.migrated_chunks}/{self.stats.total_chunks})"
                )


@click.command()
@click.option(
    "--from-model",
    "-f",
    required=True,
    help="Source embedding model (e.g., all-MiniLM-L6-v2)",
)
@click.option(
    "--to-model",
    "-t",
    required=True,
    help="Target embedding model (e.g., Snowflake/snowflake-arctic-embed-m)",
)
@click.option(
    "--canary-size",
    "-c",
    type=int,
    default=10,
    help="Number of chunks for canary validation",
)
@click.option(
    "--batch-size",
    "-b",
    type=int,
    default=100,
    help="Chunks to process per batch",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Run canary validation only, don't migrate",
)
def migrate_embeddings(
    from_model: str,
    to_model: str,
    canary_size: int,
    batch_size: int,
    dry_run: bool,
) -> None:
    """Migrate embeddings between models with canary validation.

    Examples:
        recall migrate-embeddings -f all-MiniLM-L6-v2 -t snowflake/arctic-embed-m
        recall migrate-embeddings -f all-MiniLM-L6-v2 -t nomic-embed-text-v1.5 --dry-run
    """
    click.echo("🔄 Starting embedding migration...\n")
    click.echo(f"Source model: {from_model}")
    click.echo(f"Target model: {to_model}")
    click.echo(f"Canary size: {canary_size}")
    click.echo(f"Batch size: {batch_size}")
    click.echo(f"Dry run: {dry_run}\n")

    try:
        tool = MigrationTool(
            source_model=from_model,
            target_model=to_model,
            canary_size=canary_size,
            batch_size=batch_size,
            progress_callback=click.echo,
        )

        stats = tool.migrate(dry_run=dry_run)

        # Display final stats
        click.echo("\n📊 Migration Statistics:")
        click.echo(f"Total chunks: {stats.total_chunks}")
        click.echo(f"Migrated: {stats.migrated_chunks}")
        click.echo(f"Failed: {stats.failed_chunks}")
        click.echo(f"Success rate: {stats.success_rate:.1%}")
        click.echo(f"Duration: {stats.duration:.1f}s")
        click.echo(f"Canary passed: {'✅' if stats.canary_passed else '❌'}")

    except MigrationError as e:
        click.echo(f"\n❌ Migration failed: {e}", err=True)
        raise click.Abort() from None
