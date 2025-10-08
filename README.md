# SemVecMem v1.2 - Semantic Vector Memory for Coding Agents

[![Status](https://img.shields.io/badge/status-planning-yellow)](https://github.com/your-username/SemVecMem)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

A long-term semantic memory system for coding agents (Claude Code, Grok CLI) that addresses context window limitations through vector embeddings and fuzzy retrieval.

## 🎯 Status: Quality-Gated Implementation Ready

This repository contains **comprehensive planning documentation** for SemVecMem v1.3.1. Implementation ready with quality-first approach.

### Current Phase
- ✅ Requirements analysis complete
- ✅ Architecture validated (independent + Zen MCP consensus, 9/10 confidence)
- ✅ Embedding model evaluation complete (4 models, Arctic 87% accuracy)
- ✅ Hardware validation (M1 Max confirmed excellent fit, <8% RAM)
- ✅ Quality-gated plan with 17 testing waypoints
- ✅ Multi-collection strategy validated (dimension mismatch prevention)
- ✅ 2-tier fallback validated (Arctic → MiniLM, 9/10 confidence)
- 🚀 Ready for POC phase (testing infrastructure setup)

## 📚 Documentation

### 🚀 Start Here (Implementation)
- **[QUALITY_GATED_IMPLEMENTATION_PLAN.md](QUALITY_GATED_IMPLEMENTATION_PLAN.md)** - **PRIMARY REFERENCE** - 17 testing waypoints, quality gates
- **[CLAUDE.md](CLAUDE.md)** - Guidance for Claude Code when working in this repo
- **[GO_FORWARD_PLAN_v1.3.1.md](GO_FORWARD_PLAN_v1.3.1.md)** - Detailed implementation plan with Zen insights

### Architecture & Validation
- **[ZEN_VALIDATION_FINAL_SYNTHESIS.md](ZEN_VALIDATION_FINAL_SYNTHESIS.md)** - Zen MCP consensus validation (o3-mini, 9/10 confidence)
- **[CRITICAL_REVIEW_SUMMARY.md](CRITICAL_REVIEW_SUMMARY.md)** - TL;DR of 7 critical issues + solutions
- **[ARCHITECTURE_REVIEW.md](ARCHITECTURE_REVIEW.md)** - Comprehensive architecture analysis (59 pages)
- **[ROADMAP_UPDATES_v1.3.md](ROADMAP_UPDATES_v1.3.md)** - Updated phase breakdowns with fixes

### Original Specification
- **[EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)** - 5-minute overview
- **[PROJECT_ANALYSIS_REPORT.md](PROJECT_ANALYSIS_REPORT.md)** - Complete technical analysis
- **[PRD_UPDATES_v1.2.md](PRD_UPDATES_v1.2.md)** - v1.2 embedding model expansion
- **[semantic-memory-project-starter-v1.1.markdown](semantic-memory-project-starter-v1.1.markdown)** - Original PRD

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

## 🎯 Success Metrics (Quality Gates)

| Metric | Target | How Measured | Gate |
|--------|--------|--------------|------|
| **Retrieval Accuracy** | >85% (87% for Arctic) | Benchmark suite | Phase 3 |
| **Query Latency** | <500ms | Performance tests | Phase 2 |
| **Token Overhead** | <5% | MCP payload test | Phase 2 |
| **Code Coverage** | >80% | pytest-cov | All phases |
| **Cyclomatic Complexity** | ≤6 core, ≤8 complex | radon | All phases |
| **Maintainability Index** | ≥B | radon | All phases |
| **Type Safety** | 100% | mypy strict | All phases |
| **Migration Robustness** | All failures pass | Injection tests | Phase 3 |

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

## 📋 Implementation Timeline (Quality-Gated)

**Philosophy:** Quality gates, not calendar dates. Phases exit when all metrics met.

- **POC:** Testing infrastructure + Unified API validation (2-3 days, 1 waypoint)
- **Phase 1:** Foundation (4-5 days, 6 waypoints) - Multi-collection, embedders, unified API
- **Phase 2:** Ingestion & Retrieval (3-4 days, 4 waypoints) - Chunking, retrieval, MCP
- **Phase 3:** Migration & Benchmarks (5-6 days, 4 waypoints) - CLI, migration tool, benchmarks
- **Phase 4:** Polish & Integration (2-3 days, 2 waypoints) - Final testing, performance

**Total:** 14-18 days (quality-first, no rush)

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
