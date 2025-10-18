#!/bin/bash
# Sync version from src/recall/__init__.py to .claude-plugin/plugin.json
# This ensures a single source of truth for version numbers

set -e

# Get version from Python package
VERSION=$(python3 -c "import sys; sys.path.insert(0, 'src'); from recall import __version__; print(__version__)")

# Update plugin.json
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" .claude-plugin/plugin.json
else
    # Linux
    sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" .claude-plugin/plugin.json
fi

echo "✅ Synced version $VERSION to .claude-plugin/plugin.json"
