# Quick Fix: Enable Multi-Project Support (Network Mode)

**Issue:** Embedded Qdrant uses file locking, preventing multiple Claude Code windows or projects from using Recall simultaneously.

**Solution:** Switch to Network mode (Docker Qdrant) immediately while we finalize the `recall setup` wizard.

---

## Prerequisites

- Docker installed and running
- Qdrant container on port 6333 (or start one)

---

## Step 1: Start Docker Qdrant (if not already running)

```bash
# Check if Qdrant is already running
curl -s http://localhost:6333/healthz

# If not running, start it:
docker run -d \
  --name recall-qdrant \
  -p 6333:6333 \
  -v ~/.recall/docker-6333:/qdrant/storage \
  qdrant/qdrant:latest

# Wait 3 seconds for startup
sleep 3

# Verify it's running
curl -s http://localhost:6333/healthz
# Should return: {"title":"qdrant - vector search engine","version":"..."}
```

---

## Step 2: Create ~/.recall/.env File

```bash
# Create directory if it doesn't exist
mkdir -p ~/.recall

# Create .env configuration file
cat > ~/.recall/.env << 'EOF'
# Recall Configuration
# Last updated: 2025-10-15

# QDRANT MODE
RECALL_QDRANT_MODE=network

# Network Mode Settings (Docker)
RECALL_QDRANT_HOST=localhost
RECALL_QDRANT_PORT=6333

# Embedder Settings
RECALL_EMBEDDER_MODEL=Snowflake/snowflake-arctic-embed-m
RECALL_FALLBACK_ENABLED=true
RECALL_FALLBACK_MODEL=all-MiniLM-L6-v2
EOF

echo "✅ Configuration saved to ~/.recall/.env"
```

---

## Step 3: Update Plugin (Pull Latest Code)

```bash
# Navigate to plugin directory
cd ~/.claude/plugins/recall@Recall

# Pull latest changes (includes .env loading support)
git pull origin master

# Verify you have the latest version
git log --oneline -1
# Should show: "Update MCP server to load .env config" or similar
```

---

## Step 4: Restart Claude Code

1. Quit Claude Code completely: **Cmd/Ctrl + Q**
2. Reopen Claude Code
3. The MCP server will now load the .env config and use Network mode

---

## Step 5: Verify Multi-Project Support

Run this in Claude Code:

```
/recall-stats
```

**Expected output:**
```
📊 Recall Statistics:
Total chunks: X
Active collection: recall_768d
Embedder: snowflake-arctic-embed-m
Dimension: 768D
Qdrant: localhost:6333  ← Should show network mode
```

**Test multi-project:**
1. Open multiple Claude Code windows
2. Each can use Recall simultaneously ✅
3. No "database locked" errors ✅

---

## Step 6: Migrate Existing Memories (Optional)

If you have memories in embedded mode and want to move them to network mode:

```bash
# This will be easier with the full `recall setup` wizard
# For now, manual migration:

# 1. Backup embedded data
cp -r ~/.recall/qdrant ~/.recall/qdrant-backup

# 2. Wait for full migration tool in next update
# Coming soon: recall migrate-mode --from embedded --to network
```

---

## Troubleshooting

### Issue: "Connection refused" after restart

```bash
# Check if Docker Qdrant is running
docker ps | grep recall-qdrant

# If not running, start it
docker start recall-qdrant

# Or create new one if it doesn't exist
docker run -d --name recall-qdrant -p 6333:6333 qdrant/qdrant:latest
```

### Issue: "ModuleNotFoundError: No module named 'dotenv'"

```bash
# Install python-dotenv
cd ~/.claude/plugins/recall@Recall
pip install python-dotenv

# Or if using plugin system
/recall-install  # Should install all dependencies including python-dotenv
```

### Issue: Stats still show "embedded" mode

```bash
# Verify .env file exists and has correct content
cat ~/.recall/.env | grep MODE

# Should show: RECALL_QDRANT_MODE=network

# If not, recreate the .env file (Step 2 above)
```

---

## What This Gives You

✅ **Multiple Claude Code windows** - No more file locking
✅ **Multiple projects simultaneously** - Each can use Recall
✅ **Team collaboration ready** - Shared Qdrant instance
✅ **Better performance** - Docker Qdrant optimized for concurrent access

---

## Coming Soon: Full `recall setup` Wizard

The next update will include:

```bash
recall setup
```

This wizard will:
- Detect your system (Docker, existing Qdrant)
- Guide you through mode selection
- Warn about limitations (embedded vs network)
- Test connections
- Save configuration automatically
- Migrate data between modes

**For now, this quick fix gets you multi-project support immediately!**

---

## Need Help?

- Docker installation: https://www.docker.com/get-started
- Qdrant docs: https://qdrant.tech/documentation/
- Report issues: https://github.com/WKassebaum/Recall/issues
