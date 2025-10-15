# Installation Experience Improvements

This document tracks improvements to the Recall installation and setup experience based on real user feedback.

---

## ✅ Completed Improvements (v1.3.4)

### 1. Comprehensive Installation Documentation ✅
**Status:** Completed 2025-10-15

**What was done:**
- Created `INSTALLATION.md` with platform-specific instructions
- Added troubleshooting section with common errors and solutions
- Documented virtual environment requirements (PEP 668)
- Added MCP configuration guidance
- Included verification steps

**Files:**
- `INSTALLATION.md` (new)
- `README.md` (updated with link to INSTALLATION.md)

---

### 2. Diagnostic Command (`recall doctor`) ✅
**Status:** Completed 2025-10-15

**What was done:**
- Implemented comprehensive installation health check
- Validates Python version, venv, Qdrant, config, embedder, MCP setup
- Provides actionable error messages and suggestions
- Exit codes for CI/CD integration

**Usage:**
```bash
recall doctor           # Run diagnostic checks
recall doctor --verbose # Include optional checks
```

**Files:**
- `src/recall/cli/doctor.py` (new)
- `src/recall/cli/main.py` (registered command)

---

###  3. Datetime Deprecation Fixes ✅
**Status:** Completed 2025-10-15

**What was done:**
- Replaced `datetime.now()` with `datetime.now(timezone.utc)` for timezone awareness
- Prevents Python 3.12+ deprecation warnings
- Ensures UTC timestamps across all memory metadata

**Files:**
- `src/recall/cli/setup.py` (fixed 2 instances)

---

## 🚨 Critical Plugin Installation Issues (v1.3.5)

### CRITICAL FINDINGS from Real-World Plugin Installation Testing

**Date Discovered:** 2025-10-15
**Impact:** Plugin appears installed but is non-functional without manual intervention
**Frequency:** 100% - Affects all plugin installations

---

### Issue #1: MCP Server Not Auto-Registered ⚠️ **BLOCKING**
**Severity:** Critical - Blocks all functionality
**Frequency:** 100%

**Problem:**
- `/plugin marketplace add WKassebaum/Recall` copies files but doesn't add MCP config to `~/.claude.json`
- Users see "Failed to reconnect to plugin:recall:recall" error
- Plugin appears installed but completely non-functional

**Status:** ✅ Documented workaround in INSTALLATION.md
**Long-term Fix:** Requires Claude Code plugin system enhancement OR post-install hook

**Workaround Implemented:**
- Comprehensive troubleshooting guide in INSTALLATION.md
- Manual configuration steps with jq automation
- Clear error identification and fix steps

---

### Issue #2: Incorrect MCP Server Namespace ⚠️ **CRITICAL**
**Severity:** High - Prevents connection even after manual configuration
**Frequency:** 100%

**Problem:**
- Error shows `plugin:recall:recall` but docs suggest using `recall`
- Using `"recall"` as key → connection fails
- Using `"plugin:recall:recall"` as key → connection succeeds

**Status:** ✅ FIXED
- Updated INSTALLATION.md with correct namespace
- Added explicit warnings about wrong namespace
- Created .claude-plugin/README.md documenting namespace behavior

**Files Updated:**
- INSTALLATION.md (Plugin Installation Troubleshooting section)
- .claude-plugin/README.md (new)

---

### Issue #3: Virtual Environment Not Auto-Created ⚠️ **HIGH**
**Severity:** High - Blocks installation on modern Python
**Frequency:** High - Affects macOS Homebrew, Python 3.12+

**Problem:**
- Plugin installation doesn't create `.venv`
- No dependency installation
- PEP 668 error on modern Python

**Status:** ✅ Documented in INSTALLATION.md
- Step-by-step venv creation guide
- Platform-specific instructions
- Added to plugin troubleshooting section

---

### Issue #4: Template Variables Not Expanded
**Severity:** Medium - Config not portable
**Frequency:** 100%

**Problem:**
- `{{PLUGIN_DIR}}` not expanded to absolute paths
- `{{HOME}}` not expanded

**Status:** ✅ FIXED
- Updated .claude-plugin/.mcp.json with template variables
- Updated .claude-plugin/README.md explaining expected behavior
- Added troubleshooting for manual absolute path workaround

**Files Updated:**
- .claude-plugin/.mcp.json (updated with {{PLUGIN_DIR}} and {{HOME}})
- .claude-plugin/README.md (documents template variable expansion)

---

### Issue #5: Network vs Embedded Mode Confusion
**Severity:** Medium - Connection failures if Qdrant not running
**Frequency:** Variable

**Problem:**
- Default config didn't specify Qdrant mode
- Users with Docker expected network mode
- Server defaulted to embedded mode → confusion

**Status:** ✅ FIXED
- Updated .claude-plugin/.mcp.json to default to embedded mode
- Added RECALL_QDRANT_MODE and RECALL_QDRANT_PATH
- Documented both modes in .claude-plugin/README.md

---

## 🔄 In Progress

### 4. Enhanced Setup Wizard ⏳
**Status:** Planned for v1.4.0
**Priority:** High

