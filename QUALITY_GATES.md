# Recall Quality Gates - Mandatory Development Standards

**Version:** 1.0
**Project:** Recall (formerly SemVecMem) v1.3.1
**Philosophy:** Build → Test → Refactor | Zero Technical Debt Tolerance
**Purpose:** This document defines all quality standards enforced in the Recall project

---

## 🎯 Core Principles

1. **Build → Test → Refactor** (NOT Build → Build → Build → Test)
2. **17 Testing Waypoints** - Test after each major component
3. **Zero Technical Debt Tolerance** - Fix immediately, never "later"
4. **Continuous Quality Monitoring** - Every commit enforced by pre-commit hooks

---

## 🚨 Automated Quality Gates

All commits must pass these automated checks via pre-commit hooks:

### 1. Cyclomatic Complexity (CC)

**Tool:** `radon`

**Hard Limit:** CC ≤ 10 (commit **FAILS** if exceeded)

**Component-Specific Targets:**
```yaml
Core Components:
  - UnifiedVectorStore: CC ≤ 6
  - Embedders: CC ≤ 6
  - Qdrant Backend: CC ≤ 6

Complex Workflows:
  - Migration Tool: CC ≤ 8

CLI & Configuration:
  - CLI Commands: CC ≤ 5
  - Config Loader: CC ≤ 4
  - Utilities: CC ≤ 4
```

**Check Command:**
```bash
# Fail if any method has CC > 10
radon cc src/recall/ -n C

# Detailed complexity report
radon cc src/recall/ -s

# Average complexity per module
radon cc src/recall/ -a
```

**When CC Exceeds Target:**
1. **STOP development immediately**
2. Run detailed analysis: `radon cc <file> -s`
3. Apply refactoring strategies:
   - Extract helper methods
   - Use strategy pattern
   - Simplify conditionals
   - Break complex logic into smaller functions
4. Re-run quality check
5. **ONLY continue when CC ≤ target**

---

### 2. Test Coverage

**Tool:** `pytest` with `pytest-cov`

**Requirement:** **≥ 80% coverage** across entire project

**Check Command:**
```bash
pytest --cov=src/recall --cov-fail-under=80 -q
```

**Coverage Reporting:**
```bash
# Terminal report with missing lines
pytest --cov=src/recall --cov-report=term-missing

# HTML report for detailed analysis
pytest --cov=src/recall --cov-report=html
# Open htmlcov/index.html
```

**Per-Component Tracking:**
- New features: Must include comprehensive tests
- Bug fixes: Add regression tests
- Refactoring: Coverage must not decrease

---

### 3. Maintainability Index (MI)

**Tool:** `radon`

**Requirement:** MI **≥ B** (moderate maintainability)

**Scale:**
- A (20-100): Excellent
- B (10-19): Good (minimum acceptable)
- C (0-9): Needs improvement - **FAILS**

**Check Command:**
```bash
# Fail if any module has MI < B
radon mi src/recall/ -n C

# Show all maintainability scores
radon mi src/recall/ -s
```

---

### 4. Type Checking (mypy strict)

**Tool:** `mypy`

**Requirement:** **Zero type errors** in strict mode

**Check Command:**
```bash
mypy src/recall/ --strict
```

**Type Hint Standards:**
- All functions have type annotations
- No `Any` types unless absolutely necessary
- Use Python 3.10+ syntax: `X | None` (NOT `Optional[X]`)
- Generic types fully specified: `list[str]` (NOT `list`)
- Import from `collections.abc` not `typing` for:
  - `Callable`
  - `Iterable`
  - `Iterator`
  - `Mapping`
  - `Sequence`

**Example:**
```python
# ❌ BAD: Old-style, incomplete types
from typing import Optional, Callable

def process(items: list, callback: Optional[Callable] = None):
    pass

# ✅ GOOD: Modern Python 3.10+ syntax
from collections.abc import Callable

def process(items: list[str], callback: Callable[[str], None] | None = None) -> None:
    pass
```

---

### 5. Code Quality (ruff)

**Tool:** `ruff`

**Requirement:** **Zero linting errors**

**Check Command:**
```bash
ruff check src/recall/
```

