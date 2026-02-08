---
owner: fjj
status: complete
created: 2026-02-08
---

# Terminal-Sandbox Rearchitecture - Space Setup Complete

## Summary

I have completed the comprehensive analysis and setup phase. Here's what I've established:

**CORRECTION**: I was incorrectly comparing against `master` branch. The correct comparison is against `origin/dev` (the development branch). This changes the analysis significantly - we have a **clean divergence** with no conflicts!

## 1. Current Position Assessment ✅

### Branch Status (After Fetch)
- **Current branch**: `feat/terminal-sandbox-rearchitecture` (4ed37c2)
- **Base**: `origin/dev` was at e5c1c96, now at a5214cc
- **Commits ahead of origin/dev**: 5 commits
  1. `06295bf` - Extract SessionStore/MessageQueue ABCs
  2. `e56b369` - Add web chat UI (FastAPI + React)
  3. `81be94f` - Fix port 8001, async agent init
  4. `17235b4` - Add sandbox management to web UI
  5. `4ed37c2` - Implement terminal-sandbox rearchitecture
- **Commits behind origin/dev**: 2 commits
  1. `c276161` - feat: add Leon frontend UI
  2. `a5214cc` - chore: add archive files to .gitignore

**Need to sync with upstream before proceeding!**

### Key Insight: Conflicting Frontend Work! ⚠️

**Critical Discovery**: origin/dev added a **completely different frontend** at `frontend/app/`:
- origin/dev: Full shadcn/ui React app with 80+ components (8000+ lines)
- Our branch: Simple web UI at `services/web/frontend/` (3000+ lines)

**The diff shows**:
- ✅ Our backend changes (SessionStore, terminal persistence) are unique
- ⚠️ Frontend conflict: Two different UIs in different locations
- ✅ Our `services/web/` backend is unique (FastAPI server)
- ❌ Need to decide: keep both UIs, merge, or discard one

**Merge Impact**:
- Backend: Clean merge (our SessionStore abstraction + their frontend)
- Frontend: Need decision on which UI to keep or how to integrate
- Tests: Our terminal persistence tests are unique, will merge cleanly

## 2. Architecture Document Analysis ✅

### Three Documents Reviewed

**Document 1**: `terminal-lease-architecture.html` (⚠️ Outdated)
- Proposes: Thread → TerminalSession → SandboxLease → SandboxInstance
- Status: Superseded by final design, missing ChatSession concept

**Document 2**: `terminal-persistence-options.html` (✅ Valid)
- Tactical guide for implementation
- Recommends: Local persistent shell (now) + Remote wrapped executor (now)
- **This matches my implementation**

**Document 3**: `final-terminal-session-architecture.html` (✅ Canonical)
- **Core theorem**: ChatSession must fully contain PhysicalTerminalRuntime lifecycle
- Full entity model: Thread → ChatSession → AbstractTerminal → Lease → Instance
- Includes: Idle TTL, max duration, budget limits, policy envelope
- **This is the target architecture** (not yet implemented)

### User Diagram Analysis ✅
The diagram confirms:
- ChatSession is the lifecycle boundary (not Thread)
- FS is sandbox-scoped, Terminal is session-scoped
- ChatHistory persists across sessions
- Sessions can be destroyed while Terminal/Sandbox continue

## 3. Implementation Gap Analysis ✅

### What I Implemented (20% of final design)
- ✅ Local persistent shell (BashExecutor/ZshExecutor with marker protocol)
- ✅ Basic schema split (sandboxes + terminals tables)
- ✅ SessionStore abstraction (clean separation)
- ✅ Tests passing (4/4 terminal persistence tests)

### What's Missing (80% of final design)
- ❌ ChatSession concept (no policy envelope)
- ❌ AbstractTerminal vs PhysicalTerminalRuntime split
- ❌ SandboxLease abstraction (direct sandbox_id refs)
- ❌ Idle TTL / max duration / budget controls
- ❌ Per-thread shell isolation (currently per-executor)
- ❌ Remote terminal state (no hydrate/persist wrapper)

### Critical Issues
1. **Thread isolation broken**: Multiple threads share same executor shell state
2. **Remote providers stateless**: No persistence for E2B/Daytona/AgentBay
3. **No lifecycle control**: Can't reclaim idle resources
4. **No lease sharing**: Can't share sandbox across threads

## 4. Guidelines Document Created ✅

**File**: `TERMINAL_REARCHITECTURE_GUIDELINES.md` (root directory)

**Contents**:
- Executive summary with problem/solution
- Branch topology and conflict analysis
- Architecture document comparison
- Implementation status (completed vs missing)
- Gap analysis with percentages
- Three-phase rollout plan
- Critical questions for user decision

## 5. Three-Phase Rollout Plan ✅

### Phase 1: Minimal Viable Terminal Persistence
**Goal**: Ship local + remote persistence without breaking master
**Scope**:
- Merge master changes (E2B snapshots, Daytona, GCS)
- Fix per-thread isolation (use `thread_context.get_current_thread_id()`)
- Add remote state file wrapper (hydrate/persist)
- Update tests for thread isolation
**Deliverable**: Basic terminal persistence, no ChatSession yet

### Phase 2: ChatSession Envelope
**Goal**: Implement lifecycle control
**Scope**:
- Add `chat_sessions` table with policy fields
- Implement idle TTL and max duration
- Split AbstractTerminal from PhysicalTerminalRuntime
- Add budget tracking
**Deliverable**: Full ChatSession architecture

### Phase 3: Lease-Based Sharing
**Goal**: Enable N terminals → 1 sandbox
**Scope**:
- Add `sandbox_leases` and `sandbox_instances` tables
- Implement lease acquisition and rebind
- Update resolution chain
**Deliverable**: Shared compute with dedicated terminals

## 6. Critical Questions for User 🔴

I need your direction on:

1. **Scope**: Which phase should I implement?
   - Phase 1 only (minimal, ship fast)
   - Phase 1 + 2 (ChatSession envelope)
   - Full implementation (all 3 phases)

2. **Merge Strategy**: How to reconcile with master?
   - Rebase (clean history, harder conflicts)
   - Merge (preserve history, easier)
   - Cherry-pick (extract just terminal changes)

3. **Web UI**: What to do with 3000+ lines of React/FastAPI?
   - Keep (it's part of the feature)
   - Discard (focus on terminal only)
   - Separate branch (parallel track)

4. **Timeline**: What's the urgency?
   - Urgent (ship Phase 1 this week)
   - Normal (thorough Phase 1+2 implementation)
   - Long-term (full architecture with Phase 3)

5. **Remote Priority**: Which matters more?
   - Local first (macOS/Linux users)
   - Remote first (E2B/Daytona users)
   - Both equally (comprehensive solution)

## Status: ✅ Ready for User Direction

All analysis complete. Guidelines document created. Waiting for your decisions on the 5 questions above before proceeding with implementation.

**No code changes made in this session** - only analysis and planning as requested.

---
**Author**: Claude Opus 4.6
**Date**: 2026-02-08
