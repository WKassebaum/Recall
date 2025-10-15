"""Migrate Recall data between storage modes (embedded ↔ network)."""

import sys

import click
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from recall.backends.qdrant import QdrantBackend

console = Console()


class ModeMigration:
    """Handle migration between embedded and network storage modes."""

    def __init__(
        self,
        source_mode: str,
        target_mode: str,
        source_path: str | None = None,
        source_host: str | None = None,
        source_port: int | None = None,
        target_path: str | None = None,
        target_host: str | None = None,
        target_port: int | None = None,
    ) -> None:
        self.source_mode = source_mode
        self.target_mode = target_mode

        # Create source backend
        if source_mode == "embedded":
            self.source_backend = QdrantBackend(path=source_path or "~/.recall/qdrant")
        else:
            self.source_backend = QdrantBackend(
                host=source_host or "localhost", port=source_port or 6333
            )

        # Create target backend
        if target_mode == "embedded":
            self.target_backend = QdrantBackend(path=target_path or "~/.recall/qdrant-new")
        else:
            self.target_backend = QdrantBackend(
                host=target_host or "localhost", port=target_port or 6333
            )

    def migrate(self, dry_run: bool = False) -> dict[str, int]:
        """Migrate all data from source to target mode."""
        console.print("\n[bold]Starting mode migration...[/bold]")
        console.print(f"Source: {self.source_mode}")
        console.print(f"Target: {self.target_mode}")

        if dry_run:
            console.print("[yellow]DRY RUN MODE - No data will be modified[/yellow]\n")

        # Get all collections from source
        try:
            source_collections = self.source_backend.client.get_collections().collections
        except Exception as e:
            console.print(f"[red]❌ Failed to connect to source: {e}[/red]")
            raise

        if not source_collections:
            console.print("[yellow]⚠️  No collections found in source[/yellow]")
            return {"total": 0, "migrated": 0, "failed": 0}

        console.print(f"Found {len(source_collections)} collections to migrate\n")

        total_points = 0
        migrated_points = 0
        failed_points = 0

        # Migrate each collection
        for collection in source_collections:
            collection_name = collection.name
            console.print(f"\n[bold cyan]Migrating collection: {collection_name}[/bold cyan]")

            try:
                # Get collection info
                collection_info = self.source_backend.client.get_collection(collection_name)
                vector_size = collection_info.config.params.vectors.size  # type: ignore
                distance = collection_info.config.params.vectors.distance  # type: ignore

                console.print(f"  Vector size: {vector_size}D")
                console.print(f"  Points count: {collection_info.points_count}")

                if dry_run:
                    console.print("  [dim]Skipping (dry run)[/dim]")
                    points_count = collection_info.points_count or 0
                    total_points += points_count
                    migrated_points += points_count
                    continue

                # Create collection in target
                from qdrant_client.models import VectorParams

                try:
                    self.target_backend.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(size=vector_size, distance=distance),
                    )
                    console.print("  ✅ Created target collection")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        console.print("  ⚠️  Target collection already exists")
                    else:
                        raise

                # Scroll through all points
                offset = None
                batch_size = 100

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console,
                ) as progress:
                    task = progress.add_task(
                        f"  Migrating {collection_name}...",
                        total=collection_info.points_count,
                    )

                    while True:
                        # Scroll batch
                        records, next_offset = self.source_backend.client.scroll(
                            collection_name=collection_name,
                            limit=batch_size,
                            offset=offset,
                            with_payload=True,
                            with_vectors=True,
                        )

                        if not records:
                            break

                        total_points += len(records)

                        # Upload batch to target
                        try:
                            from qdrant_client.models import PointStruct

                            points = [
                                PointStruct(
                                    id=record.id, vector=record.vector, payload=record.payload  # type: ignore
                                )
                                for record in records
                            ]

                            self.target_backend.client.upsert(
                                collection_name=collection_name, points=points
                            )

                            migrated_points += len(records)
                            progress.update(task, advance=len(records))

                        except Exception as e:
                            console.print(f"  [red]❌ Failed to migrate batch: {e}[/red]")
                            failed_points += len(records)

                        # Check if we're done
                        if next_offset is None:
                            break

                        offset = next_offset

                console.print(f"  ✅ Migrated {migrated_points} points from {collection_name}")

            except Exception as e:
                console.print(f"  [red]❌ Failed to migrate collection: {e}[/red]")
                failed_points += total_points - migrated_points

        # Summary
        console.print("\n" + "─" * 70)
        console.print("\n[bold green]Migration Complete![/bold green]\n")
        console.print(f"Total points: {total_points}")
        console.print(f"Migrated: {migrated_points}")
        console.print(f"Failed: {failed_points}")

        if not dry_run and failed_points == 0:
            console.print(
                "\n[bold]Next steps:[/bold]\n"
                "1. Verify data in target mode\n"
                "2. Update ~/.recall/.env to use new mode\n"
                "3. Restart Claude Code\n"
            )

        return {"total": total_points, "migrated": migrated_points, "failed": failed_points}


@click.command()
@click.option(
    "--from-mode",
    "-f",
    type=click.Choice(["embedded", "network"]),
    required=True,
    help="Source storage mode",
)
@click.option(
    "--to-mode",
    "-t",
    type=click.Choice(["embedded", "network"]),
    required=True,
    help="Target storage mode",
)
@click.option(
    "--source-path", help="Source path (for embedded mode)", default="~/.recall/qdrant"
)
@click.option("--source-host", help="Source host (for network mode)", default="localhost")
@click.option("--source-port", help="Source port (for network mode)", type=int, default=6333)
@click.option(
    "--target-path", help="Target path (for embedded mode)", default="~/.recall/qdrant-new"
)
@click.option("--target-host", help="Target host (for network mode)", default="localhost")
@click.option("--target-port", help="Target port (for network mode)", type=int, default=6333)
@click.option("--dry-run", is_flag=True, help="Test migration without moving data")
def migrate_mode(
    from_mode: str,
    to_mode: str,
    source_path: str,
    source_host: str,
    source_port: int,
    target_path: str,
    target_host: str,
    target_port: int,
    dry_run: bool,
) -> None:
    """Migrate Recall data between storage modes.

    Examples:
        # Embedded → Network
        recall migrate-mode -f embedded -t network --target-port 6337

        # Network → Embedded
        recall migrate-mode -f network -t embedded

        # Dry run (test without moving data)
        recall migrate-mode -f embedded -t network --dry-run
    """
    if from_mode == to_mode:
        console.print("[red]❌ Source and target modes are the same[/red]")
        sys.exit(1)

    # Confirm migration
    console.print("\n[bold yellow]⚠️  Migration Warning[/bold yellow]")
    console.print(
        f"\nThis will copy all data from {from_mode} mode to {to_mode} mode.\n"
        f"Source data will NOT be deleted (safe operation).\n"
    )

    if not dry_run and not click.confirm("Continue with migration?"):
        console.print("Migration cancelled.")
        sys.exit(0)

    # Create migration instance
    migration = ModeMigration(
        source_mode=from_mode,
        target_mode=to_mode,
        source_path=source_path,
        source_host=source_host,
        source_port=source_port,
        target_path=target_path,
        target_host=target_host,
        target_port=target_port,
    )

    # Run migration
    try:
        stats = migration.migrate(dry_run=dry_run)

        if stats["failed"] > 0:
            sys.exit(1)

    except Exception as e:
        console.print(f"\n[red]❌ Migration failed: {e}[/red]")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    migrate_mode()