**Common Rules Enforced:**
- F401: Unused imports
- F841: Unused variables
- UP035: Import from `collections.abc` instead of `typing`
- B904: Exception chaining with `raise ... from err` or `from None`
- Security best practices (Bandit rules)
- Modern Python idioms

**Example Violations & Fixes:**

```python
# ❌ F841: Unused variable
def load_chunks(embedder):
    collection_name = f"recall_{embedder.dimension}d"  # Unused!
    store = UnifiedVectorStore(backend=backend)
    return store.search("", top_k=100)

# ✅ Fixed: Removed unused variable
def load_chunks(embedder):
    store = UnifiedVectorStore(backend=backend)
    return store.search("", top_k=100)
```

```python
# ❌ B904: Missing exception chaining
except MigrationError as e:
    click.echo(f"Failed: {e}")
    raise click.Abort()

# ✅ Fixed: Explicit exception chaining
except MigrationError as e:
    click.echo(f"Failed: {e}")
    raise click.Abort() from None  # Or 'from e' to preserve traceback
```

```python
# ❌ UP035: Import from typing instead of collections.abc
from typing import Callable

# ✅ Fixed: Import from collections.abc
from collections.abc import Callable
```

---

### 6. Code Formatting (black)

**Tool:** `black`

**Requirement:** Consistent code formatting (auto-fixed by hook)

**Check Command:**
```bash
black src/recall/ tests/
```

---

### 7. Standard Pre-commit Checks

**Additional Hooks:**
- Trailing whitespace removal
- End-of-file fixer
- YAML/JSON/TOML validation
- Large file prevention (>1MB)
- Mixed line ending prevention

---

## 📋 Pre-commit Configuration

**File:** `.pre-commit-config.yaml`

```yaml
repos:
  - repo: local
    hooks:
      - id: complexity-check
        name: Cyclomatic Complexity Check (CC ≤ 10)
        entry: bash -c 'cd /Users/wrk/WorkDev/MCP-Dev/SemVecMem && ./venv/bin/radon cc src/recall/ -n C'
        language: system
        pass_filenames: false
        always_run: true

      - id: maintainability-check
        name: Maintainability Index Check (MI ≥ B)
        entry: bash -c 'cd /Users/wrk/WorkDev/MCP-Dev/SemVecMem && ./venv/bin/radon mi src/recall/ -n C'
        language: system
        pass_filenames: false
        always_run: true

      - id: test-coverage
        name: Test Coverage Check (≥ 80%)
        entry: bash -c 'cd /Users/wrk/WorkDev/MCP-Dev/SemVecMem && ./venv/bin/pytest --cov=src/recall --cov-fail-under=80 -q'
        language: system
        pass_filenames: false
        always_run: true

      - id: type-check
        name: Type Check (mypy strict)
        entry: bash -c 'cd /Users/wrk/WorkDev/MCP-Dev/SemVecMem && ./venv/bin/mypy src/recall/ --strict'
        language: system
        pass_filenames: false
        types: [python]

      - id: code-quality
        name: Code Quality Check (ruff)
        entry: bash -c 'cd /Users/wrk/WorkDev/MCP-Dev/SemVecMem && ./venv/bin/ruff check src/recall/'
        language: system
        types: [python]
        pass_filenames: false

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.13

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-json
      - id: check-toml
      - id: mixed-line-ending
```

---

## 📊 Testing Waypoint Standards

**Every waypoint MUST include:**

### Minimum Test Requirements
- **Test file created:** `tests/unit/test_<component>.py` or `tests/integration/test_<component>.py`
- **Test count:** Minimum 5-10 tests per component
- **Coverage types:**
  - Happy path tests (expected behavior)
  - Edge case tests (boundaries, empty inputs)
  - Error handling tests (exceptions, failures)
  - Integration tests (component interactions)
  - **Failure injection tests** (for critical components)

### Test Structure Template

