"""Schema migration: unnamed vectors → named vectors + sparse.

Migrates existing Qdrant collections from the legacy unnamed-vector schema
to named vectors with sparse vector support for hybrid search.
"""

import os
import time
from typing import Any

import click

from recall.backends.qdrant import QdrantBackend
from recall.config.loader import load_config
from recall.sparse.encoder import SparseEncoder


@click.command()
@click.option(
    "--collection",
    "-c",
    default=None,
    help="Collection to migrate (default: auto-detect recall_* collections)",
)
@click.option(
    "--batch-size",
    "-b",
    type=int,
    default=100,
    help="Points to process per batch",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Check schema without migrating",
)
def migrate_schema(collection: str | None, batch_size: int, dry_run: bool) -> None:
    """Migrate collection schema from unnamed to named vectors + sparse.

    This is required before hybrid keyword+semantic search can be used.
    Existing data is preserved — dense vectors are copied as-is and
    sparse vectors are computed from chunk content during migration.

    NOTE: Stop the Recall MCP server before running this command
    (embedded Qdrant uses exclusive file locks).

    Examples:
        recall migrate-schema --dry-run
        recall migrate-schema
        recall migrate-schema -c recall_768d
    """
    click.echo("🔄 Schema Migration: unnamed → named vectors + sparse\n")

    config = load_config("config.yaml")

    # Initialize backend
    qdrant_mode = os.environ.get("RECALL_QDRANT_MODE", "embedded")
    if qdrant_mode == "network":
        host = os.environ.get("RECALL_QDRANT_HOST", config.qdrant_host)
        port = int(os.environ.get("RECALL_QDRANT_PORT", str(config.qdrant_port)))
        backend = QdrantBackend(host=host, port=port)
    else:
        qdrant_path = os.environ.get("RECALL_QDRANT_PATH", "~/.recall/qdrant")
        backend = QdrantBackend(path=qdrant_path)

    # Find collections to migrate
    if collection:
        collections_to_check = [collection]
    else:
        all_collections = backend.client.get_collections().collections
        collections_to_check = [c.name for c in all_collections if c.name.startswith("recall_")]

    if not collections_to_check:
        click.echo("No recall_* collections found.")
        return

    sparse_encoder = SparseEncoder()
    migrated_count = 0

    for coll_name in collections_to_check:
        click.echo(f"📋 Checking {coll_name}...")

        # Check if migration is needed
        if not backend._detect_legacy(coll_name):
            click.echo("   ✅ Already using named vectors — skipping\n")
            continue

        # Get collection info
        info = backend.client.get_collection(collection_name=coll_name)
        point_count = info.points_count or 0
        dimension = info.config.params.vectors.size  # type: ignore[union-attr]

        click.echo("   Schema: unnamed vectors (legacy)")
        click.echo(f"   Points: {point_count}")
        click.echo(f"   Dimension: {dimension}D")

        if dry_run:
            click.echo("   🏁 Dry run — migration needed\n")
            continue

        if point_count == 0:
            click.echo("   ⚠️  Empty collection — recreating with new schema...")
            backend.client.delete_collection(collection_name=coll_name)
            backend.ensure_collection(coll_name, dimension, sparse=True)
            click.echo("   ✅ Recreated with named vectors + sparse\n")
            migrated_count += 1
            continue

        # Migrate non-empty collection
        click.echo(f"   🚀 Migrating {point_count} points...")
        start_time = time.time()

        # Phase 1: Scroll all points from old collection
        all_points = []
        next_offset = None
        while True:
            points, next_offset = backend.client.scroll(
                collection_name=coll_name,
                limit=batch_size,
                offset=next_offset,
                with_vectors=True,
                with_payload=True,
            )
            all_points.extend(points)
            if next_offset is None:
                break

        click.echo(f"   📦 Read {len(all_points)} points")

        # Phase 2: Delete old collection and recreate with new schema
        backend.client.delete_collection(collection_name=coll_name)
        backend.ensure_collection(coll_name, dimension, sparse=True)
        click.echo("   🔧 Recreated collection with named vectors + sparse")

        # Phase 3: Re-upsert with named vectors + computed sparse
        from qdrant_client.models import PointStruct

        migrated = 0
        failed = 0

        for i in range(0, len(all_points), batch_size):
            batch = all_points[i : i + batch_size]
            new_points = []

            for point in batch:
                try:
                    # Extract dense vector (was unnamed list)
                    raw_vector: Any = point.vector
                    if isinstance(raw_vector, dict):
                        dense_vector: Any = raw_vector.get("dense", list(raw_vector.values())[0])
                    else:
                        dense_vector = raw_vector

                    # Compute sparse vector from content
                    content = point.payload.get("content", "")  # type: ignore[union-attr]
                    sparse_vector = sparse_encoder.encode(content) if content else None

                    # Build new point with named vectors
                    vector: dict[str, Any] = {"dense": dense_vector}
                    if sparse_vector and sparse_vector.indices:
                        vector["sparse"] = sparse_vector

                    new_points.append(
                        PointStruct(
                            id=point.id,
                            vector=vector,
                            payload=point.payload,
                        )
                    )
                    migrated += 1
                except Exception as e:
                    failed += 1
                    click.echo(f"   ⚠️  Failed point {point.id}: {e}")

            if new_points:
                backend.client.upsert(collection_name=coll_name, points=new_points)

            progress = (i + len(batch)) / len(all_points) * 100
            click.echo(f"   Progress: {progress:.0f}% ({migrated} migrated, {failed} failed)")

        duration = time.time() - start_time
        click.echo(
            f"   ✅ Migration complete: {migrated}/{len(all_points)} points ({duration:.1f}s)\n"
        )
        migrated_count += 1

    if dry_run:
        click.echo(f"🏁 Dry run complete — {len(collections_to_check)} collection(s) checked")
    else:
        click.echo(f"✅ Schema migration complete — {migrated_count} collection(s) migrated")
