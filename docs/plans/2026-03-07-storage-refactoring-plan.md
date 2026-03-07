# Storage Layer Refactoring - Implementation Plan

**Date:** 2026-03-07
**Branch:** feat/resource-page
**Scope:** Extract 66 SQL operations from 7 sandbox files into unified storage layer

## Executive Summary

**Problem:** Sandbox domain layer has direct SQLite dependencies, violating separation of concerns.

**Solution:** Create unified `SandboxRepository` in storage layer, refactor 7 files to use it.

**Effort:** 6-9 hours (3 phases)
**Risk:** High (core lifecycle management)
**Approach:** Incremental, one file at a time, test after each

---

## Phase 1: Repository Design & Implementation (2-3 hours)

### 1.1 Analyze Table Schemas

**Files to analyze:**
- `sandbox/lease.py` - sandbox_leases, sandbox_instances, lease_events
- `sandbox/terminal.py` - abstract_terminals, thread_terminal_pointers
- `sandbox/chat_session.py` - chat_sessions, terminal_commands, terminal_command_chunks
- `sandbox/runtime.py` - (check for additional tables)
- `sandbox/provider_events.py` - (check for additional tables)
- `sandbox/capability.py` - (check for additional tables)

**Task:** Extract CREATE TABLE statements from all 7 files.

**Deliverable:** Table schema inventory document.

### 1.2 Design Repository Interface

**Goal:** Single `SandboxRepository` class with methods organized by entity.

**Entity groups:**
1. **Leases** - CRUD for sandbox_leases, sandbox_instances, lease_events
2. **Terminals** - CRUD for abstract_terminals, thread_terminal_pointers
3. **Sessions** - CRUD for chat_sessions
4. **Commands** - CRUD for terminal_commands, terminal_command_chunks
5. **Events** - INSERT for lease_events (write-only)
6. **Capabilities** - CRUD for provider capabilities (if separate table)

**Design principles:**
- Shared connection management (`_connect()` helper)
- Shared transaction handling (context managers)
- Consistent error handling
- Type hints for all methods
- Docstrings for public methods

**Deliverable:** Repository interface design (method signatures).

### 1.3 Create Repository File

**File:** `storage/providers/sqlite/sandbox_repo.py`

**Structure:**
```python
"""Unified repository for sandbox domain persistence."""

from __future__ import annotations
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from sandbox.config import DEFAULT_DB_PATH
from storage.providers.sqlite.kernel import connect_sqlite

class SandboxRepository:
    """Unified repository for all sandbox persistence operations."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path

    # Connection management
    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self.db_path)

    # Table creation (ensure_tables)
    def ensure_tables(self) -> None:
        """Create all sandbox tables if they don't exist."""
        pass

    # === LEASE OPERATIONS ===
    def upsert_lease(...) -> None: pass
    def update_lease_state(...) -> None: pass
    def get_lease(...) -> dict | None: pass
    def list_leases(...) -> list[dict]: pass
    def delete_lease(...) -> None: pass

    # === INSTANCE OPERATIONS ===
    def upsert_instance(...) -> None: pass
    def update_instance(...) -> None: pass
    def get_instance(...) -> dict | None: pass

    # === TERMINAL OPERATIONS ===
    def upsert_terminal(...) -> None: pass
    def update_terminal(...) -> None: pass
    def get_terminal(...) -> dict | None: pass
    def list_terminals_by_thread(...) -> list[dict]: pass
    def delete_terminal(...) -> None: pass

    # === TERMINAL POINTER OPERATIONS ===
    def upsert_terminal_pointer(...) -> None: pass
    def get_terminal_pointer(...) -> dict | None: pass
    def update_terminal_pointer(...) -> None: pass
    def delete_terminal_pointer(...) -> None: pass

    # === SESSION OPERATIONS ===
    def upsert_session(...) -> None: pass
    def update_session(...) -> None: pass
    def get_session(...) -> dict | None: pass
    def list_sessions(...) -> list[dict]: pass

    # === COMMAND OPERATIONS ===
    def insert_command(...) -> None: pass
    def get_commands_by_terminal(...) -> list[dict]: pass
    def delete_commands_by_terminal(...) -> None: pass

    # === EVENT OPERATIONS ===
    def insert_lease_event(...) -> None: pass
    def list_lease_events(...) -> list[dict]: pass
```

**Implementation order:**
1. Connection management + ensure_tables
2. Lease operations (most critical)
3. Instance operations
4. Terminal operations
5. Terminal pointer operations
6. Session operations
7. Command operations
8. Event operations

**Testing strategy:**
- Unit tests for each operation group
- Test with in-memory SQLite (`:memory:`)
- Test CRUD cycles (create → read → update → delete)
- Test transaction rollback on errors

**Deliverable:** `storage/providers/sqlite/sandbox_repo.py` with all methods implemented and tested.

---

## Phase 2: Incremental Refactoring (3-4 hours)

**Strategy:** Refactor one file at a time, test after each, commit after each.

**Order:** Start with highest-risk files first (most SQL operations).

### 2.1 Refactor lease.py (17 SQL ops) - HIGHEST RISK

**Current state:** Direct SQLite operations for lease lifecycle management.

**Changes:**
1. Add `SandboxRepository` import
2. Replace `_connect()` calls with `repo._connect()`
3. Replace CREATE TABLE with `repo.ensure_tables()`
4. Replace INSERT/UPDATE/DELETE with repo methods
5. Keep domain logic (state machine, validation)
6. Add backward compatibility layer if needed

**Testing:**
```bash
# Run lease-specific tests
pytest tests/sandbox/test_lease.py -v

# Run integration tests
pytest tests/integration/test_sandbox_lifecycle.py -v
```