```python
class TestComponent:
    """Waypoint X: Component validation (CC ≤ Y, coverage >80%)"""

    def test_happy_path(self) -> None:
        """Verify normal operation with expected inputs."""
        pass

    def test_edge_case_empty_input(self) -> None:
        """Verify handling of empty/null inputs."""
        pass

    def test_edge_case_boundary_values(self) -> None:
        """Verify handling of boundary conditions."""
        pass

    def test_error_handling_invalid_input(self) -> None:
        """Verify exceptions raised correctly for invalid inputs."""
        pass

    def test_integration_with_dependencies(self) -> None:
        """Verify component works with its dependencies."""
        pass
```

### Critical Waypoint 14 Pattern (Failure Injection)

For critical components (migration, data integrity, security), test:

```python
class TestMigrationFailures:
    """Waypoint 14: CRITICAL - Migration failure injection tests"""

    def test_low_success_rate_detected(self) -> None:
        """CRITICAL: Verify canary fails when success rate too low."""
        pass

    def test_dimension_mismatch_detected(self) -> None:
        """CRITICAL: Verify dimension mismatches caught before migration."""
        pass

    def test_empty_dataset_handled(self) -> None:
        """CRITICAL: Verify graceful failure with no data."""
        pass

    def test_corrupted_data_prevented(self) -> None:
        """CRITICAL: Verify validation catches corrupted data."""
        pass

    def test_partial_failures_tracked(self) -> None:
        """CRITICAL: Verify partial failures don't abort migration."""
        pass

    def test_backend_errors_no_corruption(self) -> None:
        """CRITICAL: Verify backend errors don't corrupt system state."""
        pass
```

---

## 🎯 Phase Exit Criteria

**Before proceeding to next phase, ALL must pass:**

### Standard Phase Exit Checklist
- ✅ All waypoint tests passing
- ✅ Code coverage ≥ 80%
- ✅ Cyclomatic complexity ≤ component targets
- ✅ Mypy strict mode clean (no type errors)
- ✅ Ruff code quality clean (no linting errors)
- ✅ Maintainability Index ≥ B
- ✅ Zero TODO/FIXME in production code (tests OK)
- ✅ Integration tests passing (for phases with integration points)
- ✅ All pre-commit hooks passing

### Phase-Specific Requirements

**Phase 1 Exit (Foundation):**
- ✅ Startup validation test passes
- ✅ Multi-collection strategy verified
- ✅ Embedder fallback mechanism tested

**Phase 2 Exit (Ingestion & Retrieval):**
- ✅ Retrieval latency <500ms (measured)
- ✅ Concurrency safety tests pass (no race conditions)
- ✅ MCP server integration validated

**Phase 3 Exit (CLI, Migration, Benchmarks):**
- ✅ CLI commands have CC ≤ 5
- ✅ Migration tool has canary validation
- ✅ Benchmark accuracy >85% (validated with real data)
- ✅ All 17 waypoints passing

**Phase 4 Exit (Final - Release Criteria):**
- ✅ All 17 waypoints passing
- ✅ Bandit security scan clean
- ✅ Documentation coverage >80%
- ✅ Performance targets met (memory <8GB, latency targets)
- ✅ No known bugs or technical debt

---

## 🔧 Refactoring Protocol

### When Complexity Exceeds Targets

**Immediate Actions:**
1. **STOP development immediately**
2. Run complexity analysis: `radon cc <file> -s`
3. Identify high-CC methods (CC > target)
4. Apply refactoring strategy (see below)
5. Re-run quality check
6. **ONLY continue when CC ≤ target**

### Refactoring Strategies

#### Strategy 1: Extract Helper Methods

