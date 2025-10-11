# Recall Development TODO

> **Last Updated:** 2025-10-11
> **Current Version:** v1.3.3
> **Status:** Plugin support complete, roadmap prioritized

---

## 🎯 v1.4.0 - Context Management & User Experience

**Focus:** Individual developer productivity, context window optimization
**Target:** Q1 2025

### 1. Context Size Monitoring & Alerts ⭐ **HIGHEST PRIORITY**

**User Value:** Prevent context loss, maintain session continuity
**Implementation Complexity:** Medium (Claude Code API integration)

**Requirements:**
- [ ] Implement context window usage tracking API
- [ ] Create real-time usage monitoring service
- [ ] Design alert system for 70%+ capacity threshold
- [ ] Build automatic memory offload suggestion engine
- [ ] Integrate with Claude Code status bar (if API available)
- [ ] Add configurable alert thresholds (default 70%, 85%, 95%)
- [ ] Create user notification system (non-intrusive)

**Technical Details:**
- Monitor Claude Code context via MCP
- Calculate "offloadable" memories (low importance, old, infrequently accessed)
- Surface suggestions proactively when threshold reached
- Persist user preferences for alert frequency

**Success Metrics:**
- Alert triggers at configured thresholds
- <100ms monitoring overhead
- User dismissal rate <20% (relevant suggestions)

**Dependencies:** None

---

### 2. Smart Mode Selection

**User Value:** Optimal retrieval without manual mode selection
**Implementation Complexity:** Medium-High (ML/heuristics)

**Requirements:**
- [ ] Implement query pattern analyzer
  - [ ] Temporal indicators ("last week", "yesterday", "on October 10")
  - [ ] Semantic indicators ("about", "related to", "similar to")
  - [ ] Hybrid indicators ("recent", "lately", "since")
- [ ] Build mode selection heuristics
  - [ ] Rule-based classification (v1)
  - [ ] ML-based classification (v2, optional)
- [ ] Create user preference learning system
  - [ ] Track user overrides (manual mode selection)
  - [ ] Adjust heuristics based on feedback
- [ ] Add confidence scoring for mode selection
- [ ] Implement fallback to hybrid mode when uncertain
- [ ] Add `/recall-search --auto` flag for testing

**Technical Details:**
- Parse query with spaCy or simple regex patterns
- Score each mode (semantic, chronological, hybrid)
- Select highest-scoring mode or hybrid if close
- Log selection rationale for debugging

**Success Metrics:**
- >85% accuracy on mode selection
- User override rate <15%
- Query latency increase <10ms

**Dependencies:** None

---

### 3. Memory Importance Scoring

**User Value:** Prioritize critical memories, intelligent pruning
**Implementation Complexity:** Medium

**Requirements:**
- [ ] Design importance scoring algorithm
  - [ ] Access frequency (how often retrieved)
  - [ ] Recency (when last accessed)
  - [ ] Event type weighting (decisions > preferences)
  - [ ] User-explicit importance ratings (optional field)
- [ ] Implement automatic scoring calculation
  - [ ] Update scores on each access
  - [ ] Decay over time for stale memories
- [ ] Add importance field to memory metadata
- [ ] Create priority-based retrieval ranking
  - [ ] Boost high-importance results in semantic search
  - [ ] Surface critical memories in suggestions
- [ ] Build intelligent pruning suggestions
  - [ ] Identify low-importance, old, unaccessed memories
  - [ ] User confirmation before deletion
- [ ] Add `/recall-prune` command for cleanup

**Technical Details:**
- Scoring formula: `importance = (access_count * 2) + recency_score + event_weight + user_rating`
- Store importance in Qdrant payload
- Re-rank search results by importance × similarity
- Track access patterns in lightweight database (SQLite)

**Success Metrics:**
- Critical decisions always in top 10 results
- Pruning suggestions 90%+ accurate (user acceptance)
- Importance scores stabilize after 10+ accesses

**Dependencies:** None

---

### 4. Cross-Project Memory Sharing

**User Value:** Share knowledge across projects, global preferences
**Implementation Complexity:** Medium

**Requirements:**
- [ ] Design memory scope system
  - [ ] Global scope (shared across all projects)
  - [ ] Project scope (current project only)
  - [ ] Explicit sharing (share specific memories)
- [ ] Implement scope-based filtering in retrieval
  - [ ] Default: Current project + global
  - [ ] Flag: `--scope global` or `--scope project-name`
