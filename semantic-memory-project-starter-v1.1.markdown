# Semantic Vector Memory for Coding Agents: Project Starter Kit (v1.1)

*Download Instructions:* Save this file as `semantic-memory-project-starter-v1.1.md` in your project’s top-level folder (e.g., `semvecmem/`). Use it alongside your CodeIndex repo (e.g., clone or symlink `/Users/wrk/WorkDev/MCP-Dev/claude-codeindex` or `https://github.com/WKassebaum/codeindex` for reference). Links to templates/tools are included for setup.

---

## Executive Summary
This document defines **SemVecMem** (Semantic Vector Memory) v1.1, a long-term memory system for coding agents (e.g., Claude Code CLI, Grok CLI) to address context window limitations. It uses vector embeddings for fuzzy, semantic retrieval of past sessions, code snippets, and decisions, integrated via Model Context Protocol (MCP) for low-overhead access.

**Key Updates from v1.0:**
- **Embedding Models:** Configurable support for three contenders: `all-MiniLM-L6-v2` (default; lightweight/local), `bge-small-en-v1.5` (higher accuracy/local), and `text-embedding-3-small` (OpenAI; premium accuracy/cloud-based). Select via config file (YAML/ENV vars).
- **Vector DB:** Qdrant (leverages CodeIndex experience). Auto-detect running instance (e.g., via docker.desktop) or prompt user to set up (Docker Compose).
- **CodeIndex as Resource:** Adapt structure (monorepo with `src/`, `tests/`), FastMCP integration (tool schemas/handlers), Simplified AST parser (`chunker.py`), configuration (YAML with env fallbacks), and MCP usage patterns (async tool calls).
- **Target AI Assistants:** Claude Sonnet-3.5/4.5, Grok-Code-Fast-1, Grok-4-Fast.
- **Other:** Setup script for Qdrant detection/setup; embedding benchmarks.

**Target Users:** Developers building/extending coding agents. Drop this file in your project root and run the provided setup script (generated via prompt) to bootstrap.

---

## Product Requirements Document (PRD) - Updated

### 1. Product Overview
**Name:** SemVecMem  
**Version:** 1.1 (MVP with Configurable Embeddings)  
**Description:** A semantic vector database backend for coding agents, enabling fuzzy retrieval of long-term memories. Memories are chunked via AST-aware parsing (adapted from CodeIndex), embedded with configurable models, and queried via cosine similarity. Exposed as an MCP server using FastMCP (mirroring CodeIndex patterns).  
**Problem Solved:** LLMs forget due to context compression; brittle key-based memories fail on fuzzy queries.  
**Target Users:** Developers building/extending coding agents.  
**Success Metrics:** 
- Retrieval accuracy >85% across embedding models (benchmark via semantic similarity tests).
- <500ms query latency.
- <5% context token overhead per agent session.
- Zero-code changes for embedding model switching.

### 2. Goals & Objectives
- **Primary:** Persistent, fuzzy memory with configurable embeddings for accuracy/speed trade-offs.
- **Secondary:** Leverage Qdrant (auto-setup/detect); integrate CodeIndex components for rapid dev.
- **Non-Goals:** Full RAG UI; real-time collaboration; non-coding domains.

### 3. User Stories
- As a developer, I want to configure the embedding model (e.g., local vs. OpenAI) via YAML to balance performance/cost.
- As a coding agent, I want seamless Qdrant integration, auto-detecting my existing instance.
- As a maintainer, I want project structure mirroring CodeIndex for familiarity (e.g., `src/chunker`, MCP handlers).

### 4. Functional Requirements
- **Ingestion:** 
  - Chunk input using Simplified AST from CodeIndex (TreeSitter for 39+ langs; fallback to NLTK sentence splitter for prose).
  - Embed chunks via configurable model (`all-MiniLM-L6-v2` default; `bge-small-en-v1.5` or `text-embedding-3-small` options).
  - Store in Qdrant with metadata (`chunk_id`, `timestamp`, `session_id`, `lang`, `user_intent`, `embedding_model`).
- **Retrieval:** 
  - Embed query with selected model; vector search (top-5 default).
  - Optional hybrid search (vector + keyword); re-ranking with cross-encoder.
  - Return formatted chunks (Markdown with code blocks).
- **Management:** Prune low-usage vectors; export/import DB; benchmark embeddings (CLI command for accuracy tests).
- **MCP Interface:** Tools for `ingest_memory`, `recall_memory`, `prune_memory` (JSON schema, adapted from CodeIndex FastMCP).
- **CLI Wrapper:** `semvecmem ingest <file> --embedder bge-small-en-v1.5`; `semvecmem setup-qdrant` for detection/setup.
- **Config:** YAML file (`config.yaml`) for embedder, Qdrant host/port/api_key, etc. Env var overrides (like CodeIndex).