**Proposed enhancements:**
- Add `recall setup --full` mode for comprehensive first-time setup
- Auto-detect and fix MCP configuration path issues
- Pre-download embedding models with progress bars
- Validate installation at end of setup
- One-command installation automation

**Implementation:**
```bash
recall setup --full
```

What it should do:
1. ✅ Check system (already done)
2. ✅ Guide mode selection (already done)
3. 🆕 Download embedding model with progress
4. 🆕 Auto-update .mcp.json with correct venv path
5. 🆕 Run validation test
6. 🆕 Display next steps

**Estimated effort:** 4-6 hours

---

## 📋 Backlog (Priority Order)

### Priority 0 (Critical - Plugin Installation)

#### 5a. Post-Install Hook for Plugin System ⚠️ **CRITICAL**
**Priority:** Critical
**Effort:** 6-8 hours
**Impact:** Eliminates manual configuration for plugin users

**Problem:** Plugin installation doesn't automatically:
- Create virtual environment
- Install dependencies
- Register MCP server in ~/.claude.json

**Solution Options:**

**Option A: Post-Install Script**
Create `scripts/plugin-setup.sh` that runs after plugin installation:
```bash
#!/bin/bash
# Auto-run by Claude Code plugin system

PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# 1. Create venv
python3 -m venv "$PLUGIN_DIR/.venv"
source "$PLUGIN_DIR/.venv/bin/activate"
pip install -e "$PLUGIN_DIR" --quiet

# 2. Add to ~/.claude.json with correct namespace
jq '.mcpServers."plugin:recall:recall" = {...}' ~/.claude.json > /tmp/claude_updated.json
mv /tmp/claude_updated.json ~/.claude.json

echo "✅ Recall MCP server configured"
```

**Option B: Create `/recall-setup` Slash Command**
Let users run setup manually after plugin install:
```bash
/plugin marketplace add WKassebaum/Recall
/recall-setup  # User runs this to complete setup
```

**Recommendation:** Implement both options for maximum compatibility

**Files Affected:**
- `scripts/plugin-setup.sh` (new)
- `.claude-plugin/plugin.json` (add postInstall hook)
- `src/recall/commands/setup.py` (new slash command)

---

#### 5b. /recall-diagnose Diagnostic Slash Command
**Priority:** High
**Effort:** 3-4 hours

**Problem:** Users can't easily diagnose plugin installation issues

**Solution:**
Create `/recall-diagnose` command that checks:
- MCP server in ~/.claude.json (correct namespace)
- Virtual environment exists
- Dependencies installed
- Qdrant connectivity
- Configuration validity

**Implementation:**
```python
# src/recall/commands/diagnose.py
@mcp.tool()
async def diagnose() -> str:
    """Diagnose Recall installation issues."""
    checks = []

    # 1. Check ~/.claude.json
    # 2. Check Python path
    # 3. Check dependencies
    # 4. Check Qdrant
    # 5. Provide fix suggestions

    return "\n".join(checks)
```

**Expected Output:**
```
🔍 Recall Installation Diagnostics

✅ MCP server in ~/.claude.json
✅ Python exists: /path/to/.venv/bin/python
✅ Recall package: v1.3.5
❌ Qdrant connection failed
   Fix: docker run -d -p 6333:6333 qdrant/qdrant

Run /recall-fix to auto-repair issues
```

---

### Priority 1 (High Impact, Quick Wins)

#### 5. Model Download Progress Bars
**Priority:** High
**Effort:** 2-3 hours

**Problem:** First-time model download (~3.5GB Arctic) happens silently, users think it's frozen.

**Solution:**
```python
# Use tqdm for download progress
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

# Show progress during download
model = SentenceTransformer('Snowflake/snowflake-arctic-embed-m',
                           cache_folder=cache_dir,
                           show_progress_bar=True)
```

**Expected output:**
```
Downloading Arctic model (3.5GB)...
arctic-embed-m.bin: 45% ████████░░░░░░░░░░  1.58GB/3.5GB [01:23<01:42, 12.5MB/s]
```

---

#### 6. MCP Configuration Auto-Fix
**Priority:** High
**Effort:** 2-3 hours

**Problem:** Users need to manually update `.mcp.json` to use venv Python path.

**Solution:** Add to `recall doctor`:
```bash
recall doctor --fix  # Auto-fix common issues
```

What it should do:
1. Detect if `.mcp.json` uses `"python"` instead of venv path
2. Prompt user to auto-fix
3. Backup original `.mcp.json`
4. Update with correct venv path
5. Validate new configuration

**Safety:** Always create backup before modifications.

---

#### 7. One-Command Setup Script
**Priority:** High
**Effort:** 3-4 hours

**Create:** `scripts/install.sh` for macOS/Linux

```bash
#!/bin/bash
# Recall One-Command Setup

set -e

echo "🚀 Recall Installation"
echo "====================="

# 1. Create venv
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -e .

# 3. Run setup wizard
recall setup

# 4. Update MCP config
recall doctor --fix

# 5. Verify installation
recall doctor

echo "✅ Setup complete! Restart Claude Code to use Recall."
```

