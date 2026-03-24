#!/bin/bash
# Recall Plugin Post-Install Setup
#
# This script runs automatically after plugin installation via Claude Code's
# plugin system. It automates:
# 1. Virtual environment creation
# 2. Dependency installation
# 3. MCP server registration in ~/.claude.json
#
# Exit codes:
#   0 - Success
#   1 - Fatal error (installation failed)
#   2 - Partial success (manual steps required)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detect plugin directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}🚀 Recall Plugin Setup${NC}"
echo -e "${BLUE}======================${NC}"
echo ""
echo "Plugin directory: $PLUGIN_DIR"
echo ""

# Step 1: Check Python version
echo -e "${BLUE}[1/5] Checking Python version...${NC}"
PYTHON_CMD=""

# Try python3 first
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        PYTHON_CMD="python3"
        echo -e "${GREEN}✅ Found Python $PYTHON_VERSION${NC}"
    fi
fi

# Fallback to python
if [ -z "$PYTHON_CMD" ] && command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        PYTHON_CMD="python"
        echo -e "${GREEN}✅ Found Python $PYTHON_VERSION${NC}"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}❌ Python 3.10+ not found${NC}"
    echo -e "${YELLOW}Please install Python 3.10 or later: https://www.python.org/downloads/${NC}"
    exit 1
fi

# Step 2: Create virtual environment
echo ""
echo -e "${BLUE}[2/5] Creating virtual environment...${NC}"

if [ -d "$PLUGIN_DIR/.venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment already exists, skipping${NC}"
else
    cd "$PLUGIN_DIR"
    $PYTHON_CMD -m venv .venv

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Virtual environment created${NC}"
    else
        echo -e "${RED}❌ Failed to create virtual environment${NC}"
        exit 1
    fi
fi

# Step 3: Install dependencies
echo ""
echo -e "${BLUE}[3/5] Installing dependencies...${NC}"
echo -e "${YELLOW}(This may take 30-60 seconds)${NC}"

cd "$PLUGIN_DIR"
source .venv/bin/activate

# Upgrade pip first
pip install --upgrade pip --quiet

# Install package in editable mode
if pip install -e . --quiet; then
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${RED}❌ Failed to install dependencies${NC}"
    echo -e "${YELLOW}Try manually: cd $PLUGIN_DIR && source .venv/bin/activate && pip install -e .${NC}"
    exit 1
fi

# Verify installation
if python -c "import recall; print(f'Recall v{recall.__version__}')" 2>/dev/null; then
    RECALL_VERSION=$(python -c "import recall; print(recall.__version__)")
    echo -e "${GREEN}✅ Recall $RECALL_VERSION installed${NC}"
else
    echo -e "${RED}❌ Recall package verification failed${NC}"
    exit 1
fi

# Step 4: Configure MCP server in ~/.claude.json
echo ""
echo -e "${BLUE}[4/5] Configuring MCP server...${NC}"

CLAUDE_CONFIG="$HOME/.claude.json"

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠️  jq not found - cannot auto-configure MCP server${NC}"
    echo -e "${YELLOW}Please manually add to ~/.claude.json:${NC}"
    echo ""
    echo "{"
    echo "  \"mcpServers\": {"
    echo "    \"plugin:recall:recall\": {"
    echo "      \"command\": \"$PLUGIN_DIR/.venv/bin/python\","
    echo "      \"args\": [\"-m\", \"recall.mcp.server\"],"
    echo "      \"env\": {"
    echo "        \"PYTHONPATH\": \"$PLUGIN_DIR/src\","
    echo "        \"RECALL_CONFIG\": \"$PLUGIN_DIR/config.yaml\","
    echo "        \"RECALL_QDRANT_MODE\": \"embedded\","
    echo "        \"RECALL_QDRANT_PATH\": \"$HOME/.recall/qdrant\""
    echo "      }"
    echo "    }"
    echo "  }"
    echo "}"
    echo ""
    exit 2  # Partial success
fi

# Backup existing config
if [ -f "$CLAUDE_CONFIG" ]; then
    cp "$CLAUDE_CONFIG" "$CLAUDE_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}✅ Backed up existing ~/.claude.json${NC}"
fi

# Create or update config
if [ ! -f "$CLAUDE_CONFIG" ]; then
    # Create new config
    cat > "$CLAUDE_CONFIG" <<EOF
{
  "mcpServers": {}
}
EOF
fi

# Add Recall MCP server configuration
jq --arg dir "$PLUGIN_DIR" \
   --arg home "$HOME" \
   '.mcpServers."plugin:recall:recall" = {
     "command": ($dir + "/.venv/bin/python"),
     "args": ["-m", "recall.mcp.server"],
     "env": {
       "PYTHONPATH": ($dir + "/src"),
       "RECALL_CONFIG": ($dir + "/config.yaml"),
       "RECALL_QDRANT_MODE": "embedded",
       "RECALL_QDRANT_PATH": ($home + "/.recall/qdrant")
     }
   }' "$CLAUDE_CONFIG" > /tmp/claude_updated.json