### 5. Non-Functional Requirements
- **Performance:** Local-first Qdrant; <1s ingest for 10k chunks.
- **Tech Stack:** Python 3.10+; FastMCP; sentence-transformers (`all-MiniLM-L6-v2`, `bge-small-en-v1.5`); openai (`text-embedding-3-small`); qdrant-client; TreeSitter.
- **Security:** Local DB; OpenAI API key env-protected (e.g., `OPENAI_API_KEY`).
- **Compatibility:** MCP 1.0+; auto-detect Qdrant (ping `localhost:6333`) or guide setup via Docker.
- **Dependencies:** Minimal; offline-capable for local embedders.

### 6. Assumptions & Risks
- **Assumptions:** Access to CodeIndex (`/Users/wrk/WorkDev/MCP-Dev/claude-codeindex` or GitHub); OpenAI key for `text-embedding-3-small` if selected.
- **Risks:** OpenAI API costs (mitigate: default local embedder); Qdrant not running (mitigate: setup script).
- **Out of Scope:** Distributed DB; advanced eval (v2).

### 7. Appendix
- **Embedding Config Examples:**
  - Local: `embedder: all-MiniLM-L6-v2` (fast, ~80MB, 384 dims).
  - Higher Accuracy: `embedder: bge-small-en-v1.5` (~134MB, 384 dims).
  - Premium: `embedder: text-embedding-3-small` (requires `OPENAI_API_KEY`, cloud-based).
