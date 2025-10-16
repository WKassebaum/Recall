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
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from recall.backends.qdrant import QdrantBackend
from recall.chunking.factory import ChunkerFactory
from recall.config.loader import Config, load_config
from recall.core.store import UnifiedVectorStore
from recall.embedders.sentence_transformer import SentenceTransformerEmbedder

# Load .env configuration from ~/.recall/.env
env_file = Path.home() / ".recall" / ".env"
if env_file.exists():
    load_dotenv(env_file)

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

        # Initialize Qdrant backend based on mode
        # Supports both embedded (file) and network (Docker) modes
        qdrant_mode = os.environ.get("RECALL_QDRANT_MODE", "embedded")

        if qdrant_mode == "network":
            # Network mode: Connect to Docker or remote Qdrant
            host = os.environ.get("RECALL_QDRANT_HOST", "localhost")
            port = int(os.environ.get("RECALL_QDRANT_PORT", "6333"))
            backend = QdrantBackend(host=host, port=port)
        else:
            # Embedded mode: Local file storage
            # Support RECALL_QDRANT_PATH for test isolation and custom paths
            qdrant_path = os.environ.get("RECALL_QDRANT_PATH", "~/.recall/qdrant")
            backend = QdrantBackend(path=qdrant_path)

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

    # Get backend mode and location
    backend = store.backend
    assert backend is not None  # Type narrowing
    if backend.mode == "embedded":
        qdrant_info = f"embedded ({backend.path})"
    else:
        qdrant_info = f"{backend.host}:{backend.port}"

    return (
        f"📊 Recall Statistics:\n"
        f"Total chunks: {total_chunks}\n"
        f"Active collection: {active_collection}\n"
        f"Embedder: {embedder_name}\n"
        f"Dimension: {dimension}D\n"
        f"Qdrant: {qdrant_info}"
    )