- [ ] Add scope field to memory metadata
- [ ] Create scope management commands
  - [ ] `/recall-share <memory_id>` - Make memory global
  - [ ] `/recall-unshare <memory_id>` - Make project-scoped
  - [ ] `/recall-search --scope global` - Search global only
- [ ] Build shared preference pools
  - [ ] User coding style preferences (always global)
  - [ ] Tool preferences (editor, linter, etc.)
- [ ] Add project detection (git root, cwd)

**Technical Details:**
- Add `scope` field to metadata: "global" | "project:<name>" | "shared"
- Auto-detect project name from git remote or directory
- Filter by scope in Qdrant query
- Merge global + project results in retrieval

**Success Metrics:**
- Preferences available across all projects
- Project-specific memories isolated correctly
- <5ms overhead for scope filtering

**Dependencies:** None

---

### 5. Memory Export/Import

**User Value:** Backup, restore, team knowledge sharing
**Implementation Complexity:** Low-Medium

**Requirements:**
- [ ] Design export formats
  - [ ] JSON (machine-readable, full fidelity)
  - [ ] YAML (human-readable, editable)
  - [ ] Markdown (documentation format)
- [ ] Implement export functionality
  - [ ] Export all memories: `/recall-export --format json memories.json`
  - [ ] Export by session: `/recall-export --session phase3 phase3.json`
  - [ ] Export by date range: `/recall-export --from 2025-10-01 --to 2025-10-31`
  - [ ] Export by event type: `/recall-export --events decision,milestone`
- [ ] Implement import functionality
  - [ ] Import from file: `/recall-import memories.json`
  - [ ] Conflict resolution (duplicate chunk IDs)
  - [ ] Merge or overwrite modes
- [ ] Add validation for imported data
  - [ ] Schema validation (required fields)
  - [ ] Embedding dimension compatibility check
- [ ] Create migration utilities
  - [ ] Export from one instance, import to another
  - [ ] Useful for team onboarding or backup/restore

**Technical Details:**
- Export: Query all memories, serialize with metadata
- Import: Deserialize, validate, re-embed if needed
- Handle embedding model mismatches gracefully
- Preserve all metadata fields

**Success Metrics:**
- Export/import round-trip preserves 100% of data
- Handles 10,000+ memories efficiently (<30s)
- Clear error messages for invalid imports

**Dependencies:** None

---

## 🚀 v1.5.0 - Automation & Intelligence

**Focus:** Proactive assistance, workflow automation
**Target:** Q2 2025

### 6. Auto-Ingestion Hooks

**User Value:** Capture important events automatically, reduce manual work
**Implementation Complexity:** High (integration complexity)

**Requirements:**
- [ ] Design hook system architecture
  - [ ] Event triggers (git commit, test failure, errors)
  - [ ] Configurable patterns (regex, glob, event types)
  - [ ] User-defined hooks (.recall-hooks.yaml)
- [ ] Implement Git integration
  - [ ] Post-commit hook: Capture commit message + diff summary
  - [ ] Tag decisions ("feat:", "fix:", "refactor:")
  - [ ] Automatic session_id from branch name
- [ ] Implement test integration
  - [ ] Pytest plugin for test failures
  - [ ] Capture test name, error message, stack trace
  - [ ] Automatic event_type: "error"
- [ ] Add error logging integration
  - [ ] Detect exceptions in Claude Code sessions
  - [ ] Capture error context automatically
- [ ] Create hook configuration system
  - [ ] Enable/disable individual hooks
  - [ ] Custom trigger patterns
  - [ ] Metadata templates per hook type
- [ ] Add hook management commands
  - [ ] `/recall-hooks list` - Show active hooks
  - [ ] `/recall-hooks enable git-commit` - Enable specific hook
  - [ ] `/recall-hooks disable all` - Disable all hooks

**Technical Details:**
- Hook configs in `.recall-hooks.yaml` (project root)
- Git hooks via .git/hooks/post-commit
- Pytest integration via plugin system
- Error detection via Claude Code MCP events (if available)

**Success Metrics:**
- >80% of important events captured automatically
- <50ms hook execution overhead
- User override rate <10% (hooks generate good memories)

**Dependencies:**
- Git integration: git hooks API
- Test integration: pytest plugin API
- Error detection: Claude Code MCP event system

---

### 7. Smart Suggestions

**User Value:** Proactive memory surfacing, serendipitous discovery
**Implementation Complexity:** High (pattern matching, ranking)

**Requirements:**
- [ ] Implement proactive suggestion engine
  - [ ] Monitor current code context (file being edited)
  - [ ] Detect similarity to past work
  - [ ] Surface related memories automatically
