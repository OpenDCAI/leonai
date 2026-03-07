# Storage Layer Refactoring - Context Document

**Date:** 2026-03-07
**Branch:** feat/resource-page
**PR:** #135

## Session Summary

### Completed Work

1. **PR Cleanup**
   - Removed untracked screenshot files and plan docs
   - Removed all Co-Authored-By lines from 74 commits using git filter-branch
   - Discarded unrelated package-lock.json changes
   - Force pushed cleaned branch to update PR #135

2. **Code Review**
   - Used pr-review-toolkit:code-reviewer agent
   - Found 4 important issues (confidence 80-85%)
   - Fixed critical timezone bug: changed 'localtime' to 'utc' in `sandbox_monitor_repo.py:135`
   - Verified memory leak concern was already handled in docker.py

3. **Architectural Refactoring (Completed)**
   - **#1 Config Loading Centralization**
     - Created `backend/web/services/config_loader.py` with `SandboxConfigLoader` class
     - Removed scattered config loading logic from `resource_service.py`
     - Commit: aa2e1fd

   - **#2 Catalog Duplication**
     - Added `CATALOG_ENTRY` class attribute to all 5 provider classes:
       - `LocalSessionProvider`
       - `DockerProvider`
       - `DaytonaProvider`
       - `E2BProvider`
       - `AgentBayProvider`
     - Updated `resource_service.py` to build catalog from provider classes
     - Commit: 1c6657c

   - **#3 Frontend Session Counting Hook**
     - Added `useSessionCounts` hook to `SessionList.tsx` with memoization
     - Updated `ProviderDetail.tsx` to use shared hook
     - Eliminated duplicate filter logic
     - Commit: 36f8fa4

4. **Storage Layer Separation (Partial)**
   - Identified architectural violation: `sandbox/resource_snapshot.py` contained SQLite code
   - Created `storage/providers/sqlite/resource_snapshot_repo.py` with all SQLite operations
   - Updated `sandbox/resource_snapshot.py` to delegate to storage layer
   - Maintained backward compatibility via re-exports
   - Commit: 62c302b

## Current Problem: Broader Storage Layer Coupling

### Discovery

While fixing `resource_snapshot.py`, discovered that **7 files in the sandbox layer have SQLite imports**, violating separation of concerns:

| File | SQL Operations | Issue |
|------|----------------|-------|
| `terminal.py` | 19 | Terminal session persistence mixed with domain logic |
| `lease.py` | 17 | Lease lifecycle management mixed with SQL |
| `chat_session.py` | 10 | Chat session persistence mixed with domain logic |
| `runtime.py` | 10 | Runtime state persistence mixed with domain logic |
| `provider_events.py` | 5 | Event persistence mixed with domain logic |
| `manager.py` | 4 | Orchestration mixed with SQL |
| `capability.py` | 1 | Capability persistence mixed with domain logic |
| **Total** | **66** | **Entire sandbox layer coupled to SQLite** |

### Architectural Violation

**Current (incorrect):**
```
sandbox/
├── lease.py          # Domain logic + SQLite operations
├── terminal.py       # Domain logic + SQLite operations
├── chat_session.py   # Domain logic + SQLite operations
└── ...
```

**Correct architecture:**
```
sandbox/
├── lease.py          # Domain logic only
├── terminal.py       # Domain logic only
└── ...

storage/providers/sqlite/
├── lease_repo.py     # Lease persistence
├── session_repo.py   # Session persistence
└── ...
```

### Existing Storage Layer

The `storage/providers/sqlite/` directory already has:
- `checkpoint_repo.py`
- `file_operation_repo.py`
- `queue_repo.py`
- `resource_snapshot_repo.py` (just created)
- `run_event_repo.py`
- `sandbox_monitor_repo.py` (handles READ operations for leases, sessions, events)
- `summary_repo.py`
- `thread_config_repo.py`

