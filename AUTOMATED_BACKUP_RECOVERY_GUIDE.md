# Automated Backup & Recovery Guide

## Overview

Recall now includes a comprehensive automated backup and recovery system that prevents data loss from Qdrant corruption. This guide shows you how to set up and use it.

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Install Automated Backups

```bash
cd /Users/wrk/WorkDev/MCP-Dev/SemVecMem
./scripts/setup-auto-backup.sh
```

This one-time setup:
- ✅ Installs launchd service (macOS background service)
- ✅ Runs backups every 6 hours automatically
- ✅ Rotates backups intelligently (4 recent, 7 daily, 4 weekly)
- ✅ Maintains latest-good-backup symlink for auto-recovery

### Step 2: Verify Installation

```bash
# Check service is running
launchctl list | grep recall.backup

# View backup logs
tail -f logs/backup-stdout.log

# List backups
ls -lh backups/automated/recent/
```

### Step 3: Test Recovery (Optional)

```bash
# Check health (should pass)
recall recover

# Force recovery test (will restore from backup)
recall recover --force
```

**That's it!** You're now protected against corruption.

---

## 📊 How It Works

### Automatic Backup Schedule

**Every 6 Hours:**
- 12:00 AM
- 6:00 AM
- 12:00 PM
- 6:00 PM

**Plus:**
- On system startup (5 minutes after boot)

### Intelligent Rotation

```
backups/
├── automated/
│   ├── recent/          # Last 4 backups (24 hours)
│   │   ├── recall-backup-20251018_000000.tar.gz
│   │   ├── recall-backup-20251018_060000.tar.gz
│   │   ├── recall-backup-20251018_120000.tar.gz
│   │   └── recall-backup-20251018_180000.tar.gz
│   ├── daily/           # 7 days
│   │   ├── recall-daily-20251012.tar.gz
│   │   ├── recall-daily-20251013.tar.gz
│   │   └── ...
│   └── weekly/          # 4 weeks
│       ├── recall-weekly-20250928.tar.gz
│       ├── recall-weekly-20251005.tar.gz
│       └── ...
└── latest-good-backup.tar.gz → automated/recent/recall-backup-20251018_180000.tar.gz
```

**Auto-cleanup:**
- Old backups automatically deleted
- Keeps optimal balance of recent vs historical backups
- Never exceeds configured retention limits

---

## 🔄 Auto-Recovery System

### When Does Auto-Recovery Trigger?

Recall automatically detects corruption and recovers when:

1. **Qdrant container crashes** (Exit code 101)
2. **Health checks fail** (Connection refused, timeout)
3. **Collection corruption** (WAL errors, bad file descriptor)
4. **Startup health check fails** (MCP server detects issue)

### How to Use Auto-Recovery

**Automatic (Recommended):**
```bash
# Just run this when you suspect corruption
recall recover

# It will:
# 1. Check Docker container status
# 2. Check Qdrant health
# 3. Check collection accessibility
# 4. Auto-recover if any check fails
```

**Manual/Force Recovery:**
```bash
# Force recovery from latest backup (no health checks)
recall recover --force

# Recover from specific backup
recall recover --backup backups/recall-backup-20251018_060000.tar.gz
```

**Example Output:**
```
🔍 Running Recall health diagnostics...

1️⃣  Checking Docker container...
   Status: exited

2️⃣  Checking Qdrant health...
   Healthy: False

3️⃣  Checking collection accessibility...
   Accessible: False

⚠️  Issues detected. Recovery needed.

4️⃣  Finding latest backup...
   Using backup: recall-backup-20251018_180000.tar.gz
   Backup age: 2.3 hours

🔄 Auto-recovery initiated from: recall-backup-20251018_180000.tar.gz
   Stopping Qdrant container...
   Removing corrupted volume...
   Creating new volume...
   Restoring from backup...
   Starting Qdrant container...
   Waiting for Qdrant to start...
✅ Auto-recovery successful!

🎉 Recovery complete! Qdrant is healthy.
```

