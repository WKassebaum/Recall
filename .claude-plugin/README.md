# Recall Plugin Configuration

This directory contains plugin-specific configuration for Claude Code's plugin system.

## Files

- **`.mcp.json`** - MCP server configuration template for plugin installation

## Expected Plugin Installation Behavior

When a user runs `/plugin marketplace add WKassebaum/Recall`, Claude Code's plugin system should:

1. ✅ Clone repository to plugin directory
2. ✅ Create virtual environment: `{{PLUGIN_DIR}}/.venv`
3. ✅ Install dependencies: `pip install -e .`
4. ✅ Parse `.claude-plugin/.mcp.json`
5. ✅ Expand template variables:
   - `{{PLUGIN_DIR}}` → Absolute path to plugin directory
   - `{{HOME}}` → User's home directory
6. ✅ Add to `~/.claude.json` with namespace: `plugin:recall:recall`
7. ✅ Restart MCP connection
8. ✅ Plugin ready to use

## Template Variables

The `.mcp.json` file uses template variables that should be expanded during installation:

- `{{PLUGIN_DIR}}` - Absolute path to Recall plugin directory
- `{{HOME}}` - User's home directory path

**Example Expansion:**
```json
{
  "command": "{{PLUGIN_DIR}}/.venv/bin/python"
}
```

Becomes:
```json
{
  "command": "/Users/username/.claude/plugins/recall@Recall/.venv/bin/python"
}
```

## MCP Server Namespace

**Important:** When added to `~/.claude.json`, the server key becomes namespaced:

- **Template key:** `"recall"`
- **Installed key:** `"plugin:recall:recall"`

This is handled automatically by Claude Code's plugin system.

## Configuration Details

### Command
`{{PLUGIN_DIR}}/.venv/bin/python`

Uses virtual environment Python to avoid:
- PEP 668 externally-managed-environment errors
- Global Python package pollution
- Dependency conflicts

### Environment Variables

- **`PYTHONPATH`** - Points to source directory for imports
- **`RECALL_CONFIG`** - Path to config.yaml
- **`RECALL_QDRANT_MODE`** - Vector database mode
  - `embedded` (default) - Local file storage, no Docker required
  - `network` - Docker Qdrant server (advanced)
- **`RECALL_QDRANT_PATH`** - Storage location for embedded mode

## Embedded Mode (Default)

**Recommended for plugin installations** - simpler setup, no dependencies.

- **Storage:** `~/.recall/qdrant/` (auto-created)
- **Requirements:** None (just disk space)
- **Pros:** Works offline, simple setup
- **Cons:** Not shared across systems

## Network Mode (Advanced)

For users who want shared storage across multiple systems.

- **Storage:** Docker Qdrant server
- **Requirements:** Docker Desktop/Engine
- **Pros:** Shared, better performance at scale
- **Cons:** Requires Docker, network dependency

**To use network mode:**
```bash
# Start Qdrant
docker run -d -p 6333:6333 qdrant/qdrant

# Update environment variables in ~/.claude.json
"RECALL_QDRANT_MODE": "network",
"RECALL_QDRANT_HOST": "localhost",
"RECALL_QDRANT_PORT": "6333"
```

## Troubleshooting

### "Failed to reconnect to plugin:recall:recall"

**Cause:** MCP server configuration not added to `~/.claude.json`

**Fix:**
1. Check if configuration exists:
   ```bash
   cat ~/.claude.json | jq '.mcpServers."plugin:recall:recall"'
   ```

2. If null/empty, manual configuration required (see INSTALLATION.md)

### Virtual Environment Not Created

**Cause:** Plugin system didn't create `.venv` automatically

**Fix:**
```bash
cd /path/to/Recall
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Template Variables Not Expanded

**Cause:** Claude Code plugin system didn't expand `{{PLUGIN_DIR}}`

**Fix:** Manually edit `~/.claude.json` with absolute paths (see INSTALLATION.md)

## Manual Installation Fallback

If automatic plugin installation fails, see comprehensive manual installation guide in:

- **[INSTALLATION.md](../INSTALLATION.md)** - Step-by-step platform-specific instructions
- **[README.md](../README.md)** - Quick start guide

## Known Issues

**As of v1.4.1, automatic plugin installation may not work due to:**

1. MCP server not auto-registered in `~/.claude.json`
2. Virtual environment not auto-created
3. Template variables not expanded
4. No post-install hooks executed

**Workaround:** Use manual installation (see INSTALLATION.md)

**Status:** Investigating with Claude Code team for plugin system enhancements

## Support

- **Issues:** [GitHub Issues](https://github.com/WKassebaum/Recall/issues)
- **Installation Help:** See INSTALLATION.md
- **Troubleshooting:** Run `recall doctor` for diagnostics
