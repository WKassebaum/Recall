# Recall Installation Guide

Comprehensive installation instructions for all platforms and setups.

---

## Table of Contents

1. [AI Agent Installation Guide](#ai-agent-installation-guide) **← Start here if you're Claude or another AI assistant**
2. [Prerequisites](#prerequisites)
3. [Plugin Installation (Recommended)](#plugin-installation-recommended)
4. [Manual Installation](#manual-installation)
5. [Platform-Specific Notes](#platform-specific-notes)
6. [Troubleshooting](#troubleshooting)
7. [Verification](#verification)

---

## AI Agent Installation Guide

> **For Claude Code, Cursor, Windsurf, and other AI coding assistants**
>
> If a user has asked you to install Recall, follow this guide. It provides complete instructions including steps that require user action.

### Quick Assessment

Before starting, check if Recall is already installed:

```bash
# Check if recall MCP tools are available
/mcp  # In Claude Code - look for "recall" in the list
```

If `recall` or `plugin:recall:recall` appears with tools like `ingest_memory`, `recall_memory`, `memory_stats` - Recall is already installed. Run `mcp__recall__diagnose_installation()` to verify health.

---

### Installation Steps for AI Agents

Follow these steps in order. Steps marked with **[USER ACTION]** require the user to perform manually.

#### Step 1: Clone Repository

```bash
# Clone to a suitable location
cd ~/WorkDev  # Or user's preferred development directory
git clone https://github.com/WKassebaum/Recall.git
cd Recall
```

#### Step 2: Create Virtual Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# OR: venv\Scripts\activate  # Windows
```

#### Step 3: Install Dependencies

```bash
# Install Recall in editable mode
pip install -e .
```

#### Step 4: Get Absolute Paths

**Important:** You need absolute paths for MCP configuration.

```bash
# Get the Recall directory path
RECALL_DIR=$(pwd)
echo "Recall directory: $RECALL_DIR"

# Get the Python interpreter path
PYTHON_PATH="$RECALL_DIR/venv/bin/python"
echo "Python path: $PYTHON_PATH"
```

#### Step 5: Configure MCP Server **[USER ACTION REQUIRED]**

**Tell the user:**

> I've installed Recall, but you need to add the MCP server configuration to Claude Code. Please run this command:
>
> ```bash
> claude mcp add recall -s user -- /path/to/Recall/venv/bin/python -m recall.mcp.server
> ```
>
> Replace `/path/to/Recall` with: `{RECALL_DIR}` (the path I showed above)
>
> **OR** manually add to `~/.claude.json`:
>
> ```json
> {
>   "mcpServers": {
>     "recall": {
>       "command": "/path/to/Recall/venv/bin/python",
>       "args": ["-m", "recall.mcp.server"],
>       "env": {
>         "PYTHONPATH": "/path/to/Recall/src"
>       }
>     }
>   }
> }
> ```

#### Step 6: Restart Claude Code **[USER ACTION REQUIRED]**

**Tell the user:**

> Please restart Claude Code to load the new MCP server:
> - Press **Cmd+Q** (macOS) or **Alt+F4** (Windows/Linux) to quit completely
> - Relaunch Claude Code

#### Step 7: Verify Installation

After restart, verify the installation:

```bash
# Check MCP tools are available
/mcp  # Should show "recall" with 4 tools

# Run diagnostics
mcp__recall__diagnose_installation()

# Check stats
mcp__recall__memory_stats()
```

**Expected output from memory_stats:**
```
📊 Recall Statistics:
Total chunks: 0
Active collection: recall_768d
Embedder: Snowflake/snowflake-arctic-embed-m
Dimension: 768D
Qdrant: embedded (~/.recall/qdrant/)
```

---

### Common Issues During AI-Assisted Installation

#### Issue: "externally-managed-environment" Error

**Cause:** System Python (especially Homebrew on macOS) blocks global pip installs.

**Solution:** Already handled - we use a virtual environment. If error persists:
```bash
cd /path/to/Recall
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

#### Issue: MCP Server Not Appearing After Restart

**Cause:** Configuration not added correctly to `~/.claude.json`.

**Solution:** Ask user to verify:
```bash
cat ~/.claude.json | grep -A 10 "recall"
```

If empty, the MCP add command failed. Have user manually edit `~/.claude.json`.

#### Issue: Model Download Slow/Stuck

**Cause:** First-time embedding model download (~3.5GB).

**Solution:** This is normal. Tell user:
> The Arctic embedding model (~3.5GB) is downloading. This takes 1-5 minutes depending on connection speed. Subsequent runs are instant.

#### Issue: Module Not Found Errors

**Cause:** Wrong Python interpreter or missing PYTHONPATH.

**Solution:** Verify paths in `~/.claude.json` are absolute and correct:
- `command` must point to `venv/bin/python` (not system Python)
- `PYTHONPATH` must point to `/path/to/Recall/src`

---

### Post-Installation: First Memory Test

Once installed, test with a simple memory:

```python
# Store a test memory
mcp__recall__ingest_memory(
    content="Recall installation successful! This is a test memory.",
    session_id="installation-test",
    metadata={
        "event_type": "milestone",
        "tags": "testing,installation"
    }
)

# Retrieve it
mcp__recall__recall_memory(
    query="installation test",
    session_id="installation-test"
)
```

**Success criteria:** The test memory should be retrieved with a high similarity score (>0.8).

---

### Summary for AI Agents

| Step | Action | Who |
|------|--------|-----|
| 1 | Clone repository | AI |
| 2 | Create virtual environment | AI |
| 3 | Install dependencies | AI |
| 4 | Get absolute paths | AI |
| 5 | Configure MCP server | **User** (must add to ~/.claude.json) |
| 6 | Restart Claude Code | **User** (must quit and relaunch) |
| 7 | Verify installation | AI |

**Key User Actions:**
1. Add MCP configuration (Step 5)
2. Restart Claude Code (Step 6)

These cannot be automated because they require modifying Claude Code's configuration and restarting the application.

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
/mcp
```

**Expected:** Shows `plugin:recall:recall` with 4 tools (ingest_memory, recall_memory, memory_stats, diagnose_installation)

**If you see "Failed to reconnect to plugin:recall:recall"**, see [Plugin Installation Troubleshooting](#plugin-installation-troubleshooting) below.

### Step 8: Run Diagnostics (Optional)

```bash
# In Claude Code, use the diagnose tool
mcp__recall__diagnose_installation()
```

This will check:
- ✅ MCP server configuration in ~/.claude.json
- ✅ Python version compatibility
- ✅ Virtual environment setup
- ✅ Recall package installation
- ✅ Qdrant connectivity
- ✅ Configuration files
- ✅ Embedding model availability

**Sample output:**
```
🏥 Recall Installation Diagnostics
========================================

🔍 Checking MCP server configuration...
   ✅ MCP server registered (plugin:recall:recall)
   ✅ Using virtual environment Python
   ✅ Python exists: /path/to/.venv/bin/python

🔍 Checking Python version...
   ✅ Python 3.13.7 (compatible)

🔍 Checking virtual environment...
   ✅ Virtual environment: /path/to/.venv

🔍 Checking Recall package...
   ✅ Recall v1.3.5 installed
   ✅ Package imports successfully

🔍 Checking Qdrant connectivity...
   ✅ Qdrant connected: 0 chunks
   ✅ Mode: embedded (/Users/username/.recall/qdrant)

🔍 Checking configuration files...
   ✅ Configuration: /Users/username/.recall/.env

🔍 Checking embedding model...
   ✅ Model: Snowflake/snowflake-arctic-embed-m
   ✅ Dimension: 768D

========================================
✅ All checks passed!

Your Recall installation is healthy and ready to use.
```

---

## Plugin Installation Troubleshooting

### Quick Diagnosis Tool

**Before manual troubleshooting, run the diagnostic tool to identify issues:**

```bash
# In Claude Code (if MCP server is running)
mcp__recall__diagnose_installation()
```

This will automatically check all common issues and provide specific fix recommendations.

**If MCP server isn't running yet**, proceed with manual troubleshooting below.

---

### Known Issue: MCP Server Not Auto-Registered ⚠️

**Symptom:**
```
Failed to reconnect to plugin:recall:recall
```

**Cause:** Claude Code's plugin system may not automatically add MCP server configuration to `~/.claude.json`.

**Verification:**
```bash
# Check if configuration exists
cat ~/.claude.json | jq '.mcpServers."plugin:recall:recall"'
```

**If output is `null` or empty, manual configuration is required:**

---

### Fix 1: Manual MCP Server Configuration

**Step 1: Create Virtual Environment** (if not already done)
```bash
cd ~/.claude/plugins/recall@Recall  # Or wherever plugin was installed
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

**Step 2: Get Plugin Directory Path**
```bash
cd ~/.claude/plugins/recall@Recall && pwd
# Example output: /Users/username/.claude/plugins/recall@Recall
```

**Step 3: Add MCP Server to ~/.claude.json**

**Option A: Using jq (automated)**
```bash
# Replace /path/to/Recall with output from Step 2
PLUGIN_DIR="/path/to/Recall"

jq --arg dir "$PLUGIN_DIR" \
  '.mcpServers."plugin:recall:recall" = {
    "command": ($dir + "/.venv/bin/python"),
    "args": ["-m", "recall.mcp.server"],
    "env": {
      "PYTHONPATH": ($dir + "/src"),
      "RECALL_CONFIG": ($dir + "/config.yaml"),
      "RECALL_QDRANT_MODE": "embedded",
      "RECALL_QDRANT_PATH": ($ENV.HOME + "/.recall/qdrant")
    }
  }' ~/.claude.json > /tmp/claude_updated.json && \
  mv /tmp/claude_updated.json ~/.claude.json
```

**Option B: Manual Edit**

Edit `~/.claude.json` and add:
```json
{
  "mcpServers": {
    "plugin:recall:recall": {
      "command": "/absolute/path/to/Recall/.venv/bin/python",
      "args": ["-m", "recall.mcp.server"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/Recall/src",
        "RECALL_CONFIG": "/absolute/path/to/Recall/config.yaml",
        "RECALL_QDRANT_MODE": "embedded",
        "RECALL_QDRANT_PATH": "/Users/YOUR_USERNAME/.recall/qdrant"
      }
    }
  }
}
```

**Important Notes:**
- ✅ Use `plugin:recall:recall` as the key (NOT just `recall`)
- ✅ Use absolute paths (NOT `{{PLUGIN_DIR}}` template variables)
- ✅ Use `.venv/bin/python` (NOT just `python`)

**Step 4: Verify Configuration**
```bash
cat ~/.claude.json | jq '.mcpServers."plugin:recall:recall"'
```

Should display your configuration with absolute paths.

**Step 5: Restart Claude Code**
```bash
exit  # Exit completely
claude  # Start new session
```

**Step 6: Test Connection**
```bash
/mcp
```

Should now show `plugin:recall:recall` connected with 3 tools.

---

### Fix 2: Virtual Environment Issues

**Error:**
```
error: externally-managed-environment
× This environment is externally managed
```

**Cause:** Modern Python (PEP 668) requires virtual environments.

**Solution:**
```bash
cd ~/.claude/plugins/recall@Recall
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Then follow [Fix 1](#fix-1-manual-mcp-server-configuration) to configure MCP server.

---

### Fix 3: Import Errors / Module Not Found

**Error:**
```
ModuleNotFoundError: No module named 'recall'
```

**Cause:** Dependencies not installed or wrong Python interpreter.

**Solution:**
```bash
# 1. Ensure virtual environment exists
cd ~/.claude/plugins/recall@Recall
ls .venv/bin/python  # Should exist

# 2. Install dependencies
source .venv/bin/activate
pip install -e .

# 3. Verify installation
python -c "import recall; print(recall.__version__)"
# Should print: 1.3.4 (or current version)

# 4. Update ~/.claude.json to use venv Python
# See Fix 1 above
```

---

### Fix 4: Wrong MCP Server Namespace

**Error:**
```
Failed to reconnect to plugin:recall:recall
```

**Cause:** Using `"recall"` instead of `"plugin:recall:recall"` in `~/.claude.json`

**Wrong:**
```json
{
  "mcpServers": {
    "recall": { ... }  // ❌ Wrong namespace
  }
}
```

**Correct:**
```json
{
  "mcpServers": {
    "plugin:recall:recall": { ... }  // ✅ Correct namespace
  }
}
```

**Fix:**
```bash
# Remove old "recall" entry if present
jq 'del(.mcpServers.recall)' ~/.claude.json > /tmp/claude_updated.json
mv /tmp/claude_updated.json ~/.claude.json

# Add with correct namespace (see Fix 1)
```

---

### Fix 5: Template Variables Not Expanded

**Error:** Server fails to start

**Cause:** `{{PLUGIN_DIR}}` or `{{HOME}}` not expanded to absolute paths

**Wrong:**
```json
{
  "command": "{{PLUGIN_DIR}}/.venv/bin/python"  // ❌ Not expanded
}
```

**Correct:**
```json
{
  "command": "/Users/username/.claude/plugins/recall@Recall/.venv/bin/python"  // ✅ Absolute path
}
```

**Fix:** Use absolute paths (see [Fix 1](#fix-1-manual-mcp-server-configuration))

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

**Version:** 1.4.1 | **Last Updated:** 2025-12-07