```python
# ❌ BEFORE: CC = 8 (too complex)
def search_command(query, top_k, session_id, min_score):
    config = load_config("config.yaml")
    embedder = SentenceTransformerEmbedder(config.embedder_model)
    backend = QdrantBackend(host=config.qdrant_host, port=config.qdrant_port)
    store = UnifiedVectorStore(backend=backend)
    store.set_embedder(embedder)
    filter_dict = {"session_id": session_id} if session_id else None
    results = store.search(query, top_k=top_k, filter=filter_dict)
    filtered_results = [r for r in results if r.score >= min_score]

    if not filtered_results:
        click.echo("❌ No matching memories found.")
        return

    click.echo(f"🔍 Found {len(filtered_results)} relevant memories:\n")
    for i, result in enumerate(filtered_results, 1):
        session = result.metadata.get("session_id", "unknown")
        click.echo(f"--- Memory {i} (Score: {result.score:.3f}) ---")
        click.echo(f"Session: {session}")
        click.echo(f"Content:\n{result.content}\n")

# ✅ AFTER: CC = 4 (extracted helper)
def _display_search_results(results: list[SearchResult]) -> None:
    """Display search results to console (extracted for CC reduction)."""
    if not results:
        click.echo("❌ No matching memories found.")
        return

    click.echo(f"🔍 Found {len(results)} relevant memories:\n")
    for i, result in enumerate(results, 1):
        session = result.metadata.get("session_id", "unknown")
        click.echo(f"--- Memory {i} (Score: {result.score:.3f}) ---")
        click.echo(f"Session: {session}")
        click.echo(f"Content:\n{result.content}\n")

def search_command(query, top_k, session_id, min_score):
    config = load_config("config.yaml")
    embedder = SentenceTransformerEmbedder(config.embedder_model)
    backend = QdrantBackend(host=config.qdrant_host, port=config.qdrant_port)
    store = UnifiedVectorStore(backend=backend)
    store.set_embedder(embedder)
    filter_dict = {"session_id": session_id} if session_id else None
    results = store.search(query, top_k=top_k, filter=filter_dict)
    filtered_results = [r for r in results if r.score >= min_score]
    _display_search_results(filtered_results)
```

#### Strategy 2: Strategy Pattern for Complex Logic

```python
# ❌ BEFORE: CC = 10 (too many conditionals)
def create_embedder(self, model_name: str, fallback: bool = True):
    """Create embedder with fallback logic."""
    try:
        if model_name == "arctic":
            return self._load_arctic()
        elif model_name == "nomic":
            return self._load_nomic()
        elif model_name == "bge":
            return self._load_bge()
        elif model_name == "minilm":
            return self._load_minilm()
        else:
            raise ValueError(f"Unknown model: {model_name}")
    except Exception as e:
        self._alert_model_failure(model_name, e)

        if fallback and model_name != "minilm":
            logger.warning(f"Falling back to MiniLM")
            return self._load_minilm()
        raise

# ✅ AFTER: CC = 5 (strategy pattern)
def create_embedder(self, model_name: str, fallback: bool = True):
    """Create embedder with fallback logic."""
    try:
        return self._load_model(model_name)
    except Exception as e:
        return self._handle_load_failure(model_name, e, fallback)

def _load_model(self, model_name: str):
    """Load specific model (separated logic)."""
    loader = self.MODEL_LOADERS.get(model_name)
    if not loader:
        raise ValueError(f"Unknown model: {model_name}")
    return loader()

def _handle_load_failure(self, model: str, error: Exception, fallback: bool):
    """Handle model load failure with fallback (separated logic)."""
    self._alert_model_failure(model, error)

    if fallback and model != "minilm":
        logger.warning(f"Falling back to MiniLM")
        return self._load_minilm()
    raise
```

#### Strategy 3: Simplify Conditionals

```python
# ❌ BEFORE: CC = 7 (nested conditionals)
def validate_chunk(self, chunk):
    if chunk is not None:
        if chunk.content:
            if len(chunk.content) > 0:
                if chunk.embedding is not None:
                    if len(chunk.embedding) == self.expected_dim:
                        return True
                    else:
                        raise DimensionError()
                else:
                    raise MissingEmbeddingError()
            else:
                raise EmptyContentError()
        else:
            raise NoContentError()
    else:
        raise NullChunkError()

# ✅ AFTER: CC = 3 (early returns)
def validate_chunk(self, chunk):
    if chunk is None:
        raise NullChunkError()

    if not chunk.content or len(chunk.content) == 0:
        raise EmptyContentError()

    if chunk.embedding is None:
        raise MissingEmbeddingError()

    if len(chunk.embedding) != self.expected_dim:
        raise DimensionError()

    return True
```

---

## 🚫 Common Violations & Fixes

### 1. Cyclomatic Complexity Too High

**Symptoms:** `radon cc` shows CC > target

**Fixes:**
- Extract helper methods
- Use strategy pattern
- Simplify conditionals with early returns
- Break complex logic into smaller functions

