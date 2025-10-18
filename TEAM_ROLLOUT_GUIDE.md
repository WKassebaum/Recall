# Team Rollout Guide - Breaking Changes & Migration

## ⚠️ CRITICAL: Breaking Changes Analysis

### What Changed (v1.4.0)

**✅ NON-BREAKING Changes:**
1. `docker-compose.yml` - NEW FILE (optional to use)
2. `qdrant-config.yaml` - NEW FILE (performance tuning only)
3. `recall recover` command - NEW COMMAND (backward compatible)
4. Backup scripts - NEW FILES (additive only)
5. Named volumes approach - NEW OPTION (not forced)

**⚠️ POTENTIALLY BREAKING Changes:**
1. **Docker volume type change** - IF colleagues switch from bind mounts to named volumes

---

## Impact Assessment

### Scenario 1: No Existing Data ✅ NO IMPACT

**Who:** New Recall users, fresh installations

**Action Required:** None - just use new setup

```bash
git pull
docker-compose up -d
recall setup
```

**Risk:** Zero

---

### Scenario 2: Using Embedded Mode ✅ NO IMPACT

**Who:** Users with `RECALL_QDRANT_MODE=embedded` in `~/.recall/.env`

**Action Required:** None - embedded mode unchanged

**Risk:** Zero

---

### Scenario 3: Using Network Mode (Bind Mounts) ⚠️ REQUIRES MIGRATION

**Who:** Users with existing Qdrant Docker container using bind mounts

**Current Setup:**
- Container uses `-v /path/to/local/dir:/qdrant/storage`
- Data stored on local filesystem
- Example: `-v ~/.recall/docker-6337:/qdrant/storage`

**Action Required:** Run migration script OR continue using old approach

**Risk:** Medium (data loss if migration done incorrectly)

---

## Recommended Rollout Strategy

### Option A: Backward Compatible (RECOMMENDED) ⭐

**Keep both approaches supported:**

1. **Existing users:** Keep using bind mounts (works fine)
2. **New users:** Use named volumes (more reliable)
3. **Migration:** Optional, when user chooses

**Advantages:**
- ✅ Zero breaking changes
- ✅ Users migrate at their own pace
- ✅ Fallback available if issues

**Implementation:** Document both approaches in README

---

### Option B: Require Migration

**Force everyone to named volumes:**

1. **All users must migrate** before updating
2. Provide migration script
3. Breaking change in v1.4.0

**Advantages:**
- ✅ Everyone on same reliable setup
- ✅ Simpler to support (one approach)

**Disadvantages:**
- ❌ Risky if migration fails
- ❌ Requires coordination
- ❌ Potential data loss

**My Opinion:** Only if team is small (<5 people) and you can coordinate

---

## Safe Migration Path (If Choosing Option B)

### Pre-Migration Checklist

```bash
# 1. Verify current setup
docker ps --filter "name=recall-qdrant"
docker inspect <container-name> | grep -A5 "Mounts"

# 2. Check data size
du -sh ~/.recall/docker-6337/  # Or wherever bind mount is

# 3. Create safety backup
tar czf recall-pre-migration-backup.tar.gz ~/.recall/docker-6337/

# 4. Verify backup
tar -tzf recall-pre-migration-backup.tar.gz | head
```

### Migration Steps

**Automated (Recommended):**

```bash
cd /path/to/SemVecMem
./scripts/migrate-to-named-volumes.sh
```

**Manual (If you prefer control):**

```bash
# 1. Stop current container
docker stop recall-qdrant-6337
docker rm recall-qdrant-6337

# 2. Create named volume
docker volume create recall-qdrant-data

# 3. Copy data from bind mount to named volume
docker run --rm \
  -v ~/.recall/docker-6337:/source:ro \
  -v recall-qdrant-data:/dest \
  alpine cp -a /source/. /dest/

# 4. Start with docker-compose
docker-compose up -d

# 5. Verify
curl http://localhost:6337/collections
recall stats
```

### Post-Migration Verification

```bash
# Check container is running
docker ps --filter "name=recall-qdrant-6337"

# Verify named volume
docker volume inspect recall-qdrant-data

# Test Recall
recall stats
recall search "test query"

# If all works, backup and remove old bind mount
tar czf recall-old-bind-mount.tar.gz ~/.recall/docker-6337/
rm -rf ~/.recall/docker-6337/
```

---

## Rollback Plan

### If Migration Fails

```bash
# 1. Stop new container
docker-compose down

# 2. Remove named volume
docker volume rm recall-qdrant-data

# 3. Restart with old bind mount approach
docker run -d \
  --name recall-qdrant-6337 \
  -p 6337:6333 \
  -v ~/.recall/docker-6337:/qdrant/storage \
  --restart unless-stopped \
  qdrant/qdrant:latest

# 4. Verify
curl http://localhost:6337/collections
recall stats
```

**Original data is safe** - migration script never deletes bind mount data.

---

## Communication to Team

### Email Template

