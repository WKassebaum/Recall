#!/bin/bash
# Backup Qdrant named volume to tarball
# Usage: ./scripts/backup-qdrant.sh [backup_name]

set -e

BACKUP_DIR="$(pwd)/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="${1:-recall-backup-${TIMESTAMP}}"
VOLUME_NAME="recall-qdrant-data"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "🔄 Starting Qdrant backup..."
echo "   Volume: $VOLUME_NAME"
echo "   Destination: $BACKUP_DIR/${BACKUP_NAME}.tar.gz"
echo

# Check if volume exists
if ! docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
    echo "❌ Error: Volume '$VOLUME_NAME' not found"
    echo "   Available volumes:"
    docker volume ls | grep qdrant || echo "   (none)"
    exit 1
fi

# Get volume size
VOLUME_SIZE=$(docker run --rm -v ${VOLUME_NAME}:/data alpine du -sh /data | awk '{print $1}')
echo "📊 Volume size: $VOLUME_SIZE"
echo

# Create backup
echo "⏳ Creating backup (this may take a minute)..."
docker run --rm \
    -v ${VOLUME_NAME}:/data \
    -v ${BACKUP_DIR}:/backup \
    alpine tar czf /backup/${BACKUP_NAME}.tar.gz /data

# Verify backup
if [ -f "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" ]; then
    BACKUP_SIZE=$(ls -lh "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" | awk '{print $5}')
    echo
    echo "✅ Backup complete!"
    echo "   File: $BACKUP_DIR/${BACKUP_NAME}.tar.gz"
    echo "   Size: $BACKUP_SIZE"
    echo

    # List recent backups
    echo "📁 Recent backups:"
    ls -lht "$BACKUP_DIR"/*.tar.gz 2>/dev/null | head -5 || echo "   (this is the first backup)"

    # Cleanup old backups (keep last 7 days)
    OLD_BACKUPS=$(find "$BACKUP_DIR" -name "recall-backup-*.tar.gz" -mtime +7 2>/dev/null)
    if [ -n "$OLD_BACKUPS" ]; then
        echo
        echo "🧹 Cleaning up old backups (>7 days)..."
        echo "$OLD_BACKUPS" | xargs rm -v
    fi
else
    echo "❌ Backup failed!"
    exit 1
fi