@mcp.tool()
async def diagnose_installation() -> str:
    """
    Diagnose Recall installation and configuration issues.

    Performs comprehensive health checks on:
    - MCP server configuration in ~/.claude.json
    - Python interpreter and virtual environment
    - Recall package installation
    - Qdrant connectivity (embedded or network mode)
    - Configuration file validity
    - Embedding model availability

    Returns:
        Diagnostic report with check results and fix suggestions
    """
    import json
    from importlib.metadata import version

    checks = []
    issues = []
    warnings_list = []

    # Check 1: MCP server configuration in ~/.claude.json
    checks.append("🔍 Checking MCP server configuration...")
    claude_config = Path.home() / ".claude.json"

    if not claude_config.exists():
        issues.append("❌ ~/.claude.json not found")
        checks.append("   ❌ MCP configuration file missing")
    else:
        try:
            with open(claude_config) as f:
                config_data = json.load(f)

            # Check for plugin:recall:recall namespace
            if "plugin:recall:recall" in config_data.get("mcpServers", {}):
                checks.append("   ✅ MCP server registered (plugin:recall:recall)")

                # Verify configuration
                recall_config = config_data["mcpServers"]["plugin:recall:recall"]
                python_cmd = recall_config.get("command", "")

                # Check if using venv Python
                if ".venv/bin/python" in python_cmd or "venv/bin/python" in python_cmd:
                    checks.append("   ✅ Using virtual environment Python")
                elif python_cmd in ["python", "python3"]:
                    warnings_list.append("⚠️  Using system Python instead of venv")
                    checks.append("   ⚠️  System Python (should use venv)")

                # Check Python path exists
                if Path(python_cmd).exists():
                    checks.append(f"   ✅ Python exists: {python_cmd}")
                else:
                    issues.append(f"❌ Python not found: {python_cmd}")
                    checks.append("   ❌ Python path invalid")

            elif "recall" in config_data.get("mcpServers", {}):
                warnings_list.append(
                    "⚠️  Wrong namespace: 'recall' should be 'plugin:recall:recall'"
                )
                checks.append("   ⚠️  Wrong MCP server namespace")
            else:
                issues.append("❌ Recall MCP server not registered")
                checks.append("   ❌ MCP server not in ~/.claude.json")

        except Exception as e:
            issues.append(f"❌ Error reading ~/.claude.json: {e}")
            checks.append(f"   ❌ Config read error: {e}")

    # Check 2: Python version
    checks.append("\n🔍 Checking Python version...")
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info.major == 3 and sys.version_info.minor >= 10:
        checks.append(f"   ✅ Python {python_version} (compatible)")
    else:
        issues.append(f"❌ Python {python_version} (requires 3.10+)")
        checks.append(f"   ❌ Python {python_version} too old")

    # Check 3: Virtual environment
    checks.append("\n🔍 Checking virtual environment...")
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )
    if in_venv:
        checks.append(f"   ✅ Virtual environment: {sys.prefix}")
    else:
        warnings_list.append("⚠️  Not in virtual environment (recommended)")
        checks.append("   ⚠️  No virtual environment detected")

    # Check 4: Recall package installation
    checks.append("\n🔍 Checking Recall package...")
    try:
        recall_version = version("recall")
        checks.append(f"   ✅ Recall v{recall_version} installed")

        # Verify imports work
        import recall  # noqa: F401

        checks.append("   ✅ Package imports successfully")
    except Exception as e:
        issues.append(f"❌ Recall package error: {e}")
        checks.append("   ❌ Package import failed")

    # Check 5: Qdrant connectivity
    checks.append("\n🔍 Checking Qdrant connectivity...")
    try:
        # Try to get components (this will initialize Qdrant connection)
        config, _, embedder, store = get_components()

        # Test connection by counting
        total_chunks = store.count()
        checks.append(f"   ✅ Qdrant connected: {total_chunks} chunks")

        # Check mode
        backend = store.backend
        assert backend is not None
        if backend.mode == "embedded":
            checks.append(f"   ✅ Mode: embedded ({backend.path})")
        else:
            checks.append(f"   ✅ Mode: network ({backend.host}:{backend.port})")

    except Exception as e:
        issues.append(f"❌ Qdrant connection failed: {e}")
        checks.append("   ❌ Cannot connect to Qdrant")

    # Check 6: Configuration file
    checks.append("\n🔍 Checking configuration files...")
    env_file = Path.home() / ".recall" / ".env"
    if env_file.exists():
        checks.append(f"   ✅ Configuration: {env_file}")
    else:
        warnings_list.append("⚠️  No ~/.recall/.env file (using defaults)")
        checks.append("   ⚠️  No .env configuration")

    # Check 7: Embedding model
    checks.append("\n🔍 Checking embedding model...")
    try:
        config, _, embedder, _ = get_components()
        checks.append(f"   ✅ Model: {embedder.name}")
        checks.append(f"   ✅ Dimension: {embedder.dimension}D")
    except Exception as e:
        issues.append(f"❌ Embedder error: {e}")
        checks.append("   ❌ Model load failed")

    # Build final report
    output = ["🏥 Recall Installation Diagnostics", "=" * 40, ""]
    output.extend(checks)
    output.append("")
    output.append("=" * 40)

    if not issues and not warnings_list:
        output.append("✅ All checks passed!")
        output.append("")
        output.append("Your Recall installation is healthy and ready to use.")
    elif issues:
        output.append(f"❌ {len(issues)} critical issue(s) found:")
        output.append("")
        for issue in issues:
            output.append(f"  {issue}")
        output.append("")
        output.append("📖 See INSTALLATION.md for troubleshooting:")
        output.append(
            "   - Plugin installation: INSTALLATION.md#plugin-installation-troubleshooting"
        )
        output.append("   - Manual setup: INSTALLATION.md#manual-installation")
    elif warnings_list:
        output.append(f"⚠️  {len(warnings_list)} warning(s) found:")
        output.append("")
        for warning in warnings_list:
            output.append(f"  {warning}")
        output.append("")
        output.append("Recall should work but some features may be limited.")

    return "\n".join(output)


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