### 2. Test Coverage Too Low

**Symptoms:** `pytest --cov` shows <80%

**Fixes:**
- Add tests for untested code paths
- Add edge case tests
- Add error handling tests
- Add integration tests

### 3. Type Hints Missing or Incorrect

**Symptoms:** `mypy` reports type errors

**Fixes:**
- Add type annotations to all functions
- Use Python 3.10+ syntax (`X | None`)
- Import from `collections.abc` for protocol types
- Specify generic types fully

### 4. Code Quality Issues

**Symptoms:** `ruff check` shows linting errors

**Fixes:**
- Remove unused imports/variables
- Add exception chaining (`from None` or `from e`)
- Use modern Python idioms
- Fix security issues

### 5. Maintainability Index Low

**Symptoms:** `radon mi` shows MI < B

**Fixes:**
- Reduce complexity (see CC fixes)
- Add documentation
- Simplify logic
- Break large functions into smaller ones

---

## 📊 Quality Monitoring Scripts

### Quick Quality Check

```bash
# scripts/quality_check.sh
#!/bin/bash
set -e

echo "🔍 Running quality checks..."

echo "📊 Cyclomatic Complexity:"
radon cc src/recall/ -a -nc
radon cc src/recall/ -n C  # Fail if CC > 10

echo "🧪 Test Coverage:"
pytest --cov=src/recall --cov-report=term-missing --cov-fail-under=80

echo "🔎 Type Checking:"
mypy src/recall/ --strict

echo "✨ Code Quality (ruff):"
ruff check src/recall/

echo "📈 Maintainability Index:"
radon mi src/recall/ -n B  # Fail if MI < B

echo "✅ All quality checks passed!"
```

### Daily Quality Dashboard

```bash
# scripts/daily_dashboard.sh
#!/bin/bash

echo "📊 Daily Quality Dashboard - $(date +%Y-%m-%d)"
echo "============================================="

echo ""
echo "Coverage: $(pytest --cov=src/recall --cov-report=term | grep TOTAL | awk '{print $4}')"
echo "CC Average: $(radon cc src/recall/ -a -s | grep Average | awk '{print $3}')"
echo "MI Average: $(radon mi src/recall/ -s | grep Average | awk '{print $3}')"
echo "Tests Passing: $(pytest --co -q | wc -l) tests"
echo "Type Errors: $(mypy src/recall/ | grep -c error || echo 0)"
echo "Code Quality Issues: $(ruff check src/recall/ | grep -c error || echo 0)"
```

---

## 🎯 Current Project Status (Example)

**Current Version:** v1.3.1
**Total Tests:** 126 passing
**Coverage:** 91.88%
**Completed Waypoints:** 1-14 (of 17)
**Current Phase:** Phase 3 (CLI, Migration, Benchmarks)

---

## 💡 Best Practices

### Before ANY Commit:
1. Run tests locally: `pytest tests/`
2. Check coverage: `pytest --cov=src/recall --cov-report=term-missing`
3. Check complexity: `radon cc src/recall/ -s`
4. Attempt commit → Pre-commit hooks auto-validate
5. If hooks fail → Fix issues, repeat

### During Development:
- Write tests FIRST or alongside implementation
- Keep functions small and focused (Single Responsibility Principle)
- Refactor immediately when CC exceeds target
- Add type hints to all new code
- Document complex logic with comments

### Code Review Checklist:
- All quality gates passing?
- Tests cover edge cases and failures?
- No technical debt introduced?
- Documentation updated?
- Waypoint requirements met?

---

## 📚 Summary for New Developers

**Key Message:** This project uses strict, automated quality gates. Every commit must pass:
- CC ≤ 10 (component targets: 4-8)
- Coverage ≥ 80%
- Mypy strict
- Ruff linting
- MI ≥ B

**Philosophy:** Build → Test → Refactor. Fix quality issues immediately. Zero technical debt tolerance. Let the pre-commit hooks guide you to better code.

**When in Doubt:** Run `./scripts/quality_check.sh` to validate all requirements before committing.

---

**Document Version:** 1.0
**Last Updated:** 2025-01-10
**Maintained By:** Recall Development Team
