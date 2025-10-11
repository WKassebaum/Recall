"""Recall MCP Server - Semantic vector memory for coding agents."""

import logging
import os
import sys
import warnings
from datetime import datetime, timezone
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from recall.backends.qdrant import QdrantBackend
from recall.chunking.factory import ChunkerFactory
from recall.config.loader import Config, load_config
from recall.core.store import UnifiedVectorStore
from recall.embedders.sentence_transformer import SentenceTransformerEmbedder

# Suppress all logging to stdout (MCP protocol requires clean stdout)
# Redirect to stderr or disable entirely
logging.basicConfig(
    level=logging.ERROR,  # Only errors
    stream=sys.stderr,  # Send to stderr, not stdout
    format="%(message)s",
)

# Suppress sentence-transformers warnings
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Suppress httpx logging
logging.getLogger("httpx").setLevel(logging.ERROR)

# Initialize FastMCP server
mcp = FastMCP("recall")

# Global components (initialized lazily)
_config: Config | None = None
_chunker_factory: ChunkerFactory | None = None
_embedder: SentenceTransformerEmbedder | None = None
_store: UnifiedVectorStore | None = None


def get_components() -> (
    tuple[Config, ChunkerFactory, SentenceTransformerEmbedder, UnifiedVectorStore]
):
    """Get or initialize Recall components."""
    global _config, _chunker_factory, _embedder, _store

    if _config is None:
        # Load configuration
        _config = load_config("config.yaml")

        # Initialize chunker factory
        _chunker_factory = ChunkerFactory()

        # Initialize embedder
        _embedder = SentenceTransformerEmbedder(_config.embedder_model)

        # Initialize Qdrant backend
        backend = QdrantBackend(host=_config.qdrant_host, port=_config.qdrant_port)

        # Initialize unified store
        _store = UnifiedVectorStore(backend=backend)
        _store.set_embedder(_embedder)

    assert _config is not None  # Type narrowing
    assert _chunker_factory is not None
    assert _embedder is not None
    assert _store is not None

    return _config, _chunker_factory, _embedder, _store


@mcp.tool()
async def ingest_memory(
    content: Annotated[str, Field(description="Content to store in vector memory")],
    session_id: Annotated[str, Field(description="Session identifier for filtering")],
    content_type: Annotated[
        str | None,
        Field(description='Optional content type hint ("python", "markdown", "json", "prose")'),
    ] = None,
    metadata: Annotated[
        dict[str, str] | None, Field(description="Optional additional metadata")
    ] = None,
) -> str:
    """
    Ingest content into semantic vector memory.

    Automatically chunks content based on type, generates embeddings,
    and stores in vector database with metadata for session-based filtering.

    Args:
        content: Content to store (code, text, JSON, markdown)
        session_id: Session ID for organizing and filtering memories
        content_type: Optional type hint (auto-detected if not provided)
        metadata: Optional metadata (tags, timestamps, etc.)

    Returns:
        Success message with ingestion statistics
    """
    _, chunker_factory, _, store = get_components()

    # Prepare metadata
    meta = metadata or {}
    meta["session_id"] = session_id
    meta["ingested_at"] = datetime.now(timezone.utc).isoformat()

    # Chunk content using factory (auto-detects type if not specified)
    chunks = chunker_factory.chunk(content, content_type=content_type)

    # Ingest chunks with metadata
    ingested_ids = []
    for chunk in chunks:
        # Add chunk-specific metadata
        chunk_metadata = {**meta, "chunk_id": chunk.id}
        chunk_id = store.add(chunk.content, metadata=chunk_metadata)
        ingested_ids.append(chunk_id)

    # Return success message
    return (
        f"✅ Ingested {len(chunks)} chunks from session '{session_id}'\n"
        f"Content type: {content_type or 'auto-detected'}\n"
        f"Total characters: {len(content)}\n"
        f"Average chunk size: {len(content) // len(chunks) if chunks else 0} chars"
    )


@mcp.tool()
async def recall_memory(
    query: Annotated[str, Field(description="Semantic search query")],
    top_k: Annotated[int, Field(description="Maximum number of results to return")] = 10,
    session_id: Annotated[
        str | None, Field(description="Optional session ID to filter results")
    ] = None,
    min_score: Annotated[
        float, Field(description="Minimum similarity score threshold (0-1)")
    ] = 0.0,
) -> str:
    """
    Search semantic vector memory for relevant content.

    Uses cosine similarity to find semantically similar chunks,
    with optional session-based filtering.

    Args:
        query: Natural language or code query
        top_k: Number of results (default: 10)
        session_id: Filter by session ID (optional)
        min_score: Minimum similarity score (0-1, default: 0.0)

    Returns:
        Formatted search results with scores and metadata
    """
    _, _, _, store = get_components()

    # Build filter if session_id provided
    filter_dict = {"session_id": session_id} if session_id else None

    # Search vector store
    results = store.search(query, top_k=top_k, filter=filter_dict)

    # Filter by minimum score
    results = [r for r in results if r.score >= min_score]

    if not results:
        return "No matching memories found."

    # Format results
    output_lines = [
        f"Found {len(results)} relevant memories:\n",
    ]

    for i, result in enumerate(results, 1):
        session = result.metadata.get("session_id", "unknown")
        ingested_at = result.metadata.get("ingested_at", "unknown")
        output_lines.append(f"\n--- Memory {i} (Score: {result.score:.3f}) ---")
        output_lines.append(f"Session: {session}")
        output_lines.append(f"Ingested: {ingested_at}")
        output_lines.append(f"Content:\n{result.content}")

    return "\n".join(output_lines)


@mcp.tool()
async def memory_stats() -> str:
    """
    Get statistics about stored memories.

    Returns:
        Statistics including total chunks, active collection, and embedder info
    """
    config, _, embedder, store = get_components()

    total_chunks = store.count()
    active_collection = store.active_collection or "none"
    embedder_name = embedder.name
    dimension = embedder.dimension

    return (
        f"📊 Recall Statistics:\n"
        f"Total chunks: {total_chunks}\n"
        f"Active collection: {active_collection}\n"
        f"Embedder: {embedder_name}\n"
        f"Dimension: {dimension}D\n"
        f"Qdrant: {config.qdrant_host}:{config.qdrant_port}"
    )


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