---

## 🛠️ Management Commands

### Backup Management

```bash
# View service status
launchctl list | grep recall.backup

# View recent backup logs
tail -f logs/backup-stdout.log

# Force immediate backup
./scripts/backup-qdrant-auto.sh

# Manual backup with custom name
./scripts/backup-qdrant.sh my-special-backup

# List all backups
ls -lhR backups/

# Check backup sizes
du -sh backups/*
```

### Service Control

```bash
# Stop automated backups
launchctl unload ~/Library/LaunchAgents/com.recall.backup.plist

# Start automated backups
launchctl load ~/Library/LaunchAgents/com.recall.backup.plist

# Restart service
launchctl unload ~/Library/LaunchAgents/com.recall.backup.plist
launchctl load ~/Library/LaunchAgents/com.recall.backup.plist

# Remove service completely
launchctl unload ~/Library/LaunchAgents/com.recall.backup.plist
rm ~/Library/LaunchAgents/com.recall.backup.plist
```

### Recovery Operations

```bash
# Check health only (no recovery)
recall recover --help

# Interactive recovery (asks for confirmation)
recall recover

# Force recovery (no questions)
recall recover --force

# Recover from specific backup
recall recover --backup backups/automated/daily/recall-daily-20251012.tar.gz

# Test recovery without confirmation (dry run not available - use carefully)
# Always test on dev/staging first
```

---

## 📁 Backup Storage

### Disk Space Usage

**Typical sizes:**
- Empty Qdrant: ~400 bytes
- Small project (100 chunks): ~2-5 MB
- Medium project (1000 chunks): ~20-50 MB
- Large project (10000 chunks): ~200-500 MB

**Total backup storage (with rotation):**
- 4 recent backups
- 7 daily backups
- 4 weekly backups
- **Total: ~15 backups at any time**

**Example calculation:**
- Single backup: 20 MB
- Total stored: 15 × 20 MB = 300 MB

### Location

All backups stored at:
```
/Users/wrk/WorkDev/MCP-Dev/SemVecMem/backups/
```

**Backed up by:**
- ✅ Time Machine (hourly system backups)
- ✅ Automated rotation (15 versions at any time)
- ✅ Named Docker volumes (persistent across container rebuilds)

---

## 🚨 Troubleshooting

### Backups Not Running

**Check service status:**
```bash
launchctl list | grep recall.backup
```

**Expected output:**
```
-   0   com.recall.backup
```

**If not listed:**
```bash
# Reinstall service
./scripts/setup-auto-backup.sh
```

**View error logs:**
```bash
cat logs/backup-stderr.log
```

### Recovery Fails

**Common issues:**

1. **No backups available**
   ```bash
   # Create manual backup first
   ./scripts/backup-qdrant.sh initial-backup

   # Then retry recovery
   recall recover --backup backups/initial-backup.tar.gz
   ```

2. **Docker not running**
   ```bash
   # Start Docker Desktop
   # Then retry
   recall recover
   ```

3. **Permissions error**
   ```bash
   # Fix script permissions
   chmod +x scripts/*.sh

   # Fix launchd plist
   chmod 644 ~/Library/LaunchAgents/com.recall.backup.plist
   ```

### Backup Logs Show Errors

**Check logs:**
```bash
# View recent errors
tail -50 logs/backup-stderr.log

# View full backup log
less logs/backup-stdout.log
```

**Common error solutions:**

- **"Volume not found"** → Qdrant not running: `docker-compose up -d`
- **"Permission denied"** → Scripts not executable: `chmod +x scripts/*.sh`
- **"No space left"** → Clean old backups: `rm backups/automated/recent/*`

---

## 🔧 Advanced Configuration

### Change Backup Frequency

Edit `scripts/com.recall.backup.plist`:

```xml
<!-- Current: Every 6 hours (21600 seconds) -->
<key>StartInterval</key>
<integer>21600</integer>

<!-- Change to every 4 hours (14400 seconds) -->
<key>StartInterval</key>
<integer>14400</integer>

<!-- Change to every 12 hours (43200 seconds) -->
<key>StartInterval</key>
<integer>43200</integer>
```

