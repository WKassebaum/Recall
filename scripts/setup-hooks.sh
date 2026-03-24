#!/bin/bash
# Setup Recall memory persistence hooks in Claude Code settings
#
# This script registers SessionStart, SessionEnd, PreCompact, and PostToolUse
# hooks that automate memory save/retrieve across Claude Code sessions.
#
# Usage:
#   ./scripts/setup-hooks.sh              # Auto-detect entry point location
#   ./scripts/setup-hooks.sh --uninstall  # Remove hooks from settings
#
# Prerequisites:
#   - pip install semantic-recall (or pip install -e . for development)
#   - jq (for JSON manipulation)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CLAUDE_SETTINGS="$HOME/.claude/settings.json"

# --- Uninstall mode ---
if [ "$1" = "--uninstall" ]; then
    echo -e "${BLUE}Removing Recall hooks from Claude Code settings...${NC}"
    if [ ! -f "$CLAUDE_SETTINGS" ]; then
        echo -e "${YELLOW}No settings.json found — nothing to remove${NC}"
        exit 0
    fi
    if ! command -v jq &>/dev/null; then
        echo -e "${RED}jq required for uninstall. Install: brew install jq${NC}"
        exit 1
    fi
    # Remove our hook entries
    jq 'del(.hooks.SessionStart) | del(.hooks.SessionEnd) | del(.hooks.PreCompact) |
        .hooks.PostToolUse = [.hooks.PostToolUse[]? | select(.matcher != "Bash|mcp__recall__ingest_memory")]' \
        "$CLAUDE_SETTINGS" > /tmp/claude_settings_clean.json && \
        mv /tmp/claude_settings_clean.json "$CLAUDE_SETTINGS"
    echo -e "${GREEN}Recall hooks removed from settings.json${NC}"
    exit 0
fi

# --- Install mode ---
echo -e "${BLUE}🧠 Recall Memory Persistence Hooks Setup${NC}"
echo ""

# Step 1: Find the hook entry points
echo -e "${BLUE}[1/3] Locating hook entry points...${NC}"
HOOK_CMD=""

# Try 1: Check if recall-session-start is on PATH (pip install)
if command -v recall-session-start &>/dev/null; then
    HOOK_CMD="recall-session-start"
    HOOK_PREFIX=""
    echo -e "${GREEN}✅ Found hooks on PATH (global install)${NC}"

# Try 2: Check local venv
elif [ -f "./venv/bin/recall-session-start" ]; then
    HOOK_PREFIX="$(pwd)/venv/bin/"
    HOOK_CMD="${HOOK_PREFIX}recall-session-start"
    echo -e "${GREEN}✅ Found hooks in local venv${NC}"

# Try 3: Check .venv (plugin convention)
elif [ -f "./.venv/bin/recall-session-start" ]; then
    HOOK_PREFIX="$(pwd)/.venv/bin/"
    HOOK_CMD="${HOOK_PREFIX}recall-session-start"
    echo -e "${GREEN}✅ Found hooks in .venv${NC}"

else
    echo -e "${RED}❌ Hook entry points not found${NC}"
    echo -e "${YELLOW}Run: pip install semantic-recall  (or pip install -e . for development)${NC}"
    exit 1
fi

# Verify all 4 hooks exist
for hook in recall-session-start recall-session-end recall-pre-compact recall-milestone-hook; do
    if [ -n "$HOOK_PREFIX" ]; then
        FULL="${HOOK_PREFIX}${hook}"
    else
        FULL="$hook"
    fi
    if ! command -v "$FULL" &>/dev/null && [ ! -f "$FULL" ]; then
        echo -e "${RED}❌ Missing hook: $FULL${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ All 4 hooks verified${NC}"

# Step 2: Check jq
echo ""
echo -e "${BLUE}[2/3] Checking dependencies...${NC}"
if ! command -v jq &>/dev/null; then
    echo -e "${RED}❌ jq not found — required for settings.json modification${NC}"
    echo -e "${YELLOW}Install: brew install jq (macOS) or apt install jq (Linux)${NC}"
    echo ""
    echo -e "${YELLOW}Manual setup — add these to ~/.claude/settings.json hooks section:${NC}"
    echo ""
    echo "  SessionStart, SessionEnd, PreCompact: ${HOOK_PREFIX}recall-session-start (etc.)"
    echo "  PostToolUse matcher Bash|mcp__recall__ingest_memory: ${HOOK_PREFIX}recall-milestone-hook"
    exit 2
fi
echo -e "${GREEN}✅ jq available${NC}"

# Step 3: Register hooks
echo ""
echo -e "${BLUE}[3/3] Registering hooks in ~/.claude/settings.json...${NC}"

# Backup
if [ -f "$CLAUDE_SETTINGS" ]; then
    cp "$CLAUDE_SETTINGS" "$CLAUDE_SETTINGS.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}✅ Backed up existing settings${NC}"
else
    mkdir -p "$(dirname "$CLAUDE_SETTINGS")"
    echo '{}' > "$CLAUDE_SETTINGS"
fi

# Build hook command paths
CMD_START="${HOOK_PREFIX}recall-session-start"
CMD_END="${HOOK_PREFIX}recall-session-end"
CMD_COMPACT="${HOOK_PREFIX}recall-pre-compact"
CMD_MILESTONE="${HOOK_PREFIX}recall-milestone-hook"

# Add hooks using jq
jq --arg start "$CMD_START" \
   --arg end "$CMD_END" \
   --arg compact "$CMD_COMPACT" \
   --arg milestone "$CMD_MILESTONE" '
  .hooks //= {} |
  .hooks.SessionStart = [{
    "hooks": [{"type": "command", "command": $start, "timeout": 5}]
  }] |
  .hooks.SessionEnd = [{
    "hooks": [{"type": "command", "command": $end, "timeout": 5}]
  }] |
  .hooks.PreCompact = [{
    "hooks": [{"type": "command", "command": $compact, "timeout": 5}]
  }] |
  .hooks.PostToolUse = (.hooks.PostToolUse // []) + [{
    "matcher": "Bash|mcp__recall__ingest_memory",
    "hooks": [{"type": "command", "command": $milestone, "timeout": 3}]
  }]
' "$CLAUDE_SETTINGS" > /tmp/claude_settings_hooks.json

if [ $? -eq 0 ]; then
    mv /tmp/claude_settings_hooks.json "$CLAUDE_SETTINGS"
    echo -e "${GREEN}✅ Hooks registered${NC}"
else
    echo -e "${RED}❌ Failed to update settings${NC}"
    rm -f /tmp/claude_settings_hooks.json
    exit 1
fi

# Summary
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Recall Memory Persistence Hooks Installed!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}What happens now:${NC}"
echo -e "  • ${YELLOW}SessionStart${NC}: Recalls previous session context automatically"
echo -e "  • ${YELLOW}PreCompact${NC}: Prompts saving before context compression"
echo -e "  • ${YELLOW}SessionEnd${NC}: Captures session summary for next time"
echo -e "  • ${YELLOW}Milestones${NC}: Logs git commits and test runs as breadcrumbs"
echo ""
echo -e "${BLUE}Restart Claude Code to activate hooks.${NC}"
echo ""
echo -e "To remove: ${YELLOW}./scripts/setup-hooks.sh --uninstall${NC}"
echo ""
