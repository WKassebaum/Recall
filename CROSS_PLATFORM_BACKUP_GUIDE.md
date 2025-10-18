# Cross-Platform Backup & Recovery Guide

## Platform Comparison

### Current Implementation (macOS)

**Technology:** launchd (native macOS service manager)
**Effort:** ✅ Complete (5 minutes setup)
**Reliability:** Excellent (OS-managed)

---

## Linux Implementation

### ✅ RECOMMENDED: Use Cron (Simple)

**Advantages:**
- ✅ All scripts work as-is (bash-based)
- ✅ Same Docker commands
- ✅ Native to all Linux distros
- ✅ Reliable and well-tested

**Setup Time:** 5-10 minutes

### Implementation

**Step 1: Install Service**

```bash
# The scripts work on Linux without modification
cd /path/to/SemVecMem
chmod +x scripts/*.sh

# Test manual backup first
./scripts/backup-qdrant-auto.sh
```

**Step 2: Create Cron Job**

```bash
# Edit crontab
crontab -e

# Add these lines:
# Automated backup every 6 hours
0 */6 * * * cd /path/to/SemVecMem && ./scripts/backup-qdrant-auto.sh >> logs/backup-stdout.log 2>> logs/backup-stderr.log

# Alternative: Run at specific times (matches macOS schedule)
0 0,6,12,18 * * * cd /path/to/SemVecMem && ./scripts/backup-qdrant-auto.sh >> logs/backup-stdout.log 2>> logs/backup-stderr.log
```

**Step 3: Verify Cron Installation**

```bash
# List cron jobs
crontab -l

# Check logs after first run
tail -f /path/to/SemVecMem/logs/backup-stdout.log
```

### Differences from macOS

| Feature | macOS (launchd) | Linux (cron) |
|---------|-----------------|--------------|
| Setup script | `setup-auto-backup.sh` | Manual crontab edit |
| Service management | `launchctl` | `crontab -e` |
| Logs | Automatic to logs/ | Redirect in crontab |
| Run at startup | ✅ Yes (RunAtLoad) | ❌ No (use @reboot) |
| Nice priority | ✅ Yes (built-in) | Add `nice -n 10` |

### Linux-Specific Enhancements

**Run at startup (optional):**
```bash
# Add to crontab
@reboot sleep 300 && cd /path/to/SemVecMem && ./scripts/backup-qdrant-auto.sh >> logs/backup-stdout.log 2>> logs/backup-stderr.log
```

**Lower priority (optional):**
```bash
# Use nice to avoid interfering with work
0 */6 * * * nice -n 10 cd /path/to/SemVecMem && ./scripts/backup-qdrant-auto.sh >> logs/backup-stdout.log 2>> logs/backup-stderr.log
```

### Systemd Alternative (Advanced)

For systemd-based Linux (Ubuntu 16.04+, Debian 8+, CentOS 7+):

**Create service file:**

```bash
sudo nano /etc/systemd/system/recall-backup.service
```

```ini
[Unit]
Description=Recall Qdrant Automated Backup
After=docker.service

[Service]
Type=oneshot
User=your-username
WorkingDirectory=/path/to/SemVecMem
ExecStart=/path/to/SemVecMem/scripts/backup-qdrant-auto.sh
StandardOutput=append:/path/to/SemVecMem/logs/backup-stdout.log
StandardError=append:/path/to/SemVecMem/logs/backup-stderr.log
Nice=10
```

**Create timer file:**

```bash
sudo nano /etc/systemd/system/recall-backup.timer
```

```ini
[Unit]
Description=Recall Qdrant Backup Timer
Requires=recall-backup.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=6h
Persistent=true

[Install]
WantedBy=timers.target
```

**Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable recall-backup.timer
sudo systemctl start recall-backup.timer

