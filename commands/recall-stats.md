# View Recall Statistics

Quick health check and statistics for Recall memory system.

## Usage

`/recall-stats`

## What It Does

Displays current status and configuration:

- Total memories stored
- Active embedding model and dimension
- Active collection name
- Qdrant connection details

## Example Output

```
📊 Recall Statistics:
Total chunks: 42
Active collection: recall_1024d
Embedder: snowflake-arctic-embed-m
Dimension: 1024D
Qdrant: localhost:6333
```

## When to Use

- **Quick health check** - Verify Recall is working
- **Before storing** - Confirm correct model active
- **Debugging** - Check configuration
- **Usage monitoring** - Track memory growth

## Interpreting Results

**Total chunks:**
- Shows number of memories stored across all sessions
- Each ingested content may become multiple chunks
- Growth indicates active usage

**Active collection:**
- Format: `recall_<dimension>d`
- `recall_384d` - MiniLM or BGE models
- `recall_768d` - Nomic model
- `recall_1024d` - Arctic model (default)

**Embedder:**
- Current model being used for new memories
- Primary: `snowflake-arctic-embed-m` (87% accuracy)
- Fallback: `all-MiniLM-L6-v2` (78.1% accuracy)

**Dimension:**
- Embedding vector size
- Must match collection dimension
- Higher ≠ better (model-specific)

**Qdrant:**
- Vector database connection
- Should show `localhost:6333` (default)
- If different, check config.yaml

## Troubleshooting

**"No matching memories found" when should have results:**
- Wrong collection might be active
- Use `/recall-setup` to reinitialize

**Collection doesn't match embedder:**
- Dimension mismatch error likely
- Run `/recall-setup` to sync

**Total chunks = 0 after storing:**
- Check Qdrant is running: `curl localhost:6333`
- Verify storage with `/recall-search test`

## Related Commands

- `/recall-setup` - Full setup and validation
- `/recall-search` - Search stored memories
- `/recall-timeline` - View chronological history
