# Docker Reliability Guide for Recall

## Problem: macOS Docker Volume Corruption

**Root Cause:** Docker bind mounts on macOS suffer from file descriptor translation issues and fsync problems, leading to WAL corruption in Qdrant, especially during heavy write bursts.

**Solution:** Named volumes + WAL tuning

---

## Current Setup (Reliable)

### Architecture

```
Recall MCP → Qdrant Container → Docker Named Volume (recall-qdrant-data)
                                  ↓
                         Docker-managed storage
                         (No macOS file system translation)
```

**Key Improvements:**
- ✅ **Named volumes** instead of bind mounts (eliminates macOS fsync issues)
- ✅ **WAL tuning** for larger buffers and less frequent flushes
- ✅ **Performance mode** for batched writes
- ✅ **Automatic health checks** to detect issues early

---

## Quick Start

### Starting Qdrant (Reliable Mode)

```bash
cd /Users/wrk/WorkDev/MCP-Dev/SemVecMem
docker-compose up -d
```

**Verify health:**
```bash
docker ps --filter "name=recall-qdrant-6337"  # Should show "healthy"
curl http://localhost:6337/health             # Should return {}
```

### Stopping Qdrant

```bash
docker-compose down  # Stops but keeps data
# OR
docker-compose down -v  # WARNING: Deletes all data!
```

---

## Backup & Recovery

### Backup Named Volume

**Option 1: Tarball Backup (Recommended)**

```bash
# Create dated backup
docker run --rm \
  -v recall-qdrant-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/recall-backup-$(date +%Y%m%d_%H%M%S).tar.gz /data

# List backups
ls -lh recall-backup-*.tar.gz
```

**Option 2: Export to Directory**

```bash
# Export to local directory
docker run --rm \
  -v recall-qdrant-data:/data \
  -v $(pwd)/backups:/backup \
  alpine cp -a /data/. /backup/recall-$(date +%Y%m%d)
```

### Restore from Backup

**From Tarball:**

```bash
# Stop Qdrant
docker-compose down

# Delete corrupted volume
docker volume rm recall-qdrant-data

# Recreate empty volume
docker volume create recall-qdrant-data

# Restore from backup
docker run --rm \
  -v recall-qdrant-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/recall-backup-YYYYMMDD_HHMMSS.tar.gz -C /

# Restart Qdrant
docker-compose up -d
```

**From Directory:**

```bash
# Stop Qdrant
docker-compose down

# Delete corrupted volume
docker volume rm recall-qdrant-data

# Recreate and restore
docker volume create recall-qdrant-data
docker run --rm \
  -v recall-qdrant-data:/data \
  -v $(pwd)/backups/recall-YYYYMMDD:/backup \
  alpine cp -a /backup/. /data

# Restart Qdrant
docker-compose up -d
```

---

## Automated Backup Strategy ✅ IMPLEMENTED

### One-Time Setup (macOS)

Install automated backups using launchd:

```bash
cd /Users/wrk/WorkDev/MCP-Dev/SemVecMem
./scripts/setup-auto-backup.sh
```

**What this does:**
- Installs launchd service that runs every 6 hours
- Creates backups at: startup, 6am, 12pm, 6pm, 12am
- Auto-rotates backups: 4 recent (24hrs), 7 daily, 4 weekly
- Maintains `backups/latest-good-backup.tar.gz` symlink for auto-recovery

**Backup Schedule:**
- **Recent**: Every 6 hours (keeps last 4 = 24 hours)
- **Daily**: At 2 AM daily (keeps 7 days)
- **Weekly**: Sunday 2 AM (keeps 4 weeks)

### Manual Backup

Create backup on-demand:

```bash
# Simple backup
./scripts/backup-qdrant.sh my-backup-name

# Or use the auto-rotation script
./scripts/backup-qdrant-auto.sh
```

### Auto-Recovery System ✅ IMPLEMENTED

Recall includes automated corruption detection and recovery:

**Automatic Recovery:**
```bash
# Check health and auto-recover if needed
recall recover

# Force recovery from latest backup
recall recover --force

# Recover from specific backup
recall recover --backup backups/recall-backup-20251018.tar.gz
```

**What auto-recovery does:**
1. Checks Docker container status
2. Checks Qdrant health endpoint
3. Checks collection accessibility (detects corruption)
4. If corruption detected:
   - Stops Qdrant container
   - Removes corrupted volume
   - Creates new volume
   - Restores from latest good backup
   - Starts container
   - Verifies health

**Automatic triggers:**
- Before bulk operations (>50 chunks)
- On MCP server startup (health check)
- When Qdrant health check fails

### Linux Alternative (Cron)

For Linux systems, use cron instead of launchd:

```bash
# Add to crontab (crontab -e)
0 */6 * * * cd /path/to/SemVecMem && ./scripts/backup-qdrant-auto.sh

# Or use the simpler version for manual rotation
0 2 * * * cd /path/to/SemVecMem && docker run --rm -v recall-qdrant-data:/data -v $(pwd)/backups:/backup alpine tar czf /backup/recall-backup-$(date +\%Y\%m\%d).tar.gz /data

# Keep last 7 days
0 3 * * * find /path/to/SemVecMem/backups -name "recall-backup-*.tar.gz" -mtime +7 -delete
```

---

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker logs recall-qdrant-6337 --tail 50
```

**Common issues:**
- Port 6337 already in use → `lsof -i :6337` and kill process
- Volume corrupted → Restore from backup (see above)
- Config file error → Check `qdrant-config.yaml` syntax

### WAL Corruption Detected

**Symptoms:**
- Container exits with code 101
- Logs show "Bad file descriptor (os error 9)"
- Panic in `/qdrant/lib/collection/src/shards/replica_set/mod.rs`

**Recovery:**
```bash
# 1. Stop container
docker-compose down