- [ ] Design notification system
  - [ ] Non-intrusive (status bar or side panel)
  - [ ] "You worked on similar code last week" notifications
  - [ ] "Related decision from Phase 2" alerts
- [ ] Build pattern-based insight generation
  - [ ] Detect recurring patterns (repeated errors, similar bugs)
  - [ ] Suggest preventive measures
  - [ ] Surface lessons learned
- [ ] Create suggestion ranking algorithm
  - [ ] Relevance score (similarity to current context)
  - [ ] Recency (prefer recent over old)
  - [ ] Importance (high-importance memories prioritized)
- [ ] Add user feedback mechanism
  - [ ] "Helpful" / "Not helpful" buttons
  - [ ] Learn from feedback to improve suggestions
- [ ] Implement suggestion settings
  - [ ] Frequency (every 5min, 15min, hourly, manual)
  - [ ] Threshold (only show >70% relevance)
  - [ ] Categories (decisions only, errors only, all)

**Technical Details:**
- Embed current file content, compare to memory embeddings
- Retrieve top-k similar memories (k=3-5)
- Filter by relevance threshold (>70%)
- Rank by relevance × importance × recency
- Present via Claude Code notification API

**Success Metrics:**
- >60% suggestion acceptance rate (user finds helpful)
- <3 suggestions per hour (not annoying)
- Relevance score >70% for all suggestions

**Dependencies:**
- Claude Code notification API
- Current file context access via MCP

---

### 8. Natural Language Queries

**User Value:** Conversational interface, easier discovery
**Implementation Complexity:** High (NLP, intent classification)

**Requirements:**
- [ ] Design conversational query interface
  - [ ] Support questions: "What did we decide about embeddings?"
  - [ ] Support commands: "Show me last week's work"
  - [ ] Support refinements: "Only decisions, not errors"
- [ ] Implement query intent understanding
  - [ ] Parse temporal references ("last week", "yesterday")
  - [ ] Extract entities (file names, technology names)
  - [ ] Detect event types ("decisions", "bugs", "milestones")
- [ ] Build multi-step query refinement
  - [ ] Initial broad query → "Too many results"
  - [ ] User refines: "Only from Phase 3"
  - [ ] System narrows: Shows refined results
- [ ] Create query expansion
  - [ ] Synonyms: "bugs" → "errors" + "failures"
  - [ ] Related terms: "authentication" → "auth" + "login" + "JWT"
- [ ] Add query history and suggestions
  - [ ] Remember past queries
  - [ ] Suggest similar queries
  - [ ] Auto-complete common patterns
- [ ] Implement conversational UI
  - [ ] Interactive mode: `/recall-chat`
  - [ ] Back-and-forth refinement
  - [ ] Context preservation across turns

**Technical Details:**
- Use spaCy or LLM for intent classification
- Extract temporal expressions with dateparser
- Map intents to retrieval modes (semantic/chronological/hybrid)
- Maintain conversation state for refinement
- Lightweight LLM for query understanding (optional, use Claude Code)

**Success Metrics:**
- >80% query intent correctly understood
- Average 1.5 queries to find desired memory (vs 2.5+ with manual)
- User satisfaction with conversational interface

**Dependencies:**
- NLP library (spaCy or Claude Code API)
- Conversation state management

---

### 9. Performance Dashboard

**User Value:** System insights, optimization opportunities
**Implementation Complexity:** Medium

**Requirements:**
- [ ] Design dashboard UI (web-based or CLI)
  - [ ] Real-time metrics display
  - [ ] Historical trends (7 days, 30 days)
  - [ ] Interactive charts (if web-based)
- [ ] Implement metrics collection
  - [ ] Query latency (p50, p95, p99)
  - [ ] Retrieval accuracy (relevance scores)
  - [ ] Storage usage (chunks, disk space)
  - [ ] Model performance (embedding time)
  - [ ] Cache hit rates
- [ ] Build analytics engine
  - [ ] Time-series storage (SQLite or InfluxDB)
  - [ ] Aggregation (hourly, daily, weekly)
  - [ ] Trend detection (performance degradation)
- [ ] Create alerting system
  - [ ] Latency spike alerts (>2x baseline)
  - [ ] Storage growth alerts (>80% capacity)
  - [ ] Accuracy drop alerts (<80% relevance)
- [ ] Add dashboard commands
  - [ ] `/recall-dashboard` - Open dashboard
  - [ ] `/recall-metrics` - CLI metrics summary
  - [ ] `/recall-trends` - Show 30-day trends

