# Setup and Verify Recall

Initialize Recall and verify everything is working correctly.

## Usage

`/recall-setup`

## What It Does

Performs comprehensive setup and validation:

1. **Checks Qdrant** - Verifies vector database is running
2. **Loads Embedding Model** - Downloads Arctic model if needed (~3.5GB first time)
3. **Creates Collections** - Initializes dimension-specific collections
4. **Stores Test Memory** - Validates ingestion pipeline
5. **Retrieves Test Memory** - Validates search pipeline
6. **Reports Status** - Shows configuration and performance metrics

## First-Time Setup

On first run, this command will:
- Download `snowflake/arctic-embed-m` from HuggingFace (~3.5GB)
- Takes 30-60 seconds on good connection
- Model cached to `~/.cache/huggingface/` for future use
- Progress logged to stderr

## What You'll See

```
🔧 Recall Setup & Validation

✅ Qdrant running at localhost:6333
⏳ Loading embedding model (first time: downloading ~3.5GB)...
✅ Embedding model loaded: snowflake-arctic-embed-m (1024D)
✅ Collections initialized: recall_1024d
✅ Test memory stored: chunk_test_abc123
✅ Test memory retrieved (score: 1.000)
✅ All systems operational

📊 Configuration:
- Embedder: snowflake-arctic-embed-m
- Dimension: 1024D
- Active collection: recall_1024d
- Total chunks: 1
- Qdrant: localhost:6333

⚡ Performance:
- Query latency: 17.5ms (target: <500ms)
- Embedding time: 35ms

🎉 Recall is ready to use!

Try:
- /recall-store - Store a memory
- /recall-search <query> - Search memories
- /recall-stats - View statistics
```

## When to Use

- **First installation** - Verify everything works
- **After updates** - Confirm new version working
- **Troubleshooting** - Diagnose configuration issues
- **Pre-download models** - Avoid delays on first real use

## Troubleshooting

**Qdrant not running:**
```bash
docker run -d -p 6333:6333 qdrant/qdrant
```

**Model download fails:**
- Check internet connection
- Verify HuggingFace is accessible
- Check disk space (~3.5GB needed)
- Model will auto-fallback to MiniLM (smaller, 1.2GB)

**Permission errors:**
- Ensure `~/.cache/huggingface/` is writable
- Check Python virtual environment activated

## Related Commands

- `/recall-stats` - Quick health check
- `/recall-store` - Store a memory
- `/recall-search` - Search memories
