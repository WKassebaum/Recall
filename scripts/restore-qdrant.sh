#!/bin/bash
# Restore Qdrant named volume from tarball backup
# Usage: ./scripts/restore-qdrant.sh <backup_file.tar.gz>

set -e

if [ -z "$1" ]; then
    echo "❌ Error: No backup file specified"
    echo
    echo "Usage: $0 <backup_file.tar.gz>"
    echo
    echo "Available backups:"
    ls -lht backups/*.tar.gz 2>/dev/null | head -10 || echo "  (no backups found in ./backups/)"
    exit 1
fi

BACKUP_FILE="$1"
VOLUME_NAME="recall-qdrant-data"
CONTAINER_NAME="recall-qdrant-6337"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  WARNING: This will REPLACE all data in volume '$VOLUME_NAME'"
echo "   Backup file: $BACKUP_FILE"
echo "   Backup size: $(ls -lh "$BACKUP_FILE" | awk '{print $5}')"
echo
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Restore cancelled"
    exit 0
fi

echo
echo "🔄 Starting restore process..."

# Step 1: Stop Qdrant container
echo "1️⃣  Stopping Qdrant container..."
if docker ps -q --filter "name=$CONTAINER_NAME" | grep -q .; then
    docker-compose down
    echo "   ✅ Container stopped"
else
    echo "   ℹ️  Container not running"
fi

# Step 2: Backup existing volume (safety measure)
if docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
    SAFETY_BACKUP="backups/pre-restore-safety-$(date +%Y%m%d_%H%M%S).tar.gz"
    echo
    echo "2️⃣  Creating safety backup of current volume..."
    echo "   Destination: $SAFETY_BACKUP"
    mkdir -p backups
    docker run --rm \
        -v ${VOLUME_NAME}:/data \
        -v $(pwd)/backups:/backup \
        alpine tar czf /backup/$(basename $SAFETY_BACKUP) /data
    echo "   ✅ Safety backup created"
fi

# Step 3: Remove old volume
echo
echo "3️⃣  Removing old volume..."
if docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
    docker volume rm "$VOLUME_NAME"
    echo "   ✅ Old volume removed"
else
    echo "   ℹ️  No existing volume found"
fi

# Step 4: Create new volume
echo
echo "4️⃣  Creating new volume..."
docker volume create "$VOLUME_NAME"
echo "   ✅ New volume created"

# Step 5: Restore from backup
echo
echo "5️⃣  Restoring from backup (this may take a minute)..."
docker run --rm \
    -v ${VOLUME_NAME}:/data \
    -v $(pwd):/backup \
    alpine tar xzf /backup/$(basename $BACKUP_FILE) -C /

echo "   ✅ Data restored"

# Step 6: Start Qdrant container
echo
echo "6️⃣  Starting Qdrant container..."
docker-compose up -d
sleep 5

# Step 7: Verify restoration
echo
echo "7️⃣  Verifying restoration..."
if docker ps --filter "name=$CONTAINER_NAME" --format "{{.Status}}" | grep -q "Up"; then
    echo "   ✅ Container is running"

    # Check collections
    COLLECTIONS=$(curl -s http://localhost:6337/collections 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data['result']['collections']))" 2>/dev/null || echo "0")

    if [ "$COLLECTIONS" -gt 0 ]; then
        echo "   ✅ Collections found: $COLLECTIONS"
        curl -s http://localhost:6337/collections | python3 -m json.tool | grep -A 2 "collections"
    else
        echo "   ⚠️  No collections found (backup might have been empty)"
    fi

    echo
    echo "✅ Restore complete!"
    echo
    echo "📋 Next steps:"
    echo "   - Test Recall: ./venv/bin/recall stats"
    echo "   - Check health: curl http://localhost:6337/health"
    echo "   - View logs: docker logs recall-qdrant-6337"
else
    echo "   ❌ Container failed to start"
    echo "   Check logs: docker logs recall-qdrant-6337"
    exit 1
fi
