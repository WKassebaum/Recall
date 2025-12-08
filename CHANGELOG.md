# Changelog

All notable changes to Recall will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.1] - 2025-12-07

### Changed
- **Test coverage improvements** - Expanded from 54.77% to 80.03% ⭐
  - 236 total tests covering all core modules
  - CLI modules fully tested (cleanup, doctor, recover, setup)
  - Core modules tested (store, embedders, backends)
  - Integration tests stabilized with proper database isolation
  - Added tests for migrate_mode and MCP server

### Fixed
- ✅ Integration test failures caused by database state pollution
- ✅ Import path for `UnexpectedResponse` (qdrant_client.http.exceptions)
- ✅ Test isolation using proper fixtures and mocking

### Quality
- Test coverage: 80.03% (target: >80%)
- All 236 tests passing
- Package builds verified (wheel + sdist)
- Version synchronization across all files

## [1.4.0] - 2025-10-18

### Added
- **Docker reliability improvements** - Eliminates corruption on macOS ⭐
  - Docker named volumes (replaces bind mounts for macOS stability)
  - WAL tuning configuration (`qdrant-config.yaml`) for batch writes
  - Performance mode with reduced fsync frequency
  - Health checks to detect corruption early
  - Multi-project support validated (4+ concurrent projects)
  - `docker-compose.yml` for simplified deployment
  - Zero corruption issues since implementation

- **Automated backup system** (macOS) - Prevents data loss ⭐
  - `scripts/backup-qdrant-auto.sh` - Intelligent rotation script
    - Backups every 6 hours: 4 recent (24hrs), 7 daily, 4 weekly
    - Auto-cleanup of old backups
    - Symlink to latest good backup for auto-recovery
  - `scripts/setup-auto-backup.sh` - One-command installer
  - launchd service integration (`com.recall.backup.plist`)
  - Comprehensive logging to `logs/backup-{stdout,stderr}.log`
  - Maximum 6-hour data loss window (vs total loss before)

- **Auto-recovery system** - One-command restoration ⭐
  - `recall recover` command - Health monitoring and auto-recovery
  - Three health checks: Docker container, Qdrant health, collection accessibility
  - Automatic restoration from latest backup if corruption detected
  - Force recovery option: `recall recover --force`
  - Specific backup selection: `recall recover --backup <file>`
  - 2-3 minute recovery time (fully automated)

- **Migration tools** - Safe data preservation
  - `scripts/migrate-to-named-volumes.sh` - Migrate bind mounts → named volumes
  - Preserves all data (never deletes original)
  - Automatic detection of current setup
  - Verification and rollback instructions
  - Zero breaking changes (both approaches supported)

- **Claude Skills integration** - Progressive disclosure teaching system
  - Created `~/.claude/skills/recall-memory-skill/` with comprehensive guidance
  - `SKILL.md` - 400+ line comprehensive usage guide
    - When to Use Recall (auto-trigger patterns)
    - Available MCP Tools documentation
    - Event Types and Search Strategies
    - Context Management workflows
    - Integration patterns and examples
  - `examples.md` - Real usage examples from Recall development
    - 8 comprehensive examples (debugging timelines, decision tracking, etc.)
    - Anti-patterns to avoid
    - Token efficiency analysis
  - Progressive disclosure benefits: ~20 tokens idle, full docs on-demand

- **Single-source version management** - Prevents version drift
  - Canonical version: `src/recall/__version__.py`
  - Dynamic versioning in `pyproject.toml` via setuptools
  - Auto-sync script: `scripts/sync-version.sh` syncs to plugin.json
  - Documentation in CLAUDE.md

### Changed
- Enhanced token efficiency through Skills progressive disclosure
- Improved version management workflow (single source of truth)
- Docker storage from bind mounts → named volumes (macOS stability)
- WAL configuration optimized for batched writes (512MB buffer, 30s flush)

### Fixed
- ✅ Qdrant corruption on macOS Docker (file descriptor translation issues)
- ✅ Data loss from container crashes (automated backup + recovery)
- ✅ Multi-project concurrent access (thread-safe named volumes)
- ✅ Bind mount fsync issues (Docker-managed storage eliminates OS layer)

### Documentation
- **[DOCKER_RELIABILITY.md](DOCKER_RELIABILITY.md)** - Comprehensive troubleshooting guide
  - Root cause analysis (macOS osxfs/virtiofs issues)
  - Quick start commands
  - Automated backup strategy
  - Recovery procedures
  - Volume management
  - Multi-project support details

- **[AUTOMATED_BACKUP_RECOVERY_GUIDE.md](AUTOMATED_BACKUP_RECOVERY_GUIDE.md)** - Complete user guide
  - 5-minute quick start
  - How automation works (schedule, rotation)
  - Auto-recovery usage examples
  - Management commands
  - Best practices for multi-project use
  - Troubleshooting common issues

- **[CROSS_PLATFORM_BACKUP_GUIDE.md](CROSS_PLATFORM_BACKUP_GUIDE.md)** - Platform analysis
  - Linux support: cron approach (10 min setup, scripts work as-is)
  - Windows WSL2: recommended (use Linux approach)
  - Windows native: not recommended (2-3 hours PowerShell work)
  - Platform-specific implementation details

- **[TEAM_ROLLOUT_GUIDE.md](TEAM_ROLLOUT_GUIDE.md)** - Breaking changes analysis
  - **Answer: NO database wipe needed**
  - Optional migration strategy
  - Safe migration script usage
  - Backward compatibility approach
  - Email templates for team communication
  - Rollback procedures

