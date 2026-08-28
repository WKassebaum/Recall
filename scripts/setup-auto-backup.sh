#!/bin/bash
# Setup automated Qdrant backups using launchd
# Backups run at 02/08/14/20 wall-clock and auto-rotate

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PLIST_TEMPLATE="$SCRIPT_DIR/com.recall.backup.plist.template"
PLIST_SOURCE="$SCRIPT_DIR/com.recall.backup.plist"   # rendered, gitignored
PLIST_DEST="$HOME/Library/LaunchAgents/com.recall.backup.plist"

echo "🔧 Setting up automated Qdrant backups..."
echo

# Check if launchctl is available (macOS only)
if ! command -v launchctl &> /dev/null; then
    echo "❌ Error: launchctl not found. This script is macOS-only."
    echo "   For Linux, use cron instead (see DOCKER_RELIABILITY.md)"
    exit 1
fi

# Render the plist for this machine. The template carries no absolute paths;
# a rendered plist holds this user's, so it is gitignored and never committed.
if [ ! -f "$PLIST_TEMPLATE" ]; then
    echo "❌ Error: $PLIST_TEMPLATE not found"
    exit 1
fi
sed -e "s#@@PROJECT_ROOT@@#$PROJECT_ROOT#g" -e "s#@@HOME@@#$HOME#g" \
    "$PLIST_TEMPLATE" > "$PLIST_SOURCE"
mkdir -p "$HOME/.recall/backups"

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
    echo "   - 02:00, 08:00, 14:00, 20:00 (wall-clock; the 02:00 run promotes daily/weekly)"
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
    echo "   - Output:  $HOME/.recall/backups/backup-stdout.log"
    echo "   - Errors:  $HOME/.recall/backups/backup-stderr.log"
    echo
    echo "🛠️  Management Commands:"
    echo "   - Check status:  launchctl list | grep recall.backup"
    echo "   - View logs:     tail -f $HOME/.recall/backups/backup-stdout.log"
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
