# Phase 2: Chunking Strategy Analysis

## Research Findings from CodeIndex

### CodeIndex's Multi-Strategy Approach

**Three chunking strategies:**
1. **SimpleCodeSplitter**: Line-based with overlap (2500 chars, 300 overlap)
2. **SimpleASTCodeSplitter**: Regex-based semantic chunking
3. **TreeSitterCodeSplitter**: Full AST-based chunking

**Supported content types:**
- Code: TypeScript, JavaScript, Python, Java, Go, Rust, C/C++, C#, PHP, Ruby, Swift, Kotlin, Scala
- Markup: Markdown, HTML, XML
- Data: JSON, YAML
- Styles: CSS, SCSS, LESS
- Other: SQL, Bash

**Key features:**
- Token limit awareness (7500 tokens for 8192 embedding limit)
- Semantic boundary detection (classes, functions, methods)
- Fallback strategies for unsupported languages
- Overlap for context preservation

## SemVecMem's Actual Use Case

**Per PRD: "Semantic memory for coding agents"**

### Content Types We'll Actually Store

1. **Code Snippets** (40% estimated)
   - Functions, classes, methods from agent sessions
   - Multiple languages: Python, TypeScript, JavaScript, etc.
   - Example: "I wrote this authentication function..."

2. **Session Notes/Descriptions** (30% estimated)
   - Prose descriptions of what was done
   - Decision rationale
   - Example: "We decided to use Redis for session storage because..."

3. **Structured Data** (20% estimated)
   - JSON payloads (tool parameters, API responses)
   - Configuration snippets
   - Example: `{"tool": "search_codebase", "query": "auth", "results": [...]}`

4. **Documentation** (10% estimated)
   - Markdown notes
   - Code comments with context
   - Example: "## How the OAuth Flow Works..."

## Problem with Current Implementation

**Current state:** Tree-sitter Python chunker only
- ✅ Great for Python code
- ❌ No support for prose/descriptions
- ❌ No support for JSON/YAML
- ❌ No support for other languages
- ❌ No support for Markdown

**This won't work** for a memory system that stores:
- "We used approach X because Y" (prose)
- Tool call results (JSON)
- Multi-language code snippets
- Documentation/notes (Markdown)

## Recommended Phase 2 Architecture

### Multi-Strategy Chunker Factory

```python
class ChunkerFactory:
    """Factory for content-type appropriate chunkers."""

    @staticmethod
    def get_chunker(content_type: str) -> Chunker:
        if content_type == "code":
            return ASTCodeChunker()  # Multiple languages
        elif content_type == "text":
            return ProseChunker()     # NLTK sentences
        elif content_type == "json":
            return JSONChunker()      # Structured data
        elif content_type == "markdown":
            return MarkdownChunker()  # Preserve structure
        else:
            return SimpleChunker()    # Fallback
```

### Priority Implementation Order

**Waypoint 8-10 (Phase 2 - Enhanced Chunking):**

1. **Waypoint 8A: Prose/Text Chunker** (HIGHEST PRIORITY)
   - NLTK sentence splitter
   - Paragraph-aware splitting
   - Overlap for context
   - **Rationale:** Most agent memory will be descriptions/notes

2. **Waypoint 8B: JSON/YAML Chunker** (HIGH PRIORITY)
   - Keep structured data intact when small
   - Split by top-level keys when large
   - Preserve valid JSON structure
   - **Rationale:** Tool calls, API responses, config snippets

3. **Waypoint 8C: Markdown Chunker** (MEDIUM PRIORITY)
   - Respect headers as boundaries
   - Keep code blocks intact
   - Section-aware splitting
   - **Rationale:** Documentation, notes, explanations

4. **Waypoint 8D: Multi-Language AST Chunker** (LOWER PRIORITY)
   - Adapt CodeIndex SimpleASTCodeSplitter patterns
   - Support TypeScript, JavaScript, Go, Rust, etc.
   - **Rationale:** Code snippets from various languages

## Recommendation: Don't Backtrack

**We don't need to backtrack!** Our Python chunker is solid and we'll keep it.

**Instead, we'll ADD:**
1. ProseChunker (NLTK-based) - NEW, not replacing anything
2. JSONChunker (structural) - NEW, not replacing anything
3. MarkdownChunker (section-aware) - NEW, not replacing anything
4. Enhance ASTCodeChunker to support more languages (TreeSitter patterns)

**Architecture:**
```python
# Main ingestion API - auto-detects content type
store.ingest(
    content="We decided to use Redis...",
    content_type="text"  # or auto-detect
)

# Internally routes to appropriate chunker
chunker = ChunkerFactory.get_chunker("text")  # ProseChunker
chunks = chunker.chunk(content)
```

## Implementation Plan (Phase 2 Revised)

### Day 2.1: Prose Chunker (Waypoint 8A)
- NLTK sentence splitter
- Paragraph detection
- Overlap handling
- Tests: Various text formats

### Day 2.2: JSON Chunker (Waypoint 8B)
- JSON parsing and validation
- Smart splitting (top-level keys)
- Preserve structure
- Tests: API responses, configs

### Day 2.3: Markdown Chunker (Waypoint 8C)
- Header-based splitting
- Code block preservation
- Section awareness
- Tests: READMEs, documentation

### Day 2.4: Multi-Language AST Enhancement (Waypoint 8D)
- Add TypeScript/JavaScript patterns
- Add Go, Rust patterns (optional)
- Unified interface
- Tests: Multi-language code

### Day 2.5: Chunker Factory & Integration (Waypoint 9)
- Factory pattern implementation
- Auto-detection logic
- Integration with UnifiedVectorStore
- End-to-end tests

### Day 2.6: MCP Server Basics (Waypoint 10-11)
- FastMCP server skeleton
- Basic tools: ingest_memory, recall_memory
- Configuration integration
- Agent testing

## Quality Gates (Same as Phase 1)

- ✅ Test coverage ≥80%
- ✅ Cyclomatic complexity ≤6 (chunkers), ≤8 (factory)
- ✅ Type safety (mypy strict)
- ✅ All tests passing
- ✅ Maintainability Index ≥B

## Decision

**Proceed with multi-strategy chunker approach**
- Keep existing Python chunker
- Add prose, JSON, Markdown chunkers
- Factory pattern for content-type routing
- No backtracking required

**Benefits:**
- Matches actual use case (agent memory = mixed content)
- Leverages CodeIndex patterns (proven architecture)
- Incremental implementation (add chunkers one by one)
- Backwards compatible (existing Python chunker still works)

**Next Step:** Implement ProseChunker (Waypoint 8A) as highest priority