```
Subject: [OPTIONAL] Recall v1.4.0 - Improved Reliability

Team,

Recall v1.4.0 includes reliability improvements for multi-project use:

✅ NEW FEATURES (Non-breaking):
- Automated backup system (macOS)
- Auto-recovery from corruption
- Better WAL tuning for stability

⚠️ OPTIONAL MIGRATION:
If you're using Qdrant in Docker network mode, you can optionally
migrate to named volumes for better reliability.

WHO NEEDS TO MIGRATE:
- ✅ You: if using network mode AND want better reliability
- ❌ You: if using embedded mode (no change needed)
- ❌ You: if you're happy with current setup (works fine)

MIGRATION (Optional):
1. git pull
2. ./scripts/migrate-to-named-volumes.sh
3. Takes 2-3 minutes, preserves all data

SKIP MIGRATION:
- Your current setup continues working
- No action needed

Questions? Reply to this thread.

Documentation: TEAM_ROLLOUT_GUIDE.md
```

---

## FAQ for Team

### Q: Do I have to migrate?

**A:** No. Your current setup continues working. Migration is optional.

### Q: What if I don't migrate?

**A:** You keep using bind mounts. Works fine, just slightly less reliable than named volumes on macOS/Windows.

### Q: Will my data be lost?

**A:** No. Migration script preserves all data. Original data never deleted.

### Q: Can I rollback?

**A:** Yes. Migration script keeps original data. Easy rollback.

### Q: What if I'm on Linux?

**A:** Named volumes benefit macOS/Windows most. Linux users can stay on bind mounts with no issues.

### Q: What about embedded mode users?

**A:** Zero changes. Embedded mode unaffected.

---

## Testing Strategy (Before Team Rollout)

### 1. Test on Dev Machine

```bash
# Create test bind mount
mkdir -p /tmp/test-recall-bind
docker run -d --name test-recall \
  -p 6338:6333 \
  -v /tmp/test-recall-bind:/qdrant/storage \
  qdrant/qdrant:latest

# Add some test data
# ...

# Run migration on test setup
BIND_MOUNT_PATH=/tmp/test-recall-bind \
CONTAINER_NAME=test-recall \
VOLUME_NAME=test-recall-data \
./scripts/migrate-to-named-volumes.sh

# Verify migration worked
docker exec test-recall-data ls /qdrant/storage

# Cleanup
docker stop test-recall
docker rm test-recall
docker volume rm test-recall-data
```

### 2. Test with Colleague (Volunteer)

```bash
# Have 1 colleague with non-critical data test migration
# Document any issues
# Refine script if needed
```

### 3. Rollout to Team

**Phased approach:**
- Week 1: Volunteer early adopters (1-2 people)
- Week 2: If successful, document and offer to all
- Week 3: Support stragglers

---

## Platform-Specific Considerations

### macOS

**Impact:** High - Named volumes significantly more reliable than bind mounts

**Recommendation:** Encourage migration

### Linux

**Impact:** Low - Both approaches work well

**Recommendation:** Migration optional, no pressure

### Windows

**Impact:** High - Similar issues to macOS

**Recommendation:** Encourage migration (or WSL2)

---

## What NOT to Do ❌

1. **Don't force migration** - Make it optional
2. **Don't delete bind mount data** - Migration script preserves it
3. **Don't rush rollout** - Test thoroughly first
4. **Don't skip backups** - Always backup before migrating
5. **Don't assume one-size-fits-all** - Some users can skip migration

---

## Summary: Answer to Your Question

### "Will colleagues need to wipe their databases?"

**Short Answer: NO** ✅

**Details:**

**✅ No Data Loss Scenarios:**
1. **Using embedded mode** - Zero changes needed
2. **Using network mode (bind mounts)** - Can continue as-is OR migrate safely with script
3. **New users** - Just use new setup

**⚠️ Migration Needed (But NOT wiping):**
- Only if switching from bind mounts to named volumes
- Migration script copies data (not wiping)
- Original data preserved as backup

**❌ Wiping Only Needed If:**
- Colleague wants to start fresh (their choice)
- Corruption already happened (unrelated to our changes)

### "Should we make colleagues migrate?"

**My Recommendation: NO**

Make it optional:
- Document both approaches
- Let users migrate on their schedule
- Provide migration script for those who want better reliability
- Support both bind mounts and named volumes

**Benefits:**
- ✅ Zero breaking changes
- ✅ Users choose when to migrate
- ✅ Original data safe
- ✅ Fallback available
- ✅ Happy team

---

## Final Recommendation

### Ship v1.4.0 as Backward Compatible

**What to do:**

1. **Update README.md** with two approaches:
   - Option 1: Named volumes (recommended for reliability)
   - Option 2: Bind mounts (existing setup, works fine)

2. **Provide migration script** for those who want it:
   - `./scripts/migrate-to-named-volumes.sh`
   - Safe, preserves data
   - Optional, not required

3. **Document in CHANGELOG:**
   - New features (backups, recovery)
   - Optional migration to named volumes
   - No breaking changes if staying on bind mounts

4. **Communicate to team:**
   - "New features available"
   - "Migration optional"
   - "Your data is safe"

### Timeline

- **Now:** Ship v1.4.0 as backward compatible
- **Week 1:** Early adopters test migration
- **Week 2:** Offer migration to interested users
- **Week 3+:** Support both approaches indefinitely

**Result:** Happy team, no data loss, smooth rollout.

---

**Bottom Line:**
- **Breaking changes:** Zero (if we support both approaches)
- **Data wipe needed:** No
- **Migration required:** Optional
- **Risk level:** Low (with migration script)
- **Team impact:** Minimal

Ship it! 🚀