**Key insight:** `sandbox_monitor_repo.py` already has READ methods:
- `query_leases()`, `query_lease()`, `query_lease_threads()`, `query_lease_events()`
- `query_threads()`, `query_thread_sessions()`
- `query_events()`, `query_event()`

The 7 files likely have WRITE operations (INSERT, UPDATE, DELETE) that need extraction.

## Refactoring Design Proposal

### User Constraints

1. **Don't create excessive repositories** - Minimize number of repo files
2. **Maximize code reuse** - Share common patterns and utilities
3. **Code quality is first priority** - Clean architecture over quick fixes

### Proposed Approach

**Option A: Extend sandbox_monitor_repo.py**
- Add write methods to existing `SandboxMonitorRepo` class
- Methods: `upsert_lease()`, `update_lease_state()`, `delete_lease()`, etc.
- Pro: Single source of truth for all sandbox storage
- Con: Large class, mixing reads and writes

**Option B: Create focused repositories**
- `LeaseRepository` - for lease.py (17 ops)
- `SessionRepository` - for terminal.py, chat_session.py, runtime.py (39 ops)
- `EventRepository` - for provider_events.py, capability.py (6 ops)
- Pro: Clear separation of concerns
- Con: More files, potential duplication

**Option C: Unified SandboxRepository**
- Single `SandboxRepository` class with all CRUD operations
- Organized by entity (leases, sessions, events, capabilities)
- Pro: Maximizes code reuse, single connection management
- Con: Large class

### Recommended: Option C (Unified SandboxRepository)

Create `storage/providers/sqlite/sandbox_repo.py`:

```python
class SandboxRepository:
    """Unified repository for all sandbox persistence operations."""

    # Lease operations
    def upsert_lease(self, lease_id: str, ...) -> None: ...
    def update_lease_state(self, lease_id: str, state: str) -> None: ...
    def delete_lease(self, lease_id: str) -> None: ...
    def get_lease(self, lease_id: str) -> dict | None: ...
    def list_leases(self) -> list[dict]: ...

    # Session operations
    def upsert_session(self, session_id: str, ...) -> None: ...
    def update_session(self, session_id: str, ...) -> None: ...
    def delete_session(self, session_id: str) -> None: ...
    def get_session(self, session_id: str) -> dict | None: ...

    # Event operations
    def insert_event(self, event: dict) -> None: ...
    def list_events(self, limit: int) -> list[dict]: ...

    # Capability operations
    def upsert_capability(self, provider: str, ...) -> None: ...
    def get_capability(self, provider: str) -> dict | None: ...
```

This maximizes code reuse by:
- Sharing connection management
- Sharing transaction handling
- Sharing common SQL patterns
- Keeping all sandbox storage in one place

### Implementation Strategy

**Phase 1: Create unified repository**
1. Create `storage/providers/sqlite/sandbox_repo.py`
2. Extract table schemas from the 7 files
3. Implement CRUD methods for each entity type
4. Add comprehensive tests

**Phase 2: Refactor domain objects**
1. Update `lease.py` to use `SandboxRepository`
2. Update `terminal.py` to use `SandboxRepository`
3. Update `chat_session.py` to use `SandboxRepository`
4. Update `runtime.py` to use `SandboxRepository`
5. Update `provider_events.py` to use `SandboxRepository`
6. Update `manager.py` to use `SandboxRepository`
7. Update `capability.py` to use `SandboxRepository`

**Phase 3: Cleanup**
1. Remove SQLite imports from sandbox layer
2. Remove direct SQL from sandbox layer
3. Update tests
4. Verify all functionality works

### Effort Estimation

- **Phase 1:** 2-3 hours (create repository, extract schemas, implement methods)
- **Phase 2:** 3-4 hours (refactor 7 files, update imports, fix integration)
- **Phase 3:** 1-2 hours (cleanup, testing, verification)
- **Total:** 6-9 hours

### Risk Assessment

**High risk areas:**
- `lease.py` (17 SQL ops) - Core sandbox lifecycle management
- `terminal.py` (19 SQL ops) - Terminal session management
- `runtime.py` (10 SQL ops) - Runtime state management