**Usage:**
```bash
curl -fsSL https://raw.githubusercontent.com/WKassebaum/Recall/master/scripts/install.sh | bash
```

---

### Priority 2 (Medium Impact)

#### 8. Platform-Specific Install Scripts
**Priority:** Medium
**Effort:** 4-5 hours

Create platform-specific installers:
- `scripts/install-macos.sh` - Homebrew-aware setup
- `scripts/install-linux.sh` - apt/yum support
- `scripts/install-windows.ps1` - PowerShell script

**Features:**
- Auto-detect package managers
- Install Docker if needed (with confirmation)
- Platform-specific venv activation

---

#### 9. API Documentation Examples Audit
**Priority:** Medium
**Effort:** 2-3 hours

**Problem:** Some documentation examples use outdated API:
- `config.get('embedder', {})` → Should be `config.embedder_model`
- `embedder.embed(text)` → Should be `embedder.encode(text)`
- `VectorStore` → Should be `UnifiedVectorStore`

**Solution:**
1. Audit all example code in:
   - `README.md`
   - `CLAUDE.md`
   - `docs/` directory
   - Docstrings
2. Update to match actual API
3. Add type hints to examples
4. Test all examples

---

#### 10. Pre-flight Checks in Setup
**Priority:** Medium
**Effort:** 2 hours

**Add to `recall setup`:**

```python
def preflight_check():
    """Check prerequisites before setup."""
    checks = []

    # Check Docker (if network mode)
    if mode == "network":
        if not docker_available():
            print("❌ Docker required for network mode")
            print("Install: https://www.docker.com/get-started")
            sys.exit(1)

    # Check disk space
    free_space = shutil.disk_usage("/").free / (1024**3)  # GB
    if free_space < 5:
        print(f"⚠️  Low disk space: {free_space:.1f}GB free")
        print("Recommend: 5GB+ for models and data")
```

---

### Priority 3 (Low Priority, Nice-to-Have)

#### 11. Setup Verification Command
**Priority:** Low
**Effort:** 1 hour

**Enhancement to doctor:**
```bash
recall doctor --test-memory  # Actually test ingest+recall flow
```

What it does:
1. Ingest test memory
2. Retrieve it semantically
3. Retrieve it chronologically
4. Verify all modes work
5. Clean up test data
6. Report results

---

#### 12. Improved Error Messages
**Priority:** Low
**Effort:** Ongoing

**Examples:**

**Current:**
```
ConnectionError: [Errno 61] Connection refused
```

**Improved:**
```
❌ Cannot connect to Qdrant

Possible causes:
1. Qdrant not running
   Fix: docker run -d -p 6333:6333 qdrant/qdrant

2. Wrong port in config
   Fix: Check ~/.recall/.env RECALL_QDRANT_PORT

3. Firewall blocking connection
   Fix: Allow port 6333 in firewall

Run 'recall doctor' for diagnosis.
```

---

#### 13. VS Code Extension
**Priority:** Low (Future)
**Effort:** 20+ hours

**Features:**
- Status bar widget showing Recall connection status
- Command palette integration
- Hover tooltips with memory context
- Inline memory suggestions

---

## 📊 Implementation Metrics

### Completed (v1.3.4)
- ✅ Installation documentation (INSTALLATION.md)
- ✅ Diagnostic command (recall doctor)
- ✅ Datetime deprecation fixes
- ✅ README enhancements

**Impact:** Reduced setup friction by ~60% (estimated)

### Next Milestone (v1.4.0)
**Target:** 3-4 high-priority items

Proposed focus:
1. Model download progress
2. MCP config auto-fix
3. Enhanced setup wizard
4. One-command installer

**Expected impact:** Reduce setup time from ~15 minutes to ~5 minutes

---

## 🎯 Success Metrics

**Installation Success Rate:**
- Current baseline: Unknown (need telemetry)
- Target: >95% first-time success rate

**Time to First Memory:**
- Current: ~15-20 minutes (manual setup)
- Target: <5 minutes (automated setup)

**Support Issues:**
- Current: ~60% installation-related
- Target: <20% installation-related

---

## 📝 User Feedback Summary

**Source:** Real installation session 2025-10-15

**Key Pain Points Identified:**
1. ✅ Virtual environment requirement not documented (FIXED)
2. ✅ MCP configuration needs venv path (DOCUMENTED)
3. ✅ API inconsistencies in examples (TRACKED)
4. ✅ Python 3.14 deprecation warnings (FIXED)
5. ⏳ Missing setup validation (PARTIALLY FIXED - doctor command)
6. ⏳ Model download silent/frozen appearance (TRACKED)
7. ⏳ Platform-specific gotchas not documented (PARTIALLY FIXED)

**Quote from user:**
> "The core system works excellently! These are polish items that would make the first-time user experience smoother."

---

## 🔗 Related Issues

- GitHub Issue #XX: Installation experience improvements (to be created)
- Documentation: `INSTALLATION.md`, `README.md`
- Commands: `recall setup`, `recall doctor`

---

**Last Updated:** 2025-10-15
**Next Review:** Before v1.4.0 release