# Check status
systemctl status recall-backup.timer
systemctl list-timers
```

---

## Windows Implementation

### ⚠️ MORE COMPLEX: Use Task Scheduler

**Challenges:**
- ❌ Bash scripts need conversion to PowerShell
- ❌ Different path formats
- ⚠️ Docker Desktop on Windows has volume issues similar to macOS
- ⚠️ Task Scheduler less reliable than launchd/cron

**Effort Estimate:** 2-3 hours (script conversion + testing)

**My Opinion:** Windows support requires significant additional work. Recommend:
1. If users are on Windows: Use WSL2 (Windows Subsystem for Linux) + Linux approach
2. If native Windows required: Create PowerShell version

### Option 1: WSL2 + Linux Approach (RECOMMENDED)

**Advantages:**
- ✅ Use Linux scripts as-is
- ✅ Better Docker integration
- ✅ More reliable

**Setup:**

```powershell
# Install WSL2
wsl --install

# Inside WSL2, follow Linux instructions above
wsl
cd /mnt/c/Users/YourName/path/to/SemVecMem
./scripts/setup-auto-backup.sh  # Use cron approach
```

### Option 2: Native Windows PowerShell (Advanced)

**Would require creating:**

1. **PowerShell backup script** (`scripts/backup-qdrant-auto.ps1`)
2. **Task Scheduler XML** for scheduling
3. **Setup script** (`scripts/setup-auto-backup.ps1`)

**Example PowerShell Script (Partial):**

```powershell
# backup-qdrant-auto.ps1
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackupDir = Join-Path $ProjectRoot "backups\automated"
$RecentDir = Join-Path $BackupDir "recent"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$VolumeName = "recall-qdrant-data"

# Create directories
New-Item -ItemType Directory -Force -Path $RecentDir | Out-Null

Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] === Automated Qdrant Backup Started ==="

# Create backup using Docker
docker run --rm `
  -v ${VolumeName}:/data `
  -v ${RecentDir}:/backup `
  alpine tar czf /backup/recall-backup-${Timestamp}.tar.gz /data

# Rotation logic (similar to bash version)
# ...
```

**Task Scheduler Setup:**

```powershell
# Create scheduled task
$Action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"C:\path\to\SemVecMem\scripts\backup-qdrant-auto.ps1`""

$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 6)

$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "RecallBackup" `
  -Action $Action `
  -Trigger $Trigger `
  -Settings $Settings `
  -Description "Automated Recall Qdrant Backup"