**Commit message:** `refactor(storage): move lease persistence to SandboxRepository`

### 2.2 Refactor terminal.py (19 SQL ops) - HIGHEST RISK

**Current state:** Direct SQLite operations for terminal state management.

**Changes:**
1. Add `SandboxRepository` import
2. Replace `_connect()` calls with `repo._connect()`
3. Replace CREATE TABLE with `repo.ensure_tables()`
4. Replace INSERT/UPDATE/DELETE with repo methods
5. Keep domain logic (state snapshots, terminal pointers)

**Testing:**
```bash
pytest tests/sandbox/test_terminal.py -v
```

**Commit message:** `refactor(storage): move terminal persistence to SandboxRepository`

### 2.3 Refactor chat_session.py (10 SQL ops)

**Current state:** Direct SQLite operations for session lifecycle.

**Changes:**
1. Add `SandboxRepository` import
2. Replace SQL operations with repo methods
3. Keep domain logic (policy enforcement, lifecycle)

**Testing:**
```bash
pytest tests/sandbox/test_chat_session.py -v
```

**Commit message:** `refactor(storage): move session persistence to SandboxRepository`

### 2.4 Refactor runtime.py (10 SQL ops)

**Task:** Analyze SQL operations, refactor to use repository.

**Commit message:** `refactor(storage): move runtime persistence to SandboxRepository`

### 2.5 Refactor provider_events.py (5 SQL ops)

**Task:** Analyze SQL operations, refactor to use repository.

**Commit message:** `refactor(storage): move provider events to SandboxRepository`

### 2.6 Refactor manager.py (4 SQL ops)

**Task:** Analyze SQL operations, refactor to use repository.

**Commit message:** `refactor(storage): move manager persistence to SandboxRepository`

### 2.7 Refactor capability.py (1 SQL op)

**Task:** Analyze SQL operations, refactor to use repository.

**Commit message:** `refactor(storage): move capability persistence to SandboxRepository`

---

## Phase 3: Cleanup & Verification (1-2 hours)

### 3.1 Remove SQLite Imports

**Task:** Remove `import sqlite3` from all 7 sandbox files.

**Verification:**
```bash
# Should return no results
grep -r "import sqlite3" sandbox/*.py
```

**Commit message:** `refactor(storage): remove direct SQLite imports from sandbox layer`

### 3.2 Update Imports

**Task:** Ensure all files import from storage layer, not directly from sqlite3.

**Files to check:**
- All 7 refactored files
- Any files that import from the 7 files

### 3.3 Run Full Test Suite

**Commands:**
```bash
# Unit tests
pytest tests/sandbox/ -v

# Integration tests
pytest tests/integration/ -v

# E2E tests (if applicable)
pytest tests/e2e/ -v
```

**Success criteria:**
- All tests pass
- No SQLite imports in sandbox layer
- No direct SQL in sandbox layer
- Repository layer handles all persistence

### 3.4 Performance Verification

**Task:** Ensure refactoring didn't introduce performance regressions.

**Metrics to check:**
- Lease creation time
- Terminal state update time
- Session query time

**Method:** Compare before/after with simple benchmark script.

### 3.5 Documentation Update

**Files to update:**
- `docs/architecture/storage-layer.md` (if exists)
- `MEMORY.md` - Add refactoring notes
- Inline comments - Update @@@ markers if needed

---

## Risk Mitigation

### High-Risk Areas

1. **lease.py (17 ops)** - Core sandbox lifecycle
   - **Mitigation:** Test extensively, commit frequently, keep rollback plan

2. **terminal.py (19 ops)** - Terminal state management
   - **Mitigation:** Test state persistence, verify terminal pointers work

3. **chat_session.py (10 ops)** - Session lifecycle
   - **Mitigation:** Test session creation/closure, verify policy enforcement

### Rollback Plan

If refactoring breaks functionality:
1. Identify broken file
2. `git revert <commit>` for that file
3. Fix issue in repository layer
4. Re-apply refactoring

### Testing Strategy

**After each file refactoring:**
1. Run file-specific unit tests
2. Run integration tests
3. Manual smoke test (create session, run command, destroy)
4. Commit if all pass

**After all refactoring:**
1. Full test suite
2. E2E test with all providers
3. Performance benchmark
4. Code review

---

## Success Criteria

- [ ] All 66 SQL operations moved to `SandboxRepository`
- [ ] No `import sqlite3` in sandbox layer
- [ ] All tests pass
- [ ] No performance regressions
- [ ] Code review approved
- [ ] Documentation updated

---

## Estimated Timeline

| Phase | Tasks | Time | Risk |
|-------|-------|------|------|
| Phase 1 | Repository design & implementation | 2-3h | Medium |
| Phase 2 | Incremental refactoring (7 files) | 3-4h | High |
| Phase 3 | Cleanup & verification | 1-2h | Low |
| **Total** | | **6-9h** | **High** |

---

## Next Steps

1. **Decision:** Confirm approach (unified repository vs separate repos)
2. **Start Phase 1:** Analyze table schemas, design repository interface
3. **Implement:** Create `sandbox_repo.py` with all methods
4. **Test:** Unit tests for repository layer
5. **Refactor:** One file at a time, starting with lease.py
6. **Verify:** Full test suite, performance check
7. **Merge:** Create PR, request review

---

## Notes

- This refactoring is **separate from PR #135** (resources page redesign)
- Recommend creating new branch: `refactor/storage-layer-separation`
- Can be done incrementally over multiple sessions
- Each phase can be committed separately
- Rollback plan available if issues arise
