#!/bin/bash
# Migrate from bind mount to named volumes
# Preserves all existing data

set -e

echo "🔄 Recall Migration: Bind Mount → Named Volumes"
echo "================================================"
echo

# Configuration
VOLUME_NAME="recall-qdrant-data"
CONTAINER_NAME="recall-qdrant-6337"
BIND_MOUNT_PATH="${BIND_MOUNT_PATH:-$HOME/.recall/docker-6337}"

# Detect current setup
echo "🔍 Detecting current configuration..."
echo

# Check if container exists
if docker ps -a --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "$CONTAINER_NAME"; then
    echo "   ✅ Found existing container: $CONTAINER_NAME"
    HAS_CONTAINER=true
else
    echo "   ℹ️  No existing container found"
    HAS_CONTAINER=false
fi

# Check if bind mount directory exists
if [ -d "$BIND_MOUNT_PATH" ]; then
    BIND_SIZE=$(du -sh "$BIND_MOUNT_PATH" | awk '{print $1}')
    echo "   ✅ Found bind mount data: $BIND_MOUNT_PATH ($BIND_SIZE)"
    HAS_BIND_DATA=true
else
    echo "   ℹ️  No bind mount data found at $BIND_MOUNT_PATH"
    HAS_BIND_DATA=false
fi

# Check if named volume already exists
if docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
    echo "   ⚠️  Named volume already exists: $VOLUME_NAME"
    HAS_NAMED_VOLUME=true
else
    echo "   ℹ️  Named volume doesn't exist yet"
    HAS_NAMED_VOLUME=false
fi

echo

# Determine migration path
if [ "$HAS_BIND_DATA" = false ]; then
    echo "✅ No migration needed - no existing data found"
    echo
    echo "Next steps:"
    echo "  1. Run: docker-compose up -d"
    echo "  2. Recall will use named volumes automatically"
    exit 0
fi

if [ "$HAS_NAMED_VOLUME" = true ]; then
    echo "⚠️  WARNING: Named volume already exists!"
    echo
    echo "This suggests migration was already done, or you're using both."
    echo "Proceeding will OVERWRITE the named volume with bind mount data."
    echo
    read -p "Continue? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Migration cancelled."
        exit 0
    fi
fi

# Migration required
echo "📦 Migration Required"
echo "   From: $BIND_MOUNT_PATH"
echo "   To: Docker named volume '$VOLUME_NAME'"
echo "   Data size: $BIND_SIZE"
echo
echo "⚠️  This will:"
echo "   1. Stop your current Qdrant container (if running)"
echo "   2. Create named volume"
echo "   3. Copy all data from bind mount to named volume"
echo "   4. Start container with named volumes"
echo "   5. Keep original bind mount data as backup"
echo
read -p "Proceed with migration? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Migration cancelled."
    exit 0
fi

echo
echo "🚀 Starting migration..."
echo

# Step 1: Stop container
if [ "$HAS_CONTAINER" = true ]; then
    echo "1️⃣  Stopping current container..."
    docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
    docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
    echo "   ✅ Container stopped and removed"
fi

# Step 2: Create named volume
echo
echo "2️⃣  Creating named volume..."
if [ "$HAS_NAMED_VOLUME" = true ]; then
    docker volume rm "$VOLUME_NAME" >/dev/null 2>&1
fi
docker volume create "$VOLUME_NAME" >/dev/null
echo "   ✅ Named volume created: $VOLUME_NAME"

# Step 3: Copy data from bind mount to named volume
echo
echo "3️⃣  Copying data (this may take a minute)..."
docker run --rm \
    -v "$BIND_MOUNT_PATH:/source:ro" \
    -v "$VOLUME_NAME:/dest" \
    alpine sh -c "cp -a /source/. /dest/ && echo '   ✅ Data copied successfully'"

# Verify data
COPIED_SIZE=$(docker run --rm -v "$VOLUME_NAME:/data" alpine du -sh /data | awk '{print $1}')
echo "   📊 Migrated data size: $COPIED_SIZE"

# Step 4: Start container with docker-compose
echo
echo "4️⃣  Starting container with named volumes..."
if [ -f "docker-compose.yml" ]; then
    docker-compose up -d >/dev/null
    echo "   ✅ Container started with docker-compose"
else
    # Fallback: start container manually
    docker run -d \
        --name "$CONTAINER_NAME" \
        -p 6337:6333 \
        -v "$VOLUME_NAME:/qdrant/storage" \
        --restart unless-stopped \
        qdrant/qdrant:latest >/dev/null
    echo "   ✅ Container started manually"
fi

# Wait for startup
echo
echo "5️⃣  Waiting for Qdrant to start..."
sleep 5

# Verify health
if curl -s http://localhost:6337/health >/dev/null 2>&1 || curl -s http://localhost:6337/collections >/dev/null 2>&1; then
    echo "   ✅ Qdrant is healthy"
else
    echo "   ⚠️  Health check inconclusive (may still be starting)"
fi

# Step 5: Verify migration
echo
echo "6️⃣  Verifying migration..."
COLLECTIONS=$(curl -s http://localhost:6337/collections 2>/dev/null | grep -o '"collections":\[.*\]' || echo "")
if [ -n "$COLLECTIONS" ]; then
    echo "   ✅ Collections accessible"
else
    echo "   ℹ️  No collections yet (expected if database was empty)"
fi

# Done
echo
echo "✅ Migration Complete!"
echo
echo "📊 Summary:"
echo "   - Original data preserved at: $BIND_MOUNT_PATH"
echo "   - New named volume: $VOLUME_NAME"
echo "   - Container: $CONTAINER_NAME (running)"
echo "   - Data size: $COPIED_SIZE"
echo
echo "🔍 Next Steps:"
echo "   1. Test Recall: recall stats"
echo "   2. Verify data: recall search 'test query'"
echo "   3. If all works, you can delete bind mount:"
echo "      rm -rf $BIND_MOUNT_PATH"
echo
echo "📁 Backup Safety:"
echo "   - Original bind mount NOT deleted (safe to remove manually later)"
echo "   - Create backup before deleting:"
echo "      tar czf recall-bind-mount-backup.tar.gz $BIND_MOUNT_PATH"
echo
