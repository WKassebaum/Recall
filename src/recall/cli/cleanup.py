"""Cleanup command for removing test data from Recall."""

import os
from pathlib import Path

import click
from dotenv import load_dotenv
from qdrant_client.models import FieldCondition, Filter, MatchValue
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from recall.backends.qdrant import QdrantBackend

console = Console()


@click.command()
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be deleted without actually deleting",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Skip confirmation prompt",
)
def cleanup_test_data(dry_run: bool, yes: bool) -> None:
    """Remove test data pollution from Recall database.

    Deletes memories from test sessions that interfere with semantic search quality.
    """
    # Load .env configuration
    env_file = Path.home() / ".recall" / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    # Initialize backend based on mode
    qdrant_mode = os.environ.get("RECALL_QDRANT_MODE", "embedded")

    if qdrant_mode == "network":
        host = os.environ.get("RECALL_QDRANT_HOST", "localhost")
        port = int(os.environ.get("RECALL_QDRANT_PORT", "6333"))
        backend = QdrantBackend(host=host, port=port)
        console.print(f"[cyan]Connected to network mode: {host}:{port}[/cyan]")
    else:
        qdrant_path = os.environ.get("RECALL_QDRANT_PATH", "~/.recall/qdrant")
        backend = QdrantBackend(path=qdrant_path)
        console.print(f"[cyan]Connected to embedded mode: {qdrant_path}[/cyan]")

    print()

    # Test session IDs to remove
    test_sessions = [
        "metadata-test",
        "session-a",
        "session-b",
        "test-session-auth",
        "test-session-markdown",
        "test-session-python",
        "test-session-score",
    ]

    # Get collection name (should be recall_768d for Arctic)
    collections = backend.client.get_collections().collections
    collection_names = [c.name for c in collections]

    if not collection_names:
        console.print("[yellow]No collections found in database[/yellow]")
        return

    # Use first available collection (usually recall_768d)
    collection_name = collection_names[0]

    # Count test data in each session
    table = Table(title="Test Data to be Deleted", show_header=True)
    table.add_column("Session ID", style="yellow", width=30)
    table.add_column("Memory Count", style="red", justify="right")
    table.add_column("Sample Content", style="dim")

    total_to_delete = 0
    session_counts = {}

    for session_id in test_sessions:
        records, _ = backend.client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="metadata.session_id",
                        match=MatchValue(value=session_id),
                    )
                ]
            ),
            limit=100,
            with_payload=True,
            with_vectors=False,
        )

        if records:
            count = len(records)
            total_to_delete += count
            session_counts[session_id] = count

            # Get sample content
            payload = records[0].payload if records[0].payload else {}
            sample = payload.get("content", "")[:50]
            table.add_row(session_id, str(count), f"{sample}...")

    if total_to_delete == 0:
        console.print("[green]✓ No test data found - database is already clean![/green]")
        return

    console.print(table)
    print()

    # Show summary
    summary = Panel(
        f"[bold]Total test memories to delete: {total_to_delete}[/bold]\n"
        f"Collection: {collection_name}\n"
        f"Mode: {qdrant_mode}",
        title="Summary",
        border_style="yellow",
    )
    console.print(summary)
    print()

    # Dry run mode
    if dry_run:
        console.print("[yellow]DRY RUN - No data will be deleted[/yellow]")
        return

    # Confirmation prompt
    if not yes:
        confirm = click.confirm(
            "⚠️  This will permanently delete these test memories. Continue?",
            default=False,
        )
        if not confirm:
            console.print("[yellow]Cancelled - no data deleted[/yellow]")
            return

    # Delete test data
    console.print()
    console.print("[yellow]Deleting test data...[/yellow]")

    deleted_count = 0
    for session_id, count in session_counts.items():
        # Delete by session_id filter
        backend.client.delete(
            collection_name=collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="metadata.session_id",
                        match=MatchValue(value=session_id),
                    )
                ]
            ),
        )
        deleted_count += count
        console.print(f"  ✓ Deleted {count} memories from {session_id}")

    print()
    console.print(f"[green]✓ Successfully deleted {deleted_count} test memories![/green]")
    console.print()
    console.print("[dim]Run 'recall stats' to see updated database statistics[/dim]")


if __name__ == "__main__":
    cleanup_test_data()
