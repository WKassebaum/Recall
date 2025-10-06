# SemVecMem v1.2 - Semantic Vector Memory for Coding Agents

[![Status](https://img.shields.io/badge/status-planning-yellow)](https://github.com/your-username/SemVecMem)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

A long-term semantic memory system for coding agents (Claude Code, Grok CLI) that addresses context window limitations through vector embeddings and fuzzy retrieval.

## 🎯 Status: Pre-Implementation Planning

This repository contains **comprehensive planning documentation** for SemVecMem v1.2. Implementation begins shortly.

### Current Phase
- ✅ Requirements analysis complete
- ✅ Architecture designed and validated
- ✅ Embedding model evaluation complete (4 models, 87% accuracy)
- ✅ Hardware validation (M1 Max confirmed excellent fit)
- 🚀 Ready for Phase 1 implementation

## 📚 Documentation

### Quick Start
- **[EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)** - 5-minute overview, go/no-go decision
- **[IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md)** - Phase-by-phase checklist

### Detailed Analysis
- **[PROJECT_ANALYSIS_REPORT.md](PROJECT_ANALYSIS_REPORT.md)** - Complete technical analysis (architecture, research, risk)
- **[PRD_UPDATES_v1.2.md](PRD_UPDATES_v1.2.md)** - v1.2 changes (expanded embedding models)
- **[semantic-memory-project-starter-v1.1.markdown](semantic-memory-project-starter-v1.1.markdown)** - Original PRD

### Development Reference
- **[CLAUDE.md](CLAUDE.md)** - Guidance for Claude Code when working in this repo

## 🚀 Key Features (Planned)

### Semantic Memory
- AST-aware chunking via TreeSitter (39+ languages)
- Fuzzy retrieval of past code, sessions, decisions
- Persistent across coding sessions

### Embedding Models (v1.2)
- **Default:** `snowflake/arctic-embed-m` (87% accuracy, 1024D)
- **Long Context:** `nomic-embed-text-v1.5` (86.2% accuracy, 768D, 8K tokens)
- **Balanced:** `bge-small-en-v1.5` (84.7% accuracy, 384D)
- **Speed:** `all-MiniLM-L6-v2` (78.1% accuracy, 384D)

All models run excellently on M1 Max (<8% of 64GB RAM).

### Integration
- MCP (Model Context Protocol) server via FastMCP
- Local-first with Qdrant vector database
- Zero cloud dependencies, no API keys required

## 🎯 Success Metrics

| Metric | Target | Projected |
|--------|--------|-----------|
| Retrieval Accuracy | >85% | **87%** ✅ |
| Query Latency | <500ms | ~35ms ✅ |
| Token Overhead | <5% | ~3% ✅ |
| Code Coverage | >80% | TBD |

## 🛠️ Planned Architecture

```
MCP Client (Claude/Grok CLI)
  ↓ (tool calls via MCP)
MCP Server (FastMCP)
  ↓
Core Engine
  ├─ Chunker (TreeSitter AST parser)
  ├─ Embedder Factory (4 models with intelligent fallback)
  └─ Vector Store (Qdrant)
```

## 📋 Implementation Timeline

- **Phase 1:** Foundation & Core (Days 1-2.5) - Project skeleton, config, embedders, Qdrant
- **Phase 2:** Ingestion & Retrieval (Days 3-4.5) - Chunking, core pipeline, MCP server
- **Phase 3:** CLI & Polish (Days 5.5-7) - CLI, benchmarks, docs, tests

**Total:** 7 days (56 hours) for production-ready MVP

## 🔧 Hardware Requirements

**Validated on:**
- M1 Max with 64GB RAM ✅
- Uses <8% RAM for all models
- ~35ms query latency with MPS acceleration

**Minimum:**
- Python 3.10+
- 4GB RAM (embeddings + Qdrant)
- 10GB disk (models + data)
- Docker Desktop (for Qdrant) or native Qdrant binary

## 📖 Getting Started (Post-Implementation)

```bash
# Installation (when ready)
pip install semvecmem

# Setup Qdrant
semvecmem setup-qdrant

# Ingest code
semvecmem ingest myproject/ --recursive

# Query
semvecmem recall "authentication logic" --top-k 5

# Benchmark models
semvecmem benchmark
```

## 🤝 Contributing

This project is in planning phase. Once implementation begins, contributions will be welcome.

## 📄 License

Apache 2.0 (planned)

## 🙏 Acknowledgments

- CodeIndex project for AST chunking patterns
- Qdrant for vector database
- FastMCP for MCP server framework
- Snowflake, Nomic AI, BAAI for embedding models

---

**Note:** This is a planning repository. Code implementation starts after documentation review.

For questions or feedback, see [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) for project overview.