**Technical Details:**
- Collect metrics in UnifiedVectorStore
- Store in SQLite time-series table
- Generate charts with matplotlib (CLI) or Plotly (web)
- Dashboard served via Flask (if web-based)

**Success Metrics:**
- <1s dashboard load time
- Metrics collection overhead <5ms per query
- Clear visualization of performance trends

**Dependencies:** None

---

### 10. Session Recap (formerly "Summarization")

**User Value:** Conversational memory refresh, decision history
**Implementation Complexity:** Medium-High

**Requirements:**
- [ ] Design conversational recap system
  - [ ] NOT data compression (no information loss)
  - [ ] Intelligent timeline + semantic query combination
  - [ ] Natural language presentation
- [ ] Implement timeline-based queries
  - [ ] "What did we do last week?"
  - [ ] "Show me yesterday's decisions"
  - [ ] "What happened on October 10?"
- [ ] Implement decision history queries
  - [ ] "When did we move to version x?"
  - [ ] "Why did we choose Arctic embedder?"
  - [ ] "What were our considerations for multi-collection strategy?"
- [ ] Build intelligent event grouping
  - [ ] Group related events (e.g., debugging session = error + discovery + success)
  - [ ] Detect cause-effect relationships
  - [ ] Present as coherent narrative
- [ ] Create natural language presentation
  - [ ] Conversational tone, not data dump
  - [ ] Example: "Last week you worked on plugin support (Oct 11), implemented Apache 2.0 licensing (Oct 11), and completed Phase 3 testing (Oct 10)"
  - [ ] Highlight key decisions and outcomes
- [ ] Add recap commands
  - [ ] `/recall-recap --from 2025-10-01 --to 2025-10-07` - Date range recap
  - [ ] `/recall-recap --session phase3` - Session summary
  - [ ] `/recall-recap "Why did we switch to Apache 2.0?"` - Decision history

**Technical Details:**
- Combine chronological retrieval (time range) + semantic search (intent)
- Group events by session_id, timestamp proximity, semantic similarity
- Detect event sequences (error → discovery → success)
- Use Claude Code API for natural language generation (optional)
- Present as narrative, not raw JSON

**Success Metrics:**
- Recap captures 100% of events (no information loss)
- Natural language presentation rated >80% satisfaction
- Query latency <1s for 100 memories

**Dependencies:**
- Natural language generation (Claude Code API or template-based)

---

## 🚀 v2.0+ - Enterprise & Scale

**Focus:** Team collaboration, enterprise features, scale
**Target:** Q3-Q4 2025

### 11. Multi-User Support

**User Value:** Team collaboration, shared knowledge base
**Implementation Complexity:** High

**Requirements:**
- [ ] Design multi-user architecture
  - [ ] User authentication (OAuth, API keys)
  - [ ] User permissions (read, write, admin)
  - [ ] Shared vs private memories
- [ ] Implement user management
  - [ ] User registration, login, logout
  - [ ] Role-based access control (RBAC)
  - [ ] Team creation and management
- [ ] Add user-scoped memories
  - [ ] Filter by user (owner)
  - [ ] Share with specific users
  - [ ] Team-wide shared memories
- [ ] Create collaboration features
  - [ ] Memory comments/annotations
  - [ ] Memory approval workflows (for teams)
  - [ ] Activity feeds (who stored/accessed what)

**Success Metrics:**
- Support 100+ concurrent users
- <100ms overhead for permission checks
- Zero data leaks between users

**Dependencies:**
- Authentication service (OAuth provider or custom)
- User database (PostgreSQL)

---

### 12. Distributed Qdrant Setup

**User Value:** Scale to millions of memories, high availability
**Implementation Complexity:** High

**Requirements:**
- [ ] Design distributed architecture
  - [ ] Qdrant cluster setup (3+ nodes)
  - [ ] Sharding strategy (by user, by project, by time)
  - [ ] Replication for high availability
- [ ] Implement cluster management
  - [ ] Node discovery and health checks
  - [ ] Automatic failover
  - [ ] Load balancing across nodes
- [ ] Add distributed query routing
  - [ ] Route queries to appropriate shards
  - [ ] Merge results from multiple shards
  - [ ] Handle network partitions

**Success Metrics:**
- Scale to 10M+ memories
- <50ms query latency (99th percentile)
- 99.9% uptime

**Dependencies:**
- Qdrant cluster deployment
- Load balancer (HAProxy, NGINX)

---

### 13. Advanced Query DSL

**User Value:** Power users, complex queries
**Implementation Complexity:** Medium-High