**Risks:**
- Breaking existing functionality
- Introducing subtle bugs in state management
- Performance regressions
- Test failures

**Mitigation:**
- Comprehensive testing after each file refactoring
- Incremental commits (one file at a time)
- Keep existing tests passing
- Add integration tests for repository layer

## Decision Point

**Three options presented to user:**

1. **Full refactoring now** - Extract all 66 SQL operations
   - Delays PR significantly (6-9 hours)
   - High risk of introducing bugs
   - Clean architecture achieved immediately

2. **Incremental** - Fix worst offenders only: `lease.py` (17), `terminal.py` (19)
   - Moderate effort (3-4 hours)
   - Reduces risk by limiting scope
   - Partial solution, leaves 30 SQL ops in sandbox layer

3. **Separate PR** - Ship current PR, do storage refactoring separately
   - No delay to current PR
   - Allows proper planning and testing
   - **Recommended approach**

## Current PR Status

**Commits on feat/resource-page:**
- 91a34d1: fix(monitor): use UTC instead of localtime in hours_diverged calculation
- aa2e1fd: refactor(services): centralize config loading to reduce coupling
- 36f8fa4: refactor(frontend): extract session counting to shared hook
- 1c6657c: refactor(providers): move catalog metadata into provider classes
- 62c302b: refactor(storage): move SQLite operations from sandbox to storage layer

**PR #135 includes:**
- UI redesign: sandbox cards with side-sheet detail panel
- Code review fixes: timezone bug
- Architectural refactoring: config loading, catalog, session counting, resource_snapshot

**Ready to merge:** Yes, pending decision on broader storage refactoring

## Next Steps

**Awaiting user decision on:**
1. Full refactoring now (option 1)
2. Incremental refactoring (option 2)
3. Separate PR (option 3) - **recommended**

**If option 3 chosen:**
1. Push current commits
2. Merge PR #135
3. Create new issue/PR for storage layer refactoring
4. Implement unified `SandboxRepository` in separate branch
5. Refactor 7 files incrementally with comprehensive testing

## Files to Watch

**Modified in this session:**
- `backend/web/services/config_loader.py` (new)
- `backend/web/services/resource_service.py`
- `frontend/app/src/pages/resources/SessionList.tsx`
- `frontend/app/src/pages/resources/ProviderDetail.tsx`
- `sandbox/providers/local.py`
- `sandbox/providers/docker.py`
- `sandbox/providers/daytona.py`
- `sandbox/providers/e2b.py`
- `sandbox/providers/agentbay.py`
- `storage/providers/sqlite/sandbox_monitor_repo.py`
- `storage/providers/sqlite/resource_snapshot_repo.py` (new)
- `sandbox/resource_snapshot.py`

**Files needing refactoring (if proceeding):**
- `sandbox/lease.py` (17 SQL ops)
- `sandbox/terminal.py` (19 SQL ops)
- `sandbox/chat_session.py` (10 SQL ops)
- `sandbox/runtime.py` (10 SQL ops)
- `sandbox/provider_events.py` (5 SQL ops)
- `sandbox/manager.py` (4 SQL ops)
- `sandbox/capability.py` (1 SQL op)

## Key Learnings

1. **Architectural violations compound** - One file (resource_snapshot.py) led to discovering 7 files with same issue
2. **Backward compatibility matters** - Re-exports allow incremental refactoring without breaking existing code
3. **Repository pattern scales** - Unified repository maximizes code reuse while maintaining clean boundaries
4. **Scope management critical** - 66 SQL operations across 7 files is a major refactoring, not a quick fix

## References

- PR #135: https://github.com/OpenDCAI/leonai/pull/135
- Code review agent output: Found 4 issues, fixed timezone bug
- Git rules: `.claude/rules/git.md` - Conventional Commits, small commits, single responsibility
- Architecture rules: `.claude/rules/codestyle.md` - No monkeypatch, strong typing, explicit error handling