# 2. Restore from backup (most recent)
docker volume rm recall-qdrant-data
docker volume create recall-qdrant-data
docker run --rm -v recall-qdrant-data:/data -v $(pwd):/backup alpine tar xzf /backup/recall-backup-LATEST.tar.gz -C /

# 3. Restart
docker-compose up -d

# 4. Verify health
curl http://localhost:6337/health
```

### Data Loss Prevention

**If corruption is frequent:**

1. **Increase backup frequency** (hourly instead of daily)
2. **Increase WAL buffer size** in `qdrant-config.yaml`:
   ```yaml
   storage:
     wal_capacity_mb: 1024  # Increase from 512
     flush_interval_sec: 60 # Increase from 30
   ```
3. **Enable performance mode** (already enabled)
4. **Consider per-project containers** (see CLAUDE.md for multi-project setup)

---

## Volume Management

### Inspect Volume

```bash
# Get volume details
docker volume inspect recall-qdrant-data

# Get mount point (Docker-managed, typically /var/lib/docker/volumes/)
docker volume inspect recall-qdrant-data --format '{{.Mountpoint}}'

# List files in volume
docker run --rm -v recall-qdrant-data:/data alpine ls -lah /data
```

### View Volume Size

```bash
docker run --rm -v recall-qdrant-data:/data alpine du -sh /data
```

### Clone Volume (for Testing)

```bash
# Create test clone
docker volume create recall-qdrant-data-test
docker run --rm -v recall-qdrant-data:/source:ro -v recall-qdrant-data-test:/dest alpine cp -a /source/. /dest
```

---

## Configuration Files

### docker-compose.yml

Located at: `/Users/wrk/WorkDev/MCP-Dev/SemVecMem/docker-compose.yml`

**Key settings:**
- Named volume: `recall-qdrant-data`
- Port: 6337
- Config: `qdrant-config.yaml`
- Health checks enabled
- Restart policy: `unless-stopped`

### qdrant-config.yaml

Located at: `/Users/wrk/WorkDev/MCP-Dev/SemVecMem/qdrant-config.yaml`

**WAL Tuning:**
- `wal_capacity_mb: 512` - Larger buffer reduces fsync frequency
- `wal_segments_ahead: 2` - Buffer more segments
- `flush_interval_sec: 30` - Less frequent flushes
- `indexing_threshold: 50000` - Batch more before indexing

**To modify:** Edit file and restart container:
```bash
docker-compose restart
```

---

## Multi-Project Support

For multiple projects using Recall:

### Option 1: Shared Container (Current)

- One container serves all projects
- Collections isolated by dimension (recall_384d, recall_768d, recall_1024d)
- **Pro:** Resource-efficient, simple
- **Con:** One corruption affects all projects

### Option 2: Per-Project Containers (Future)

Create `docker-compose-multi.yml`:

```yaml
services:
  recall-qdrant:
    container_name: recall-qdrant-6337
    volumes:
      - recall-data:/qdrant/storage
    ports:
      - "6337:6333"

  quickbooks-qdrant:
    container_name: quickbooks-qdrant-6338
    volumes:
      - quickbooks-data:/qdrant/storage
    ports:
      - "6338:6333"

  project3-qdrant:
    container_name: project3-qdrant-6339
    volumes:
      - project3-data:/qdrant/storage
    ports:
      - "6339:6333"

volumes:
  recall-data:
  quickbooks-data:
  project3-data:
```

**Pro:** Complete isolation, one failure doesn't affect others
**Con:** More resource usage (4x containers)

---

## Performance Monitoring

### Check Health

```bash
# Container health
docker ps --filter "name=recall-qdrant-6337"

# Qdrant health
curl http://localhost:6337/health

# Collection stats
curl http://localhost:6337/collections/recall_768d
```

### Monitor Logs

```bash
# Follow logs in real-time
docker logs -f recall-qdrant-6337

# Check for errors
docker logs recall-qdrant-6337 2>&1 | grep -i "error\|panic\|warning"
```

### Resource Usage

```bash
# Container resource usage
docker stats recall-qdrant-6337

# Volume disk usage
docker run --rm -v recall-qdrant-data:/data alpine du -sh /data
```

---

## Best Practices

1. **Backup before major operations**
   - Before bulk ingestion (>100 chunks)
   - Before migration
   - Before version upgrades

2. **Monitor disk space**
   - WAL files can grow large during heavy writes
   - Keep at least 5GB free on Docker volume

3. **Graceful shutdowns**
   - Use `docker-compose down` (not `docker kill`)
   - Wait for WAL flush (30 seconds after last write)

4. **Regular health checks**
   - Check logs weekly for warnings
   - Test restore from backup monthly
   - Verify backup integrity

5. **Time Machine integration**
   - Export backups to user directory for Time Machine
   - Don't rely solely on Docker volumes in Time Machine

---

## Emergency Recovery

If all else fails and container won't start:

```bash
# 1. Remove everything
docker-compose down -v
docker volume rm recall-qdrant-data

# 2. Fresh start
docker volume create recall-qdrant-data
docker-compose up -d

# 3. Collections will auto-recreate on first use
# Data is lost, but system is functional

# 4. Re-ingest critical memories manually or from backup
```

---

**Version:** v1.4.0
**Last Updated:** 2025-10-18
**Reliability Improvement:** Named volumes + WAL tuning