- **Tech References:**
  - [Qdrant Docs](https://qdrant.tech/documentation/)
  - [FastMCP](https://github.com/modelcontextprotocol/fastmcp)
  - [CodeIndex Repo](https://github.com/WKassebaum/codeindex)
  - [sentence-transformers](https://huggingface.co/sentence-transformers)
  - [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)

---

## Detailed Prompt for AI Coding Assistant
Use this as a **system prompt** in your AI tool (e.g., Claude Sonnet-3.5/4.5, Grok-Code-Fast-1, Grok-4-Fast via VS Code with RooCode/Cline). It generates the codebase incrementally.

```plaintext
You are an expert Python developer specializing in AI agent tools, MCP servers, and vector databases. Your task: Implement SemVecMem v1.1 per the attached PRD. Leverage CodeIndex project as a resource: Adapt structure (monorepo with src/, tests/, config.yaml), FastMCP usage (tool schemas/handlers from mcp.py), Simplified AST parser (chunker.py with TreeSitter), configuration (YAML with env fallbacks).

Core Specs:
- Vector Store: Qdrant (via qdrant-client; collection 'semvecmem'; HNSW index, ef_construct=100, m=16).
- Qdrant Setup: Include setup script (setup.py or CLI cmd) to detect running instance (ping host:port, e.g., localhost:6333) or launch via Docker Compose (provide sample compose.yaml).
- Chunking: Adapt CodeIndex Simplified AST (TreeSitter 39 langs; fallback NLTK sentences for prose).
- Embeddings: Configurable via config.yaml:
  - 'all-MiniLM-L6-v2' (sentence-transformers; default; 384 dims).
  - 'bge-small-en-v1.5' (sentence-transformers; 384 dims).
  - 'text-embedding-3-small' (openai; requires OPENAI_API_KEY; batch embeds).
  - Factory function to load based on config; store model name in metadata.
- Metadata: Dict with 'chunk_id', 'timestamp', 'session_id', 'lang', 'user_intent', 'embedding_model'.
- Retrieval: Cosine sim; top_k=5; filter by metadata if specified (e.g., lang=python).
- CLI: Click-based; add --embedder flag; 'semvecmem setup-qdrant' cmd.
- MCP Server: FastMCP tools (ingest_memory, recall_memory, prune_memory); pass embedder via params if override; adapt CodeIndex schemas/handlers.
- Error Handling: Graceful (e.g., fallback to all-MiniLM-L6-v2 if OpenAI fails; retry Qdrant ping).
- Testing: Pytest; include embedding benchmarks (e.g., similarity tests on sample chunks).
- Structure: Mirror CodeIndex: src/semvecmem/{core, mcp, cli, chunker, config}; pyproject.toml; README.md; config.yaml; docker-compose.yaml.

Phased Output:
1. Generate project skeleton (files/dirs, config.yaml, docker-compose.yaml).
2. Implement config & embedder factory (support 3 models).
3. Adapt chunker from CodeIndex.
4. Build core (ingest/embed/store/query with Qdrant).
5. MCP server (adapt FastMCP patterns).
6. CLI layer incl. Qdrant setup.
7. Tests, benchmarks & docs.

Output Format: Full code files in Markdown code blocks (e.g., ```python filename.py ... ```). Explain changes briefly. Ask for next phase confirmation.

PRD: [Paste full updated PRD from above].
CodeIndex Notes: Use as template—e.g., chunker extracts funcs/classes; FastMCP in mcp/ dir; config loads YAML/env.
```

**Usage Tip:** Start with this prompt, then iterate: "Phase 1: Skeleton." Expect ~2-4 hours for MVP generation.

---

## Suggested Architecture

### High-Level Diagram (Text-Based)
```
[User/Agent] --> MCP Client (e.g., Claude Code CLI) 
                |
                | Tool Call (JSON: {tool: "recall_memory", params: {query: "...", top_k: 5, embedder: "optional_override"}})
                v
[MCP Server (FastMCP, adapted from CodeIndex)] <--> [Core Engine]
  - Expose /tools; handlers mirror CodeIndex mcp.py
  - Config: Load from config.yaml/env (e.g., QDRANT_HOST, EMBEDDER_MODEL)
                |
                v
[Chunker (Adapted CodeIndex AST)] --> [Embedder Factory (Configurable: MiniLM/bge/OpenAI)] --> [Vector Store (Qdrant)]
  - Input: Text/code stream
  - Chunk: AST nodes + sentences
  - Embed: Switch per config; local/API
  - Store: Collection w/ payloads; detect/setup Qdrant
                ^
                | Query: Embed --> ANN Search --> Re-rank --> Format (MD chunks)
[CLI Wrapper] <-- Click cmds; setup-qdrant for detection/launch
```

### Components Breakdown
| Component | Tech | Responsibility | Overhead Notes |
|-----------|------|----------------|---------------|
| **Chunker** | TreeSitter/NLTK (from CodeIndex) | Semantic splitting (code/prose) | Low: <100ms/chunk; preserves structure. |
| **Embedder** | sentence-transformers / openai | Vectorize; configurable | Factory switches models; OpenAI adds latency (~200ms). |
| **Store** | Qdrant (client) | Index/retrieve | Auto-detect; HNSW for fast ANN. |
| **MCP Server** | FastMCP | Tool routing | Zero bloat: Injects ~200-500 tokens. |
| **CLI** | Click | Mgmt/setup | Setup cmd reduces friction. |
| **Config** | YAML + os.environ | Settings | Mirrors CodeIndex for familiarity. |

**Scalability:** Qdrant handles 10k-100k chunks; embeddings configurable for trade-offs.

---

## Project Roadmap

### Phase 1: Setup & Prototype (1-2 days)
- [ ] Clone/setup repo (prompt for skeleton; include `config.yaml`, `docker-compose.yaml`).
- [ ] Adapt CodeIndex structure/chunker/config.
- [ ] Implement embedder factory & ingest with Qdrant detection.
- [ ] Test: Retrieval with each embedder on sample data.
- **Milestone:** Working DB with configurable embeddings.

### Phase 2: MCP Integration (1 day)
- [ ] Build FastMCP server (adapt CodeIndex `mcp.py`).
- [ ] Integrate Qdrant setup logic (detect/launch).
- [ ] Agent test with Claude Code CLI.
- **Milestone:** Fuzzy recall via MCP.

### Phase 3: Enhancements & Polish (2 days)
- [ ] CLI with embedder/Qdrant options.
- [ ] Pytest suite (80% coverage; benchmark embeddings).
- [ ] Docs: README with CodeIndex refs.
- **Milestone:** Full MVP v1.1.

### Phase 4: Iteration & Deployment (Ongoing, 1 week+)
- [ ] Test OpenAI embedder costs/accuracy.
- [ ] v2: Advanced Qdrant filters; hierarchical memory.
- [ ] Release: PyPI package; link to CodeIndex.
- **Tools/Resources:**
  - Template: Cookiecutter Python.
  - Benchmarks: `ragas` or `datasets` for test data.
  - Tracking: GitHub Issues.

---

*End of Document. Next Steps:* Save this file in project root. Run AI prompt for code generation (e.g., "Phase 1: Skeleton"). Reference CodeIndex files (e.g., copy `chunker.py` from `/Users/wrk/WorkDev/MCP-Dev/claude-codeindex`). Ping for refinements!