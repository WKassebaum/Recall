# Search Recall Memory (Semantic)

Search your external memory by meaning using vector similarity.

## Usage

`/recall-search <query> [--session <session-id>] [--top-k <number>]`

## What It Does

Performs semantic search across your stored memories, returning the most relevant results ranked by similarity score.

## Examples

**Basic search:**
```
/recall-search embedding model decisions
```

**Search within specific session:**
```
/recall-search authentication issues --session phase3
```

**Get more results:**
```
/recall-search debugging attempts --top-k 10
```

## Parameters

- `<query>` (required): What you're looking for (by meaning, not exact match)
- `--session <session-id>`: Filter to specific session
- `--top-k <number>`: Number of results to return (default: 5)

## How It Works

1. Converts your query to an embedding vector
2. Compares against all stored memories using cosine similarity
3. Returns top matches ranked by relevance score
4. Shows scores (0.0-1.0, higher = more relevant)

## When to Use

- **"What did we decide about X?"** - Find decisions by topic
- **"How did we solve Y?"** - Find solutions by problem domain
- **"What have we learned about Z?"** - Find discoveries by theme
- **"Remind me about..."** - Retrieve context by meaning

## Tips

- Be descriptive in queries (not just keywords)
- Use natural language: "how we handled authentication" > "auth"
- Session filtering reduces noise for focused projects
- Scores above 0.7 are typically very relevant

## Related Commands

- `/recall-timeline` - Search by time instead of meaning
- `/recall-hybrid` - Combine semantic + temporal search
