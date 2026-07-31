#!/bin/bash
# Automated Qdrant backup with intelligent rotation
# Called by launchd every 6 hours
# Keeps: 4 recent (6hr intervals), 7 daily, 4 weekly
#
# Two backup modes, auto-detected:
#
#   api    - Qdrant snapshot API over HTTP. Works whether Qdrant runs as a
#            native binary, under Docker, or on another host. Snapshots only
#            the collections Recall owns, so a shared instance holding other
#            projects' data does not inflate every backup.
#   docker - legacy path: tar of the named Docker volume. Kept for the
#            docker-compose setup described in DOCKER_RELIABILITY.md.
#
# Override detection with RECALL_BACKUP_MODE=api|docker
#
# Environment:
#   QDRANT_URL                  default http://localhost:6333
#   RECALL_BACKUP_COLLECTIONS   collection name prefix, default "recall"
#   RECALL_QDRANT_VOLUME        docker volume name, default recall-qdrant-data
#   RECALL_BACKUP_DIR           override backup root (useful for test runs)
#
# Restore (api mode) - both routes verified 2026-07-31 against Qdrant 1.17.1.
# Archive members are named <collection>__<snapshot-name>.snapshot, so the
# target collection is the part of the filename before the double underscore.
#
#   tar xzf recall-backup-TIMESTAMP.tar.gz -C /tmp/restore
#   for f in /tmp/restore/*.snapshot; do
#     c="${f##*/}"; c="${c%%__*}"
#     curl -X POST "$QDRANT_URL/collections/$c/snapshots/upload?priority=snapshot" \
#          -H 'Content-Type:multipart/form-data' -F "snapshot=@$f"
#   done
#
# The upload endpoint is not subject to service.max_request_size_mb, so a
# multi-hundred-MB snapshot goes through. If it ever does refuse, stage the
# file inside Qdrant's own snapshots_path and recover from there instead -
# recovery by file:// URL is rejected for any path outside that directory:
#
#   cp "$f" "$SNAPSHOTS_PATH/restore.snapshot"
#   curl -X PUT "$QDRANT_URL/collections/$c/snapshots/recover" \
#        -H 'Content-Type: application/json' \
#        -d "{\"location\": \"file://$SNAPSHOTS_PATH/restore.snapshot\"}"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${RECALL_BACKUP_DIR:-$PROJECT_ROOT/backups/automated}"
RECENT_DIR="$BACKUP_DIR/recent"
DAILY_DIR="$BACKUP_DIR/daily"
WEEKLY_DIR="$BACKUP_DIR/weekly"

QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
COLLECTION_PREFIX="${RECALL_BACKUP_COLLECTIONS:-recall}"
VOLUME_NAME="${RECALL_QDRANT_VOLUME:-recall-qdrant-data}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="recall-backup-${TIMESTAMP}"
ARCHIVE="$RECENT_DIR/${BACKUP_NAME}.tar.gz"

mkdir -p "$RECENT_DIR" "$DAILY_DIR" "$WEEKLY_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "=== Automated Qdrant Backup Started ==="

# --- Mode detection ----------------------------------------------------------

detect_mode() {
    if [ -n "${RECALL_BACKUP_MODE:-}" ]; then
        echo "$RECALL_BACKUP_MODE"
        return
    fi
    if curl -sf --max-time 10 "$QDRANT_URL/collections" >/dev/null 2>&1; then
        echo "api"
        return
    fi
    if command -v docker >/dev/null 2>&1 && docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
        echo "docker"
        return
    fi
    echo "none"
}

MODE="$(detect_mode)"

if [ "$MODE" = "none" ]; then
    log "ERROR: Qdrant not reachable at $QDRANT_URL and no docker volume '$VOLUME_NAME'"
    log "       Set QDRANT_URL, or start Qdrant, or set RECALL_BACKUP_MODE explicitly"
    exit 1
fi

log "Backup mode: $MODE"

# --- api mode ----------------------------------------------------------------

backup_api() {
    local staging collections count snapshot_name
    staging="$(mktemp -d "${TMPDIR:-/tmp}/recall-backup.XXXXXX")"
    trap 'rm -rf "$staging"' RETURN

    collections="$(curl -sf --max-time 30 "$QDRANT_URL/collections" | python3 -c "
import json, sys
prefix = sys.argv[1]
names = [c['name'] for c in json.load(sys.stdin)['result']['collections']]
print('\n'.join(n for n in sorted(names) if n.startswith(prefix)))
" "$COLLECTION_PREFIX")"

    if [ -z "$collections" ]; then
        log "ERROR: no collections matching prefix '$COLLECTION_PREFIX' at $QDRANT_URL"
        return 1
    fi

    count=0
    while IFS= read -r collection; do
        [ -n "$collection" ] || continue
        log "Snapshotting collection: $collection"

        snapshot_name="$(curl -sf --max-time 600 -X POST \
            "$QDRANT_URL/collections/$collection/snapshots" \
            | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['name'])")"

        if [ -z "$snapshot_name" ]; then
            log "ERROR: snapshot creation returned no name for $collection"
            return 1
        fi

        curl -sf --max-time 1800 \
            "$QDRANT_URL/collections/$collection/snapshots/$snapshot_name" \
            -o "$staging/${collection}__${snapshot_name}"

        # Qdrant keeps snapshots on the server until told otherwise; drop it so
        # the storage directory does not grow by a full copy every six hours.
        curl -sf --max-time 60 -X DELETE \
            "$QDRANT_URL/collections/$collection/snapshots/$snapshot_name" >/dev/null

        log "  captured $(du -h "$staging/${collection}__${snapshot_name}" | awk '{print $1}')"
        count=$((count + 1))
    done <<< "$collections"

    log "Archiving $count collection snapshot(s)..."
    tar czf "$ARCHIVE" -C "$staging" .
}

# --- docker mode -------------------------------------------------------------

backup_docker() {
    local volume_size
    if ! docker ps --filter "name=recall-qdrant-6337" --format "{{.Status}}" | grep -q "Up"; then
        log "WARNING: Qdrant container not running - backup may be stale"
    fi

    volume_size=$(docker run --rm -v "${VOLUME_NAME}":/data alpine du -sh /data 2>/dev/null | awk '{print $1}')
    log "Volume size: $volume_size"

    docker run --rm \
        -v "${VOLUME_NAME}":/data \
        -v "${RECENT_DIR}":/backup \
        alpine tar czf "/backup/${BACKUP_NAME}.tar.gz" /data >/dev/null 2>&1
}

case "$MODE" in
    api)    backup_api ;;
    docker) backup_docker ;;
    *)      log "ERROR: unknown mode '$MODE'"; exit 1 ;;
esac

if [ -f "$ARCHIVE" ]; then
    BACKUP_SIZE=$(ls -lh "$ARCHIVE" | awk '{print $5}')
    log "Recent backup created: $BACKUP_SIZE"

    ln -sf "$ARCHIVE" "$BACKUP_DIR/latest-good-backup.tar.gz"
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
    cp "$ARCHIVE" "$DAILY_DIR/$DAILY_NAME"
    log "Daily backup created: $DAILY_NAME"

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
    cp "$ARCHIVE" "$WEEKLY_DIR/$WEEKLY_NAME"
    log "Weekly backup created: $WEEKLY_NAME"

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