if [ $? -eq 0 ]; then
    mv /tmp/claude_updated.json "$CLAUDE_CONFIG"
    echo -e "${GREEN}✅ MCP server configured in ~/.claude.json${NC}"
else
    echo -e "${RED}❌ Failed to update ~/.claude.json${NC}"
    rm -f /tmp/claude_updated.json
    exit 1
fi

# Step 5: Verify MCP server configuration
echo ""
echo -e "${BLUE}[5/5] Verifying MCP server configuration...${NC}"

if jq -e '.mcpServers."plugin:recall:recall"' "$CLAUDE_CONFIG" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ MCP server registration verified${NC}"
else
    echo -e "${RED}❌ MCP server not found in ~/.claude.json${NC}"
    exit 1
fi

# Step 6: Install memory persistence hooks (optional)
echo ""
echo -e "${BLUE}[6/6] Setting up memory persistence hooks...${NC}"

if command -v jq &> /dev/null; then
    if [ -f "$PLUGIN_DIR/scripts/setup-hooks.sh" ]; then
        bash "$PLUGIN_DIR/scripts/setup-hooks.sh" && \
            echo -e "${GREEN}✅ Memory persistence hooks installed${NC}" || \
            echo -e "${YELLOW}⚠️  Hook setup skipped (non-critical)${NC}"
    else
        echo -e "${YELLOW}⚠️  Hook setup script not found — skipping${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  jq not installed — hooks require manual setup${NC}"
    echo -e "${YELLOW}   Install jq, then run: $PLUGIN_DIR/scripts/setup-hooks.sh${NC}"
fi

# Success summary
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Recall Plugin Setup Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo ""
echo -e "1. ${YELLOW}Configure storage mode:${NC}"
echo -e "   ${BLUE}recall setup${NC}"
echo ""
echo -e "2. ${YELLOW}Restart Claude Code:${NC}"
echo -e "   - Quit completely (Cmd/Ctrl + Q)"
echo -e "   - Relaunch Claude Code"
echo ""
echo -e "3. ${YELLOW}Verify installation:${NC}"
echo -e "   ${BLUE}/mcp${NC}"
echo -e "   Should show: ${GREEN}plugin:recall:recall${NC} with 3 tools"
echo ""
echo -e "4. ${YELLOW}Optional - Run diagnostics:${NC}"
echo -e "   ${BLUE}recall doctor${NC}"
echo ""
echo -e "${BLUE}Documentation:${NC}"
echo -e "  • Installation: $PLUGIN_DIR/INSTALLATION.md"
echo -e "  • Usage Guide: $PLUGIN_DIR/CLAUDE.md"
echo -e "  • Troubleshooting: $PLUGIN_DIR/INSTALLATION.md#plugin-installation-troubleshooting"
echo ""

exit 0
