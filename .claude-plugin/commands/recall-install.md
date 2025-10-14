# Install Recall Dependencies

Install Python dependencies required for Recall to function.

**Tasks to perform:**

1. Determine the plugin directory location using the marker file
2. Install dependencies using pip:

```bash
# Navigate to plugin directory (should be in ~/.claude/plugins/recall@Recall/)
PLUGIN_DIR=$(find ~/.claude/plugins -type d -name "recall@*" 2>/dev/null | head -1)

if [ -z "$PLUGIN_DIR" ]; then
    echo "❌ Plugin directory not found. Is the plugin installed?"
    exit 1
fi

echo "📦 Installing Recall dependencies from: $PLUGIN_DIR"

# Install dependencies including MCP optional dependency
cd "$PLUGIN_DIR" && pip install -e ".[mcp]"

echo "✅ Dependencies installed successfully!"
echo ""
echo "Next steps:"
echo "1. Restart Claude Code to reload the MCP server"
echo "2. Run /recall-setup to verify installation"
```

**What gets installed:**
- qdrant-client (vector database)
- sentence-transformers (embeddings)
- mcp (Model Context Protocol)
- tree-sitter (AST parsing)
- And 8 other required packages

**After installation:**
- Restart Claude Code: `Cmd/Ctrl + Q`
- Verify with: `/recall-setup`

**Note:** This is a one-time setup. Dependencies persist across Claude Code restarts.