- Created Claude Skills teaching documentation
- Added Docker Reliability section to CLAUDE.md
- Added Version Management section to CLAUDE.md
- Real-world usage examples from production development

### Quality
- Maintains backward compatibility
- Zero breaking changes (supports both bind mounts and named volumes)
- Skills enhance discoverability without changing core functionality
- Production-tested on macOS with 4 concurrent projects
- Automated backup system validated (launchd service running)

## [1.3.2] - 2025-10-11

### Added
- **Dual-mode memory system** - Semantic + episodic retrieval
  - Semantic mode: Search by meaning (vector similarity)
  - Chronological mode: Search by time range (timestamp-ordered)
  - Hybrid mode: Combine semantic + temporal + event filtering
- **Event-based structure** - Six event types (decision, discovery, milestone, preference, error, success)
- **Advanced filtering** - Time range, event types, session-based filtering
- **Comprehensive CLAUDE.md guidance** - 350+ lines of usage patterns and auto-trigger guidance
- **Open-ended time range support** - Query from specific date to present
- **Timezone-aware datetime handling** - Fixed timezone comparison bugs

### Changed
- Enhanced `recall_memory()` API with retrieval_mode, time_range, event_types, sort_by parameters
- Enhanced `ingest_memory()` with event metadata guidance
- Improved result formatting - Mode-aware display (show/hide scores based on mode)

### Fixed
- Timezone handling bug with `datetime.max` in open-ended time ranges
- MCP stdout contamination (all logging redirected to stderr)
- Config path resolution (absolute path for MCP compatibility)

### Documentation
- Created comprehensive validation report (500+ lines)
- Created detailed release notes (400+ lines)
- Added CLAUDE.md section on external working memory (350+ lines)
- Organized documentation into docs/ folder structure
- Updated README.md for v1.3.2 with dual-mode features

### Quality
- Test coverage: 91.94% (exceeds 80% target)
- All quality gates passing
- Zero breaking changes (fully backward compatible)

## [1.3.1] - 2025-10-10

### Added
- Phase 3 completion: Migration tool, benchmark suite, MCP server
- Migration tool with canary validation (CC ≤ 8)
  - Canary testing with configurable sample size
  - Batch processing support
  - Progress tracking and reporting
  - Dry run mode
- Benchmark suite for embedding model accuracy validation
- MCP server integration with FastMCP
- CLI commands: `recall migrate`, `recall benchmark`

### Changed
- Enhanced test coverage to 91.94%
- Comprehensive failure injection testing for migration tool
- All 126 tests passing (20 new migration tests)

### Quality
- All 17 waypoints validated
- Cyclomatic complexity: CC ≤ 8 maintained
- Performance: 17.5ms average query latency (28x faster than target)
- Memory usage: <8GB on M1 Max

### Documentation
- Phase 3 completion summary
- Migration tool documentation
- Benchmark methodology

## [1.3.0] - 2025-10-08

### Added
- Phase 2 completion: Ingestion pipeline, retrieval engine, MCP tools
- TreeSitter AST-aware chunking for 39+ languages
- Multi-strategy chunking (Python, Markdown, JSON, prose)
- Session-based memory isolation
- Metadata enrichment and filtering
- MCP tools: `ingest_memory`, `recall_memory`, `memory_stats`

### Changed
- Enhanced chunking with semantic structure preservation
- Improved retrieval with similarity score thresholds
- Auto-detection of content types

### Quality
- End-to-end integration tests passing
- Latency <500ms validated
- Accuracy >85% validated

## [1.2.0] - 2025-10-05

### Added
- Phase 1 completion: Foundation and core infrastructure
- UnifiedVectorStore with multi-collection routing
- Embedder factory with 2-tier fallback (Arctic → MiniLM)
- Configuration system (YAML + env vars)
- Qdrant multi-collection setup (384D, 768D, 1024D)
- Dimension verification and validation
- Startup health checks

### Changed
- Simplified fallback strategy to 2-tier (from 4-tier)
- Enhanced error handling and logging
- Improved configuration validation

### Quality
- Test coverage >80%
- Cyclomatic complexity CC ≤ 6 for core components
- Type safety: mypy strict mode
- Code quality: ruff passing

### Documentation
- Quality-gated implementation plan
- Architecture review (59 pages)
- Zen MCP validation reports

## [1.1.0] - 2025-10-01

### Added
- Project planning and architecture validation
- Zen MCP consensus validation (9/10 confidence)
- Hardware validation on M1 Max
- Embedding model benchmarking (4 models evaluated)
- Multi-collection strategy design
- Quality gates and waypoint system

### Documentation
- Executive summary
- Project analysis report
- PRD updates v1.2
- Critical review summary
- Go-forward plan v1.3.1

## [1.0.0] - 2025-09-28

### Added
- Initial project specification
- Product requirements document (PRD)
- Use case analysis
- Success metrics definition
- Technology stack selection

---

## Version Naming Convention

- **Major (X.0.0)**: Breaking API changes, significant architecture changes
- **Minor (1.X.0)**: New features, backward-compatible enhancements
- **Patch (1.3.X)**: Bug fixes, documentation updates, minor improvements

## Links

- [Latest Release](https://github.com/WKassebaum/Recall/releases/latest)
- [All Releases](https://github.com/WKassebaum/Recall/releases)
- [Documentation](docs/)
- [Contributing Guide](CONTRIBUTING.md)
