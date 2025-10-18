#!/bin/bash
# Test skill structure and validate YAML frontmatter

set -e

SKILL_DIR="$HOME/.claude/skills/recall-memory-skill"

echo "🔍 Testing Recall Memory Skill Structure..."
echo

# Check directory exists
if [ ! -d "$SKILL_DIR" ]; then
    echo "❌ Skill directory not found: $SKILL_DIR"
    exit 1
fi
echo "✅ Skill directory exists: $SKILL_DIR"

# Check SKILL.md exists
if [ ! -f "$SKILL_DIR/SKILL.md" ]; then
    echo "❌ SKILL.md not found"
    exit 1
fi
echo "✅ SKILL.md found"

# Check YAML frontmatter
if ! head -1 "$SKILL_DIR/SKILL.md" | grep -q "^---$"; then
    echo "❌ SKILL.md missing YAML frontmatter opening (---)"
    exit 1
fi
echo "✅ YAML frontmatter opening found"

# Check for name field
if ! grep -q "^name:" "$SKILL_DIR/SKILL.md"; then
    echo "❌ SKILL.md missing 'name:' field in frontmatter"
    exit 1
fi
echo "✅ 'name' field found in frontmatter"

# Check for description field
if ! grep -q "^description:" "$SKILL_DIR/SKILL.md"; then
    echo "❌ SKILL.md missing 'description:' field in frontmatter"
    exit 1
fi
echo "✅ 'description' field found in frontmatter"

# Check examples.md exists
if [ ! -f "$SKILL_DIR/examples.md" ]; then
    echo "⚠️  examples.md not found (optional but recommended)"
else
    echo "✅ examples.md found"
fi

echo
echo "✅ All skill structure checks passed!"
echo
echo "📋 Skill Files:"
ls -lh "$SKILL_DIR"
echo
echo "📏 Skill Size:"
echo "  SKILL.md: $(wc -l < "$SKILL_DIR/SKILL.md") lines"
echo "  examples.md: $(wc -l < "$SKILL_DIR/examples.md") lines"
echo
echo "🔄 To load the skill:"
echo "  1. Restart Claude Code (Cmd/Ctrl + Q, then relaunch)"
echo "  2. The skill will be auto-discovered on startup"
echo "  3. Claude will use it automatically when working with Recall"
