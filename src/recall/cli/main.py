"""Recall CLI - Semantic vector memory for coding agents.

Command-line interface for ingesting code/text and performing semantic searches.
"""

import sys
from pathlib import Path

import click

from recall.backends.qdrant import QdrantBackend
from recall.chunking.factory import ChunkerFactory
from recall.cli.cleanup import cleanup_test_data
from recall.cli.doctor import doctor
from recall.cli.migrate import migrate_embeddings
from recall.cli.migrate_mode import migrate_mode
from recall.cli.recover import recover
from recall.cli.setup import setup
from recall.config.loader import load_config
from recall.core.store import SearchResult, UnifiedVectorStore
from recall.embedders.sentence_transformer import SentenceTransformerEmbedder


@click.group()
@click.version_option(version="1.3.1", prog_name="recall")
def cli() -> None:
    """Recall - Semantic vector memory for coding agents.

    Store and retrieve code snippets, documentation, and context using
    semantic vector search powered by embeddings and Qdrant.
    """
    pass


@cli.command()
@click.argument("content", type=str)
@click.option(
    "--session-id",
    "-s",
    required=True,
    help="Session identifier for organizing memories",
)
@click.option(
    "--content-type",
    "-t",
    type=click.Choice(["python", "markdown", "json", "prose"], case_sensitive=False),
    help="Content type (auto-detected if not specified)",
)
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True, path_type=Path),
    help="Read content from file instead of argument",
)
def ingest(
    content: str,
    session_id: str,
    content_type: str | None,
    file: Path | None,
) -> None:
    """Ingest content into semantic vector memory.

    Examples:
        recall ingest "def hello(): pass" -s my-session -t python
        recall ingest -f code.py -s my-session
    """
    # Read from file if specified
    if file:
        content = file.read_text()
        click.echo(f"📂 Reading from {file}")

    # Initialize components
    config = load_config("config.yaml")
    embedder = SentenceTransformerEmbedder(config.embedder_model)
    backend = QdrantBackend(host=config.qdrant_host, port=config.qdrant_port)
    store = UnifiedVectorStore(backend=backend)
    store.set_embedder(embedder)

    # Chunk content
    chunker_factory = ChunkerFactory()
    chunks = chunker_factory.chunk(content, content_type=content_type)

    # Ingest chunks
    for chunk in chunks:
        metadata = {"session_id": session_id}
        store.add(chunk.content, metadata=metadata)

    click.echo(
        f"✅ Ingested {len(chunks)} chunks from session '{session_id}'\n"
        f"Content type: {content_type or 'auto-detected'}\n"
        f"Total characters: {len(content)}"
    )


def _display_search_results(results: list[SearchResult]) -> None:
    """Display search results to console (extracted for CC reduction)."""
    if not results:
        click.echo("❌ No matching memories found.")
        return

    click.echo(f"🔍 Found {len(results)} relevant memories:\n")
    for i, result in enumerate(results, 1):
        session = result.metadata.get("session_id", "unknown")
        click.echo(f"--- Memory {i} (Score: {result.score:.3f}) ---")
        click.echo(f"Session: {session}")
        click.echo(f"Content:\n{result.content}\n")


@cli.command(name="search")
@click.argument("query", type=str)
@click.option(
    "--top-k",
    "-k",
    type=int,
    default=10,
    help="Maximum number of results to return",
)
@click.option(
    "--session-id",
    "-s",
    help="Filter results by session ID",
)
@click.option(
    "--min-score",
    type=float,
    default=0.0,
    help="Minimum similarity score (0-1)",
)
def search_command(
    query: str,
    top_k: int,
    session_id: str | None,
    min_score: float,
) -> None:
    """Search semantic vector memory.

    Examples:
        recall search "authentication code" -k 5
        recall search "database setup" -s my-session
    """
    # Initialize components
    config = load_config("config.yaml")
    embedder = SentenceTransformerEmbedder(config.embedder_model)
    backend = QdrantBackend(host=config.qdrant_host, port=config.qdrant_port)
    store = UnifiedVectorStore(backend=backend)
    store.set_embedder(embedder)

    # Build filter and search
    filter_dict = {"session_id": session_id} if session_id else None
    results = store.search(query, top_k=top_k, filter=filter_dict)

    # Filter by min score and display
    filtered_results = [r for r in results if r.score >= min_score]
    _display_search_results(filtered_results)


@cli.command()
def stats() -> None:
    """Show statistics about stored memories."""
    # Initialize components
    config = load_config("config.yaml")
    embedder = SentenceTransformerEmbedder(config.embedder_model)
    backend = QdrantBackend(host=config.qdrant_host, port=config.qdrant_port)
    store = UnifiedVectorStore(backend=backend)
    store.set_embedder(embedder)

    total_chunks = store.count()
    active_collection = store.active_collection or "none"

    click.echo("📊 Recall Statistics:")
    click.echo(f"Total chunks: {total_chunks}")
    click.echo(f"Active collection: {active_collection}")
    click.echo(f"Embedder: {embedder.name}")
    click.echo(f"Dimension: {embedder.dimension}D")
    click.echo(f"Qdrant: {config.qdrant_host}:{config.qdrant_port}")


@cli.command()
def setup_qdrant() -> None:
    """Detect or launch Qdrant vector database.

    Checks if Qdrant is running locally. If not, provides instructions
    for launching via Docker.
    """
    config = load_config("config.yaml")

    # Try to connect
    try:
        backend = QdrantBackend(host=config.qdrant_host, port=config.qdrant_port)
        if backend.health_check():
            click.echo(f"✅ Qdrant is running at {config.qdrant_host}:{config.qdrant_port}")
            return
    except Exception as e:
        click.echo(f"❌ Qdrant not accessible: {e}")

    # Provide setup instructions
    click.echo("\n📦 To start Qdrant locally with Docker:\n")
    click.echo("  docker run -p 6333:6333 -p 6334:6334 \\")
    click.echo("    -v $(pwd)/qdrant_storage:/qdrant/storage \\")
    click.echo("    qdrant/qdrant\n")
    click.echo("Or use docker-compose.yaml in this repository:")
    click.echo("  docker-compose up -d")
    sys.exit(1)


# Add migration commands to CLI group
cli.add_command(migrate_embeddings, name="migrate")
cli.add_command(migrate_mode, name="migrate-mode")

# Add setup, cleanup, and diagnostic commands to CLI group
cli.add_command(setup, name="setup")
cli.add_command(cleanup_test_data, name="cleanup")
cli.add_command(doctor, name="doctor")
cli.add_command(recover, name="recover")


if __name__ == "__main__":
    cli()