```

**My Opinion on Windows Native:**
- **Effort:** High (2-3 hours of PowerShell development)
- **Maintenance:** Higher (two codebases)
- **Reliability:** Lower than launchd/cron
- **Recommendation:** Only if WSL2 is not an option

---

## Platform Recommendations

### Summary Table

| Platform | Solution | Effort | Reliability | Recommendation |
|----------|----------|--------|-------------|----------------|
| **macOS** | launchd | ✅ 5 min | Excellent | ✅ Use as-is (done) |
| **Linux** | cron | ✅ 10 min | Excellent | ✅ Recommended |
| **Linux (systemd)** | systemd timer | 30 min | Excellent | ⭐ Best for servers |
| **Windows (WSL2)** | WSL2 + cron | ✅ 15 min | Very Good | ✅ Recommended |
| **Windows (native)** | PowerShell + Task Scheduler | ⚠️ 2-3 hrs | Fair | ❌ Only if required |

### My Recommendations

**For Your Team:**

1. **macOS users:** ✅ Use current implementation (done)
2. **Linux users:** ✅ Use cron approach (10 min setup)
3. **Windows users:**
   - **Best:** WSL2 + cron (works like Linux)
   - **Alternative:** Manual backups via `./scripts/backup-qdrant.sh`
   - **Last resort:** Create PowerShell version (only if demanded)

### Implementation Priority

**Phase 1 (Now):** ✅ macOS (complete)

**Phase 2 (If needed):** Linux cron support
- Document in README
- Test on Ubuntu/Debian
- Estimated effort: 1 hour

**Phase 3 (Optional):** systemd support
- For production Linux servers
- Estimated effort: 2 hours

**Phase 4 (Only if demanded):** Windows PowerShell
- Survey team first
- If 2+ Windows users: Create PowerShell version
- Estimated effort: 3-4 hours

---

## Cross-Platform Docker & Recovery

**Good news:** These work identically on all platforms:

✅ **Docker commands** (same everywhere):
```bash
docker-compose up -d
docker ps
docker logs recall-qdrant-6337
```

✅ **Named volumes** (same everywhere):
```bash
docker volume ls
docker volume inspect recall-qdrant-data
```

✅ **Backup/restore** (same everywhere):
```bash
./scripts/backup-qdrant.sh my-backup
./scripts/restore-qdrant.sh backups/my-backup.tar.gz
```

✅ **Recall CLI** (same everywhere):
```bash
recall recover
recall stats
```

**Platform-specific only:**
- Automated scheduling (launchd vs cron vs Task Scheduler)
- Script syntax (bash vs PowerShell)
- File paths (`/Users/` vs `/home/` vs `C:\Users\`)

---

## Testing Strategy

### Before Rolling Out to Team

**Test on each platform:**

1. **Linux VM** (30 minutes)
   ```bash
   # Spin up Ubuntu VM
   # Install Docker
   # Test cron approach
   # Verify backups work
   ```

2. **WSL2** (30 minutes)
   ```bash
   # Install WSL2
   # Test Linux approach works in WSL2
   # Verify Docker Desktop integration
   ```

3. **Windows Native** (skip unless required)
   - Only implement if team members demand it
   - WSL2 is better solution

### Platform-Specific Issues to Watch

**Linux:**
- Cron environment variables (PATH, etc.)
- Log rotation (logrotate integration)
- Permissions on backup directory

**Windows:**
- Path separators (`\` vs `/`)
- Line endings (CRLF vs LF)
- Docker Desktop volume mounting
- Task Scheduler reliability

---

## Documentation Updates Needed

If we add Linux/Windows support:

1. **README.md:** Platform-specific installation sections
2. **AUTOMATED_BACKUP_RECOVERY_GUIDE.md:** Add Linux/Windows sections
3. **DOCKER_RELIABILITY.md:** Cross-platform notes
4. **New:** `scripts/setup-auto-backup-linux.sh`
5. **New:** `scripts/setup-auto-backup-windows.ps1` (if needed)

---

## My Final Opinion

### What to Do Now:

**✅ Ship with macOS support only**
- Document that automated backups work on macOS
- Provide manual backup instructions for other platforms
- Wait for user demand before building Linux/Windows automation

**✅ Document manual backup for all platforms**
- Works everywhere: `./scripts/backup-qdrant.sh`
- Works everywhere: `recall recover`
- Good enough for teams with mixed platforms

**✅ If Linux users request automation:**
- Add cron instructions to README (1 hour)
- Test on Ubuntu VM (30 min)
- Ship it

**❌ Don't build Windows native until demanded**
- WSL2 is better solution
- PowerShell version only if absolutely necessary
- Wait for 2+ team members to request it

### Quick Win: Universal Manual Backups

All platforms can use manual backups **today**:

```bash
# Before risky operations (works everywhere)
./scripts/backup-qdrant.sh pre-migration-backup

# If corruption happens (works everywhere)
recall recover --backup backups/pre-migration-backup.tar.gz
```

This gives **80% of the value with 100% platform compatibility.**

Automation is nice but manual backups are good enough for most teams.

---

**Bottom Line:**
- macOS: ✅ Fully automated (done)
- Linux: Easy to add (1 hour)
- Windows: WSL2 + Linux approach (recommended)
- Windows native: Only if absolutely necessary (3-4 hours)

I'd wait for team feedback before investing in Linux/Windows automation.
