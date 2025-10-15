# Recall Installation Guide

Comprehensive installation instructions for all platforms and setups.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Plugin Installation (Recommended)](#plugin-installation-recommended)
3. [Manual Installation](#manual-installation)
4. [Platform-Specific Notes](#platform-specific-notes)
5. [Troubleshooting](#troubleshooting)
6. [Verification](#verification)

---

## Prerequisites

### Required

- **Python 3.10+** ([Download](https://www.python.org/downloads/))
- **Claude Code CLI** or compatible MCP client
- **Virtual environment** (REQUIRED for modern Python installations)

### Optional

- **Docker** (required for network mode / multi-project support)
  - [Docker Desktop](https://www.docker.com/products/docker-desktop/) for macOS/Windows
  - Docker Engine for Linux

### Disk Space

- ~3.5GB for Arctic embedding model (downloaded automatically on first use)
- ~500MB for Python dependencies
- ~1GB for Qdrant data storage (grows with usage)

---

## Plugin Installation (Recommended)

### Step 1: Add Plugin Marketplace

```bash
/plugin marketplace add WKassebaum/Recall
```

### Step 2: Install Plugin

```bash
/plugin install recall@Recall
```

### Step 3: Install Python Dependencies

```bash
/recall-install
```

**⚠️ Important:** If you encounter this error:

```
error: externally-managed-environment
× This environment is externally managed
```

**Solution:** Modern Python installations (especially Homebrew on macOS) use PEP 668 externally-managed environments. You need to create a virtual environment first:

```bash
# Navigate to plugin directory
cd ~/.claude/plugins/recall@Recall

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate     # Windows

# Now install dependencies
pip install -e .
```

### Step 4: Update MCP Configuration

After creating a virtual environment, you MUST update the MCP configuration to use the venv Python:

**Option A: Automatic (recommended):**
```bash
# Navigate to plugin directory
cd ~/.claude/plugins/recall@Recall

# Run doctor to check and fix configuration
recall doctor  # Coming soon in v1.4
```

**Option B: Manual:**

Edit `.mcp.json`:

```json
{
  "mcpServers": {
    "recall": {
      "command": "${CLAUDE_PLUGIN_ROOT}/.venv/bin/python",  // ✅ Use venv Python
      "args": ["-m", "recall.mcp.server"],
      "env": {
        "PYTHONPATH": "${CLAUDE_PLUGIN_ROOT}/src"
      }
    }
  }
}
```

### Step 5: Configure Storage Mode

```bash
recall setup
```

Choose between:
- **Embedded mode** (simple, ONE project at a time)
- **Network mode** (Docker, multi-project support) ✅ Recommended

### Step 6: Restart Claude Code

```bash
# Cmd/Ctrl + Q to quit
# Then relaunch
```

### Step 7: Verify Installation

```bash
/recall-setup
```

Expected output:
```
✅ Python 3.13.7 (compatible)
✅ Virtual environment detected
✅ Qdrant running: localhost:6333
✅ Embedder model available: arctic-embed-m (768D)
✅ Configuration valid
```

---

## Manual Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/WKassebaum/Recall.git
cd Recall
```

### Step 2: Create Virtual Environment

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (Command Prompt):**
```cmd
python -m venv .venv
.venv\Scripts\activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

> **Note:** If you see "script execution is disabled" on Windows, run:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

### Step 3: Install Dependencies

```bash
pip install -e .
```

**For development:**
```bash
pip install -e ".[dev]"
```

### Step 4: Configure MCP Server

**Option A: Using Claude Code CLI (automatic):**
```bash
claude mcp add-json --scope user recall '{
  "command": "/absolute/path/to/Recall/.venv/bin/python",
  "args": ["-m", "recall.mcp.server"],
  "env": {
    "PYTHONPATH": "/absolute/path/to/Recall/src"
  }
}'
```

> **Important:** Replace `/absolute/path/to/Recall/` with your actual path. Use `pwd` to get the current directory.

**Option B: Manual (edit ~/.mcp.json):**

Add to `~/.mcp.json` (create if it doesn't exist):

```json
{
  "mcpServers": {
    "recall": {
      "command": "/absolute/path/to/Recall/.venv/bin/python",
      "args": ["-m", "recall.mcp.server"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/Recall/src"
      }
    }
  }
}
```

### Step 5: Configure Storage Mode

```bash
recall setup
```

### Step 6: Restart Claude Code and Verify

```bash
# Restart Claude Code (Cmd/Ctrl + Q)

# In Claude Code:
mcp__recall__memory_stats()
```

---

## Platform-Specific Notes

### macOS (Homebrew Python)

**Common Issues:**

1. **PEP 668 Error** - Virtual environment is REQUIRED
   ```bash
   # Solution
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Command Not Found** - Python not in PATH
   ```bash
   # Solution
   brew install python@3.11
   echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.zshrc
   source ~/.zshrc
   ```

3. **Docker Desktop Required** for network mode
   ```bash
   brew install --cask docker
   ```

**Activation Command:**
```bash
source .venv/bin/activate
```

---

### Linux (Ubuntu/Debian)

**Prerequisites:**
```bash
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv python3-pip
```

**Docker Installation:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER  # Add current user to docker group
newgrp docker  # Refresh groups
```

**Activation Command:**
```bash
source .venv/bin/activate
```

---

### Windows

**Prerequisites:**
- Python from [python.org](https://www.python.org/downloads/) (NOT Microsoft Store version)
- Check "Add Python to PATH" during installation

**PowerShell Execution Policy:**
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

**Docker Desktop:**
- Download from [docker.com](https://www.docker.com/products/docker-desktop/)
- Requires Windows 10/11 Pro or Enterprise (for Hyper-V)
- OR use WSL2 backend

**Activation Command:**
```cmd
.venv\Scripts\activate        # Command Prompt
.venv\Scripts\Activate.ps1    # PowerShell
```

**Path Separators:**
- Use backslashes: `.venv\Scripts\activate`
- OR forward slashes work in PowerShell: `.venv/Scripts/activate`

---

## Troubleshooting

### Error: externally-managed-environment

**Cause:** Modern Python installations (PEP 668) prevent global pip installs.

**Solution:**
```bash
python3 -m venv .venv
source .venv/bin/activate  # Activate FIRST
pip install -e .           # Then install
```

---

### Error: MCP Server Not Found

**Cause:** `.mcp.json` points to system Python instead of venv Python.

**Check:**
```bash
# See what Python your MCP config uses
cat ~/.mcp.json | grep "command"
```

**Fix:**
Update `.mcp.json` to use full path to venv Python:
```json
{
  "command": "/absolute/path/to/.venv/bin/python"  // Not just "python"
}
```

---

### Error: Qdrant Connection Failed

**Symptoms:**
```
❌ Failed to connect to Qdrant: Connection refused
```

**Network Mode Solutions:**

1. **Check if Docker is running:**
   ```bash
   docker ps
   ```

2. **Start Qdrant:**
   ```bash
   docker run -d --name recall-qdrant -p 6333:6333 qdrant/qdrant:latest
   ```

3. **Verify Qdrant is accessible:**
   ```bash
   curl http://localhost:6333/health
   ```

**Embedded Mode Solutions:**

1. **Check file permissions:**
   ```bash
   ls -la ~/.recall/qdrant/
   chmod -R u+rw ~/.recall/qdrant/
   ```

2. **Close other Claude Code windows** (embedded mode supports ONE window at a time)

---

### Error: Model Download Timeout

**Symptoms:**
```
Downloading Arctic model... (hangs)
```

**Solution:**
```bash
# Pre-download model manually with better progress feedback
python -c "
from sentence_transformers import SentenceTransformer
print('Downloading Arctic model (3.5GB)...')
model = SentenceTransformer('Snowflake/snowflake-arctic-embed-m')
print('✅ Download complete!')
"
```

**Alternative (faster mirror):**
```bash
export HF_ENDPOINT=https://hf-mirror.com  # China mirror
# Then retry
```

---

### Error: Database Locked (Embedded Mode)

**Symptoms:**
```
sqlite3.OperationalError: database is locked
```

**Cause:** Multiple Claude Code windows trying to access embedded Qdrant simultaneously.

**Solution:**
1. **Close all Claude Code windows except one**
2. **OR switch to network mode:**
   ```bash
   recall setup --reconfigure
   # Choose "Network (Docker)" mode
   ```

---

### Warning: datetime.utcnow() deprecated

**Cause:** Using Python 3.12+ which deprecated `datetime.utcnow()`.

**Note:** Recall v1.3.3+ already uses timezone-aware datetimes. If you see this warning, you're using an older version:

```bash
# Update to latest version
cd ~/.claude/plugins/recall@Recall
git pull origin master
pip install -e .
```

---

## Verification

### Quick Health Check

```bash
# From command line
recall doctor  # Coming in v1.4

# OR manual checks:

# 1. Check Python version
python --version
# Expected: Python 3.10+

# 2. Check virtual environment
which python
# Expected: /path/to/Recall/.venv/bin/python

# 3. Check Qdrant
curl http://localhost:6333/health
# Expected: {"status":"ok"}

# 4. Check imports
python -c "import recall; print('✅ Recall installed')"

# 5. Check MCP server
python -m recall.mcp.server --help
# Should show MCP server help
```

### Full Validation

```bash
# In Claude Code, test MCP tools:
mcp__recall__memory_stats()

# Expected output:
📊 Recall Statistics:
Total chunks: 0 (or more if you have data)
Active collection: recall_768d
Embedder: Snowflake/snowflake-arctic-embed-m
Dimension: 768D
Qdrant: localhost:6333
```

---

## Next Steps

After successful installation:

1. **Read Usage Guide:** See [README.md#usage](README.md#usage)
2. **Check CLAUDE.md:** Auto-trigger patterns and best practices
3. **Store First Memory:** Use `/recall-store` slash command
4. **Explore Retrieval:** Try semantic, chronological, and hybrid searches

---

## Getting Help

- **Issues:** [GitHub Issues](https://github.com/WKassebaum/Recall/issues)
- **Discussions:** [GitHub Discussions](https://github.com/WKassebaum/Recall/discussions)
- **Documentation:** [docs/](docs/)

---

**Version:** 1.3.3+ | **Last Updated:** 2025-10-15
