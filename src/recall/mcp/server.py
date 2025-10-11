# Copyright 2025 William Kassebaum
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
        # Load configuration - use absolute path or fallback to relative
        import pathlib

        config_path = os.environ.get(
            "RECALL_CONFIG",
            str(pathlib.Path(__file__).parent.parent.parent.parent / "config.yaml"),
        )
        _config = load_config(config_path)

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
        dict[str, str] | None,
        Field(
            description='Optional metadata. RECOMMENDED: {"event_type": "decision|discovery|milestone|preference|error|success", "tags": "topic1,topic2", "context": "why created", "outcome": "what happened"}'
        ),
    ] = None,
) -> str:
    """
    Ingest content into semantic vector memory with optional event metadata.

    Automatically chunks content, generates embeddings, and stores with metadata
    for both semantic and temporal retrieval.

    RECOMMENDED METADATA STRUCTURE:
      event_type: "decision" | "discovery" | "milestone" | "preference" | "error" | "success"
      tags: "topic1,topic2,topic3"
      context: "Why this memory was created"
      outcome: "What happened or was decided"

    EXAMPLE - Decision Event:
      metadata = {
        "event_type": "decision",
        "tags": "architecture,embeddings",
        "context": "Comparing 4 embedding models",
        "outcome": "Selected Arctic for 93.3% accuracy"
      }

    Args:
        content: Content to store (code, text, JSON, markdown)
        session_id: Session ID for organizing and filtering memories
        content_type: Optional type hint (auto-detected if not provided)
        metadata: Optional metadata (event_type, tags, context, outcome, etc.)

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
    event_type = meta.get("event_type", "memory")
    return (
        f"✅ Ingested {len(chunks)} chunks from session '{session_id}'\n"
        f"Event type: {event_type}\n"
        f"Content type: {content_type or 'auto-detected'}\n"
        f"Total characters: {len(content)}\n"
        f"Average chunk size: {len(content) // len(chunks) if chunks else 0} chars"
    )


@mcp.tool()
async def recall_memory(
    query: Annotated[
        str | None,
        Field(
            description="Semantic search query (required for semantic/hybrid, optional for chronological)"
        ),
    ] = None,
    top_k: Annotated[int, Field(description="Maximum number of results to return")] = 10,
    session_id: Annotated[
        str | None, Field(description="Optional session ID to filter results")
    ] = None,
    min_score: Annotated[
        float, Field(description="Minimum similarity score threshold (0-1)")
    ] = 0.0,
    retrieval_mode: Annotated[
        str,
        Field(description='Retrieval mode: "semantic" (default), "chronological", or "hybrid"'),
    ] = "semantic",
    time_range: Annotated[
        str | None,
        Field(
            description='Time range filter: "2025-10-01,2025-10-11" or "2025-10-10," (open-ended)'
        ),
    ] = None,
    event_types: Annotated[
        str | None,
        Field(description='Event type filter: "decision,milestone" (comma-separated)'),
    ] = None,
    sort_by: Annotated[str, Field(description='Sort order: "score" (default) or "time"')] = "score",
) -> str:
    """
    Search memory using semantic similarity OR temporal queries.

    SEMANTIC MODE (default):
      - Search by meaning: "What decisions about embedders?"
      - Returns results ranked by similarity score
      - Requires query parameter

    CHRONOLOGICAL MODE:
      - Search by time: Show Phase 3 timeline
      - Returns results in time order (oldest to newest)
      - Query parameter optional (filters if provided)
      - Use with time_range and/or session_id

    HYBRID MODE:
      - Combines semantic relevance + temporal filtering
      - Use for: "Recent debugging attempts"
      - Supports all filtering options

    EXAMPLES:

    Semantic: recall_memory(query="embedding decisions")

    Chronological: recall_memory(
        retrieval_mode="chronological",
        session_id="phase3",
        time_range="2025-10-08,2025-10-11"
    )

    Hybrid: recall_memory(
        query="debugging",
        retrieval_mode="hybrid",
        time_range="2025-10-10,",
        event_types="discovery,error"
    )

    Args:
        query: Semantic search query (optional for chronological mode)
        top_k: Number of results (default: 10)
        session_id: Filter by session ID
        min_score: Minimum similarity score (0-1)
        retrieval_mode: "semantic", "chronological", or "hybrid"
        time_range: "start,end" or "start," (open-ended)
        event_types: "type1,type2" (comma-separated)
        sort_by: "score" or "time"

    Returns:
        Formatted search results with scores and metadata
    """
    _, _, _, store = get_components()

    # Build filter if session_id provided
    filter_dict = {"session_id": session_id} if session_id else None

    # Parse time_range if provided
    time_range_tuple = None
    if time_range:
        parts = time_range.split(",")
        start = parts[0] if parts[0] else None
        end = parts[1] if len(parts) > 1 and parts[1] else None
        if start:
            time_range_tuple = (start, end)

    # Parse event_types if provided
    event_types_list = None
    if event_types:
        event_types_list = [t.strip() for t in event_types.split(",")]

    # Search vector store with new parameters
    results = store.search(
        query=query,
        top_k=top_k,
        filter=filter_dict,
        retrieval_mode=retrieval_mode,
        time_range=time_range_tuple,
        event_types=event_types_list,
        sort_by=sort_by,
    )

    # Filter by minimum score (for semantic/hybrid modes)
    if retrieval_mode != "chronological":
        results = [r for r in results if r.score >= min_score]

    if not results:
        return "No matching memories found."

    # Format results
    mode_label = retrieval_mode.upper()
    output_lines = [
        f"Found {len(results)} relevant memories ({mode_label} mode):\n",
    ]

    for i, result in enumerate(results, 1):
        session = result.metadata.get("session_id", "unknown")
        ingested_at = result.metadata.get("ingested_at", "unknown")
        event_type = result.metadata.get("event_type", "memory")

        # Show score for semantic/hybrid, hide for chronological
        if retrieval_mode == "chronological":
            output_lines.append(f"\n--- Memory {i} [{event_type}] ---")
        else:
            output_lines.append(f"\n--- Memory {i} (Score: {result.score:.3f}) [{event_type}] ---")

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