**Apply changes:**
```bash
launchctl unload ~/Library/LaunchAgents/com.recall.backup.plist
cp scripts/com.recall.backup.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.recall.backup.plist
```

### Change Retention Periods

Edit `scripts/backup-qdrant-auto.sh`:

```bash
# Current retention
RECENT_KEEP=4   # 4 recent backups (24 hours with 6hr frequency)
DAILY_KEEP=7    # 7 daily backups
WEEKLY_KEEP=4   # 4 weekly backups

# Example: Keep more recent backups
RECENT_KEEP=8   # 8 recent backups (48 hours)
DAILY_KEEP=14   # 14 daily backups (2 weeks)
WEEKLY_KEEP=8   # 8 weekly backups (2 months)
```

### Backup to External Drive

**Option 1: Change backup directory**

Edit `scripts/backup-qdrant-auto.sh`:
```bash
# Current
BACKUP_DIR="$PROJECT_ROOT/backups/automated"

# External drive
BACKUP_DIR="/Volumes/ExternalDrive/recall-backups"
```

**Option 2: Symlink backups directory**
```bash
# Move backups to external drive
mv backups /Volumes/ExternalDrive/recall-backups

# Create symlink
ln -s /Volumes/ExternalDrive/recall-backups backups
```

---

## 💡 Best Practices

### 1. Monitor Backup Health Weekly

```bash
# Check backups are running
launchctl list | grep recall.backup

# Check backup count
ls -l backups/automated/recent/ | wc -l
# Should show 4-5 files

# Check latest backup age
ls -lt backups/automated/recent/ | head -2
# Should be less than 6 hours old
```

### 2. Test Recovery Monthly

```bash
# Test on dev/staging first
recall recover --force

# Verify data integrity
recall stats
recall search "test query"
```

### 3. Before Major Operations

```bash
# Create named backup before risky operations
./scripts/backup-qdrant.sh before-major-migration

# Proceed with risky operation
recall migrate ...

# If something goes wrong
recall recover --backup backups/before-major-migration.tar.gz
```

### 4. Multi-Project Strategy

If using Recall for 4 projects:

```bash
# Create project-specific snapshots before big changes
./scripts/backup-qdrant.sh project-quickbooks-stable
./scripts/backup-qdrant.sh project-recall-stable
./scripts/backup-qdrant.sh project-codeindex-stable
./scripts/backup-qdrant.sh project-other-stable

# Keep these long-term (don't auto-delete)
mv backups/project-*.tar.gz backups/project-snapshots/
```

---

## 📊 Monitoring & Metrics

### Backup Statistics

```bash
# Total backup storage
du -sh backups/

# Breakdown by type
du -sh backups/automated/*/

# Count backups
find backups/ -name "*.tar.gz" | wc -l

# Largest backup
ls -lhS backups/automated/*/*.tar.gz | head -1

# Oldest backup
ls -lht backups/automated/*/*.tar.gz | tail -1
```

### Success Rate

```bash
# View last 10 backup runs
tail -100 logs/backup-stdout.log | grep "Complete"

# Count failures in last week
grep -c "ERROR" logs/backup-stderr.log
```

---

## 🎯 Summary

**What you get:**
- ✅ Automated backups every 6 hours
- ✅ Intelligent rotation (15 backups total)
- ✅ One-command recovery from corruption
- ✅ Zero manual intervention required
- ✅ Multi-project support (4 projects safe)

**What it prevents:**
- ❌ Data loss from Qdrant crashes
- ❌ Corruption from macOS Docker issues
- ❌ Lost work from WAL errors
- ❌ Hours of re-ingesting memories

**Total setup time:** 5 minutes
**Maintenance required:** None (fully automated)
**Recovery time:** 2-3 minutes (automated)

---

**Version:** v1.4.0
**Last Updated:** 2025-10-18
**Status:** Production-ready
