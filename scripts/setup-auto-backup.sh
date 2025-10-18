#!/bin/bash
# Setup automated Qdrant backups using launchd
# Backups run every 6 hours and auto-rotate

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PLIST_SOURCE="$SCRIPT_DIR/com.recall.backup.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.recall.backup.plist"

echo "🔧 Setting up automated Qdrant backups..."
echo

# Check if launchctl is available (macOS only)
if ! command -v launchctl &> /dev/null; then
    echo "❌ Error: launchctl not found. This script is macOS-only."
    echo "   For Linux, use cron instead (see DOCKER_RELIABILITY.md)"
    exit 1
fi

# Check if plist source exists
if [ ! -f "$PLIST_SOURCE" ]; then
    echo "❌ Error: $PLIST_SOURCE not found"
    exit 1
fi

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$HOME/Library/LaunchAgents"

# Unload existing service if running
if launchctl list | grep -q "com.recall.backup"; then
    echo "📋 Stopping existing backup service..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# Copy plist to LaunchAgents
echo "📝 Installing launch agent..."
cp "$PLIST_SOURCE" "$PLIST_DEST"

# Load the service
echo "🚀 Starting backup service..."
launchctl load "$PLIST_DEST"

# Verify it's loaded
if launchctl list | grep -q "com.recall.backup"; then
    echo
    echo "✅ Automated backups installed successfully!"
    echo
    echo "📊 Backup Schedule:"
    echo "   - Every 6 hours (automatically)"
    echo "   - On system startup (5 minutes after boot)"
    echo "   - Keeps: 4 recent (24hrs), 7 daily, 4 weekly"
    echo
    echo "📁 Backup Locations:"
    echo "   - Recent:  $PROJECT_ROOT/backups/automated/recent/"
    echo "   - Daily:   $PROJECT_ROOT/backups/automated/daily/"
    echo "   - Weekly:  $PROJECT_ROOT/backups/automated/weekly/"
    echo "   - Latest:  $PROJECT_ROOT/backups/latest-good-backup.tar.gz (symlink)"
    echo
    echo "📋 Logs:"
    echo "   - Output:  $PROJECT_ROOT/logs/backup-stdout.log"
    echo "   - Errors:  $PROJECT_ROOT/logs/backup-stderr.log"
    echo
    echo "🛠️  Management Commands:"
    echo "   - Check status:  launchctl list | grep recall.backup"
    echo "   - View logs:     tail -f $PROJECT_ROOT/logs/backup-stdout.log"
    echo "   - Stop service:  launchctl unload $PLIST_DEST"
    echo "   - Start service: launchctl load $PLIST_DEST"
    echo "   - Force backup:  ./scripts/backup-qdrant-auto.sh"
    echo
    echo "🔄 Auto-Recovery:"
    echo "   If Qdrant corrupts, Recall will auto-recover from latest backup:"
    echo "   - recall recover              # Check health + auto-recover"
    echo "   - recall recover --force      # Force recovery now"
    echo
else
    echo "❌ Failed to load backup service"
    echo "   Check: launchctl list | grep recall"
    exit 1
fi
