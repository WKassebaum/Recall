"""Storage mode migration tool with canary validation.

Migrate memories between embedded and network (Docker) Qdrant modes.
"""

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import click
from dotenv import load_dotenv

from recall.backends.qdrant import QdrantBackend
from recall.config.loader import load_config
from recall.core.store import Chunk, UnifiedVectorStore
from recall.embedders.sentence_transformer import SentenceTransformerEmbedder


@dataclass
class ModeMigrationStats:
    """Track mode migration statistics."""

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


class ModeMigrationError(Exception):
    """Raised when mode migration fails."""

    pass


class ModeCanaryValidator:
    """Validate migration on sample data before full mode migration."""

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
        target_store: UnifiedVectorStore,
        progress_callback: Callable[[str], None] | None = None,
    ) -> tuple[bool, str]:
        """Run canary validation on sample chunks.

        Args:
            source_chunks: Sample chunks to test
            target_store: Target storage to test writes
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
                # Test write to target store (with upsert to avoid duplicates)
                test_chunk = Chunk(
                    content=chunk.content,
                    embedding=chunk.embedding,
                    chunk_id=f"canary_{chunk.id}",
                    metadata={**chunk.metadata, "canary_test": "true"},
                )
                target_store.upsert([test_chunk])

                # Verify write by reading back
                results = target_store.search(
                    chunk.content[:50],  # Search with content prefix
                    top_k=1,
                    filter={"canary_test": "true"},
                )

                if results and results[0].content == chunk.content:
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


class ModeMigrationTool:
    """Migrate memories between embedded and network Qdrant modes."""

    def __init__(
        self,
        source_mode: str,
        target_mode: str,
        canary_size: int = 10,
        batch_size: int = 100,
        progress_callback: Callable[[str], None] | None = None,
    ):
        """Initialize mode migration tool.

        Args:
            source_mode: Current storage mode ("embedded" or "network")
            target_mode: Target storage mode ("embedded" or "network")
            canary_size: Number of chunks for canary validation
            batch_size: Chunks to process per batch
            progress_callback: Optional callback for progress updates
        """
        self.source_mode = source_mode
        self.target_mode = target_mode
        self.canary_size = canary_size
        self.batch_size = batch_size
        self.progress_callback = progress_callback

        self.stats = ModeMigrationStats()
        self.stats.canary_sample_size = canary_size

    def _log(self, message: str) -> None:
        """Log message via callback or print."""
        if self.progress_callback:
            self.progress_callback(message)
        else:
            click.echo(message)

    def migrate(self, dry_run: bool = False) -> ModeMigrationStats:
        """Execute mode migration with canary validation.

        Args:
            dry_run: If True, only validate without migrating

        Returns:
            Migration statistics

        Raises:
            ModeMigrationError: If migration fails
        """
        self.stats.start_time = time.time()

        try:
            # 1. Initialize components
            self._log("🔧 Initializing mode migration...")
            source_store, target_store = self._initialize_stores()

            # 2. Load source chunks
            self._log(f"📦 Loading chunks from {self.source_mode} mode...")
            source_chunks = self._load_source_chunks(source_store)
            self.stats.total_chunks = len(source_chunks)
            self._log(f"Found {self.stats.total_chunks} chunks to migrate")

            if self.stats.total_chunks == 0:
                raise ModeMigrationError("No chunks found in source mode")

            # 3. Canary validation
            canary_passed, canary_message = self._run_canary_validation(source_chunks, target_store)
            self._log(f"{'✅' if canary_passed else '❌'} {canary_message}")

            if not canary_passed:
                raise ModeMigrationError(f"Canary validation failed: {canary_message}")

            self.stats.canary_passed = True

            if dry_run:
                self._log("🏁 Dry run complete - no data migrated")
                self.stats.end_time = time.time()
                return self.stats

            # 4. Full migration
            self._log(f"🚀 Starting full migration ({self.stats.total_chunks} chunks)...")
            self._migrate_chunks(source_chunks, target_store)

            self.stats.end_time = time.time()
            self._log(
                f"✅ Migration complete: {self.stats.migrated_chunks}/{self.stats.total_chunks} "
                f"chunks ({self.stats.duration:.1f}s)"
            )

            return self.stats

        except Exception as e:
            self.stats.end_time = time.time()
            raise ModeMigrationError(f"Migration failed: {e}") from e

    def _initialize_stores(self) -> tuple[UnifiedVectorStore, UnifiedVectorStore]:
        """Initialize source and target storage backends."""
        # Load config and environment
        config = load_config("config.yaml")
        env_file = Path.home() / ".recall" / ".env"
        if env_file.exists():
            load_dotenv(env_file)

        # Get embedder (same for both source and target)
        embedder_model = os.environ.get("RECALL_EMBEDDER_MODEL", config.embedder_model)
        embedder = SentenceTransformerEmbedder(embedder_model)

        # Initialize source backend
        if self.source_mode == "network":
            source_host = os.environ.get("RECALL_QDRANT_HOST", config.qdrant_host)
            source_port = int(os.environ.get("RECALL_QDRANT_PORT", config.qdrant_port))
            source_backend = QdrantBackend(host=source_host, port=source_port)
        else:  # embedded
            source_path = os.environ.get("RECALL_QDRANT_PATH", "~/.recall/qdrant")
            source_backend = QdrantBackend(path=source_path)

        # Initialize target backend
        if self.target_mode == "network":
            # For network target, prompt user for host/port
            target_host = click.prompt("Target Qdrant host", default="localhost", type=str)
            target_port = click.prompt("Target Qdrant port", default=6333, type=int)
            target_backend = QdrantBackend(host=target_host, port=target_port)
        else:  # embedded
            target_path = click.prompt(
                "Target Qdrant path",
                default="~/.recall/qdrant-migrated",
                type=str,
            )
            target_backend = QdrantBackend(path=target_path)

        # Create stores
        source_store = UnifiedVectorStore(backend=source_backend)
        source_store.set_embedder(embedder)

        target_store = UnifiedVectorStore(backend=target_backend)
        target_store.set_embedder(embedder)

        return source_store, target_store

    def _load_source_chunks(self, source_store: UnifiedVectorStore) -> list[Chunk]:
        """Load all chunks from source store."""
        total_chunks = source_store.count()
        if total_chunks == 0:
            return []

        # Use search to retrieve chunks
        results = source_store.search("", top_k=total_chunks)

        chunks = []
        for result in results:
            chunk = Chunk(
                content=result.content,
                chunk_id=result.chunk_id,
                embedding=result.embedding if hasattr(result, "embedding") else None,
                metadata=result.metadata,
            )
            chunks.append(chunk)

        return chunks

    def _run_canary_validation(
        self, source_chunks: list[Chunk], target_store: UnifiedVectorStore
    ) -> tuple[bool, str]:
        """Run canary validation on sample chunks."""
        validator = ModeCanaryValidator(
            sample_size=self.canary_size,
            min_success_rate=0.8,
        )

        return validator.validate(source_chunks, target_store, self.progress_callback)

    def _migrate_chunks(
        self,
        source_chunks: list[Chunk],
        target_store: UnifiedVectorStore,
    ) -> None:
        """Migrate all chunks to target store."""
        # Process in batches
        for i in range(0, len(source_chunks), self.batch_size):
            batch = source_chunks[i : i + self.batch_size]
            self._migrate_batch(batch, target_store)

    def _migrate_batch(
        self,
        batch: list[Chunk],
        target_store: UnifiedVectorStore,
    ) -> None:
        """Migrate a batch of chunks."""
        for chunk in batch:
            try:
                # Upsert chunk to target (preserves embeddings)
                target_store.upsert([chunk])
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
    "--from-mode",
    "-f",
    required=True,
    type=click.Choice(["embedded", "network"], case_sensitive=False),
    help="Source storage mode",
)
@click.option(
    "--to-mode",
    "-t",
    required=True,
    type=click.Choice(["embedded", "network"], case_sensitive=False),
    help="Target storage mode",
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
def migrate_mode(
    from_mode: str,
    to_mode: str,
    canary_size: int,
    batch_size: int,
    dry_run: bool,
) -> None:
    """Migrate memories between embedded and network Qdrant modes.

    Examples:
        recall migrate-mode -f embedded -t network
        recall migrate-mode -f network -t embedded --dry-run
    """
    click.echo("🔄 Starting storage mode migration...\n")
    click.echo(f"Source mode: {from_mode}")
    click.echo(f"Target mode: {to_mode}")
    click.echo(f"Canary size: {canary_size}")
    click.echo(f"Batch size: {batch_size}")
    click.echo(f"Dry run: {dry_run}\n")

    # Warn if migrating from network to embedded
    if from_mode == "network" and to_mode == "embedded":
        click.echo("⚠️  WARNING: Embedded mode has limitations:")
        click.echo("   - ONE project at a time only")
        click.echo("   - File locking prevents concurrent access")
        click.echo("   - Not recommended for multi-project workflows\n")
        if not click.confirm("Continue with migration to embedded mode?"):
            raise click.Abort()

    try:
        tool = ModeMigrationTool(
            source_mode=from_mode,
            target_mode=to_mode,
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

        if not dry_run:
            click.echo("\n✅ Migration complete!")
            click.echo(f"💡 Next step: Update ~/.recall/.env to use '{to_mode}' mode")
            click.echo("   Then restart Claude Code (Cmd/Ctrl + Q)")

    except ModeMigrationError as e:
        click.echo(f"\n❌ Migration failed: {e}", err=True)
        raise click.Abort() from None
