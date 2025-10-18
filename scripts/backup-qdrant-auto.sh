#!/bin/bash
# Automated Qdrant backup with intelligent rotation
# Called by launchd every 6 hours
# Keeps: 4 recent (6hr intervals), 7 daily, 4 weekly

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups/automated"
RECENT_DIR="$BACKUP_DIR/recent"
DAILY_DIR="$BACKUP_DIR/daily"
WEEKLY_DIR="$BACKUP_DIR/weekly"
VOLUME_NAME="recall-qdrant-data"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="recall-backup-${TIMESTAMP}"

# Create backup directories
mkdir -p "$RECENT_DIR" "$DAILY_DIR" "$WEEKLY_DIR"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "=== Automated Qdrant Backup Started ==="

# Check if volume exists
if ! docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
    log "ERROR: Volume '$VOLUME_NAME' not found"
    exit 1
fi

# Check if container is running
if ! docker ps --filter "name=recall-qdrant-6337" --format "{{.Status}}" | grep -q "Up"; then
    log "WARNING: Qdrant container not running - backup may be stale"
fi

# Get volume size
VOLUME_SIZE=$(docker run --rm -v ${VOLUME_NAME}:/data alpine du -sh /data 2>/dev/null | awk '{print $1}')
log "Volume size: $VOLUME_SIZE"

# Create recent backup
log "Creating recent backup..."
docker run --rm \
    -v ${VOLUME_NAME}:/data \
    -v ${RECENT_DIR}:/backup \
    alpine tar czf /backup/${BACKUP_NAME}.tar.gz /data >/dev/null 2>&1

if [ -f "$RECENT_DIR/${BACKUP_NAME}.tar.gz" ]; then
    BACKUP_SIZE=$(ls -lh "$RECENT_DIR/${BACKUP_NAME}.tar.gz" | awk '{print $5}')
    log "Recent backup created: $BACKUP_SIZE"

    # Create symlink to latest backup (for auto-recovery)
    ln -sf "$RECENT_DIR/${BACKUP_NAME}.tar.gz" "$BACKUP_DIR/latest-good-backup.tar.gz"
    log "Updated latest-good-backup symlink"
else
    log "ERROR: Backup creation failed"
    exit 1
fi

# Rotate recent backups (keep last 4 = 24 hours of 6hr intervals)
log "Rotating recent backups (keeping last 4)..."
RECENT_COUNT=$(ls -1 "$RECENT_DIR"/*.tar.gz 2>/dev/null | wc -l)
if [ "$RECENT_COUNT" -gt 4 ]; then
    ls -1t "$RECENT_DIR"/*.tar.gz | tail -n +5 | xargs rm -f
    log "Removed $((RECENT_COUNT - 4)) old recent backup(s)"
fi

# Daily backup (at 2 AM, keep 7 days)
HOUR=$(date +%H)
if [ "$HOUR" = "02" ]; then
    log "Creating daily backup..."
    DAILY_NAME="recall-daily-$(date +%Y%m%d).tar.gz"
    cp "$RECENT_DIR/${BACKUP_NAME}.tar.gz" "$DAILY_DIR/$DAILY_NAME"
    log "Daily backup created: $DAILY_NAME"

    # Rotate daily backups (keep 7)
    DAILY_COUNT=$(ls -1 "$DAILY_DIR"/*.tar.gz 2>/dev/null | wc -l)
    if [ "$DAILY_COUNT" -gt 7 ]; then
        ls -1t "$DAILY_DIR"/*.tar.gz | tail -n +8 | xargs rm -f
        log "Removed $((DAILY_COUNT - 7)) old daily backup(s)"
    fi
fi

# Weekly backup (Sunday at 2 AM, keep 4 weeks)
DAY_OF_WEEK=$(date +%u)
if [ "$DAY_OF_WEEK" = "7" ] && [ "$HOUR" = "02" ]; then
    log "Creating weekly backup..."
    WEEKLY_NAME="recall-weekly-$(date +%Y%m%d).tar.gz"
    cp "$RECENT_DIR/${BACKUP_NAME}.tar.gz" "$WEEKLY_DIR/$WEEKLY_NAME"
    log "Weekly backup created: $WEEKLY_NAME"

    # Rotate weekly backups (keep 4)
    WEEKLY_COUNT=$(ls -1 "$WEEKLY_DIR"/*.tar.gz 2>/dev/null | wc -l)
    if [ "$WEEKLY_COUNT" -gt 4 ]; then
        ls -1t "$WEEKLY_DIR"/*.tar.gz | tail -n +5 | xargs rm -f
        log "Removed $((WEEKLY_COUNT - 4)) old weekly backup(s)"
    fi
fi

# Summary
log "=== Backup Summary ==="
log "Recent backups: $(ls -1 "$RECENT_DIR"/*.tar.gz 2>/dev/null | wc -l)"
log "Daily backups: $(ls -1 "$DAILY_DIR"/*.tar.gz 2>/dev/null | wc -l)"
log "Weekly backups: $(ls -1 "$WEEKLY_DIR"/*.tar.gz 2>/dev/null | wc -l)"
log "Total backup size: $(du -sh "$BACKUP_DIR" | awk '{print $1}')"
log "=== Automated Backup Complete ==="