**Requirements:**
- [ ] Design query DSL syntax
  - [ ] Boolean operators: AND, OR, NOT
  - [ ] Field filters: session:phase3, event:decision
  - [ ] Range queries: date:[2025-10-01 TO 2025-10-31]
  - [ ] Fuzzy matching: content:~"authentication"
- [ ] Implement DSL parser
  - [ ] Lexer/parser (ANTLR or pyparsing)
  - [ ] AST generation
  - [ ] Query optimization
- [ ] Add DSL commands
  - [ ] `/recall-query 'session:phase3 AND event:decision'`
  - [ ] `/recall-query 'date:[last-week TO today] AND NOT event:error'`

**Success Metrics:**
- Support 90% of common query patterns
- <20ms parsing overhead
- Clear error messages for invalid syntax

**Dependencies:** None

---

### 14. Memory Analytics & Insights

**User Value:** Understand memory usage patterns, optimize workflows
**Implementation Complexity:** Medium

**Requirements:**
- [ ] Build analytics engine
  - [ ] Memory access patterns (most/least accessed)
  - [ ] Session activity trends (busiest periods)
  - [ ] Event type distribution (decisions vs errors)
  - [ ] Query pattern analysis (common searches)
- [ ] Generate insights
  - [ ] "You haven't accessed Phase 2 memories in 30 days"
  - [ ] "Most accessed decision: Multi-collection strategy"
  - [ ] "Debugging pattern detected: 80% of errors on Fridays"
- [ ] Create analytics dashboard
  - [ ] Visual reports (charts, graphs)
  - [ ] Export to PDF/CSV
  - [ ] Scheduled reports (weekly, monthly)

**Success Metrics:**
- Generate actionable insights (>50% user follow-up rate)
- <5s report generation time
- Clear, understandable visualizations

**Dependencies:**
- Analytics database (SQLite or PostgreSQL)
- Visualization library (matplotlib, Plotly)

---

### 15. Third-Party API Integration

**User Value:** Extend Recall to other tools, custom integrations
**Implementation Complexity:** Medium

**Requirements:**
- [ ] Design RESTful API
  - [ ] Authentication (API keys, OAuth)
  - [ ] Rate limiting
  - [ ] Versioning (v1, v2)
- [ ] Implement API endpoints
  - [ ] POST /api/v1/memories - Ingest memory
  - [ ] GET /api/v1/memories/search - Search memories
  - [ ] GET /api/v1/memories/stats - Get statistics
- [ ] Create API documentation
  - [ ] OpenAPI/Swagger spec
  - [ ] Interactive docs (Swagger UI)
  - [ ] Code examples (Python, JavaScript, curl)
- [ ] Build client libraries
  - [ ] Python SDK
  - [ ] JavaScript SDK
  - [ ] CLI wrapper

**Success Metrics:**
- <100ms API response time (p95)
- >99% uptime
- Clear documentation with examples

**Dependencies:**
- API framework (FastAPI, Flask)
- API gateway (optional, for rate limiting)

---

## 📋 Immediate Next Steps (Post v1.3.3)

1. **Triage user feedback from plugin testing** (Week 1)
   - Monitor GitHub issues for plugin-related bugs
   - Address installation friction points
   - Improve documentation based on user questions

2. **Begin Context Size Monitoring prototype** (Week 2-3)
   - Research Claude Code context API
   - Build basic monitoring POC
   - Test alert threshold accuracy

3. **Plan v1.4.0 sprint** (Week 4)
   - Break down features into 2-week sprints
   - Assign complexity estimates
   - Prioritize based on user feedback from v1.3.3

---

## 📝 Notes

**Prioritization Rationale:**
- **v1.4.0 focus:** Context management addresses #1 user pain point (context loss)
- **v1.5.0 focus:** Automation reduces manual work, increases adoption
- **v2.0+ focus:** Enterprise features come after individual UX is perfected

**User Feedback Integration:**
- Summarization clarified as "Session Recap" (conversational, no data loss)
- Multi-user and distributed features deprioritized (premature optimization)
- Import/export promoted (team collaboration, backup/restore needs)

**Key Success Metrics Across All Features:**
- **User Satisfaction:** >80% feature adoption rate
- **Performance:** <100ms overhead for new features
- **Quality:** >80% test coverage, CC ≤ 8
- **Reliability:** >99% uptime, graceful error handling

---

**Version:** v1.3.3 → v1.4.0 → v1.5.0 → v2.0+
**Status:** Roadmap finalized, ready for incremental development
**Last Updated:** 2025-10-11
