# V1 Gap Analysis: Current V4 vs V1 Requirements

Date: 2026-02-15

## Current State (V4 Implementation)

**What We Have:**
- Slide-out panel for thread inspector (master-detail pattern)
- Basic sandbox status filtering (active/all/idle/paused)
- System overview with run stats (running/completed/errors/stuck)
- Stuck runs panel with clickable items
- Top errors panel
- Search by thread_id/run_id/text
- Sandboxes table with basic info (status/thread/provider/state/last_active/cwd)
- Thread detail view with runs list and event timeline
- Event tailing for live updates

**What's Missing (V1 Requirements):**

## 1. Ground Truth Main Table

**V1 Requirement:**
- Fields: provider/thread_id/chat_session_id/lease_id/instance_id/observed_state/desired_state/last_active/source
- Stable sorting - no flicker on refresh
- Show real resource occupancy

**Current Gap:**
- Sandboxes table only shows: status/thread/provider/state/last_active/cwd
- Missing: chat_session_id, lease_id, instance_id, desired_state, source
- No stable refresh (clears and redraws on every fetch)
- No visual indication of state convergence (observed vs desired)

**Implementation Needed:**
- Backend: Extend `/api/operator/sandboxes` to return full ground truth fields
- Frontend: Preserve old data until new data arrives (no flash)
- Add columns for lease_id, instance_id, desired_state
- Visual indicator when observed_state != desired_state

## 2. Orphan Resource Panel

**V1 Requirement:**
- Show orphan/untracked instances
- Actions: adopt / destroy
- Make orphans discoverable and actionable

**Current Gap:**
- No orphan detection at all
- No orphan panel
- No adopt/destroy operations

**Implementation Needed:**
- Backend: `/api/operator/orphans` endpoint
  - Query provider APIs for all instances
  - Cross-reference with sandbox.db sessions
  - Return untracked instances
- Backend: `/api/operator/orphans/{instance_id}/adopt` POST endpoint
- Backend: `/api/operator/orphans/{instance_id}/destroy` POST endpoint
- Frontend: New "Orphan Resources" panel in dashboard
- Frontend: Action buttons for adopt/destroy with confirmation

## 3. Session Operations Convergence

**V1 Requirement:**
- pause/resume/destroy via unified API semantics
- Operations converge within one refresh cycle
- State changes are observable

**Current Gap:**
- No session operation buttons in UI
- No pause/resume/destroy actions exposed
- No convergence tracking

**Implementation Needed:**
- Backend: Unified session operation endpoints
  - POST `/api/operator/sessions/{thread_id}/pause`
  - POST `/api/operator/sessions/{thread_id}/resume`
  - POST `/api/operator/sessions/{thread_id}/destroy`
- Frontend: Action buttons in sandbox table rows
- Frontend: Optimistic UI updates + convergence indicator
- Frontend: Operation result feedback (success/error/pending)

## 4. Provider Event View

**V1 Requirement:**
- Show webhook/event records
- Support troubleshooting and tracing
- Make state changes explainable

**Current Gap:**
- No provider event view
- No webhook history
- Can't trace why a sandbox changed state

**Implementation Needed:**
- Backend: `/api/operator/provider-events` endpoint
  - Query provider webhook/event logs
  - Filter by thread_id, provider, time range
- Frontend: New "Provider Events" section in thread detail panel
- Frontend: Timeline view of provider events (similar to run events)
- Frontend: Link events to state transitions

## 5. Alert System Visualization

**Research Evidence:**
- Backend already has alert system with webhooks (from e2e tests)
- Stuck run detection exists
- No frontend visualization

**Current Gap:**
- Alerts exist in backend but not shown in UI
- No alert configuration UI
- No alert history view

**Implementation Needed:**
- Backend: `/api/operator/alerts` endpoint (list active alerts)
- Backend: `/api/operator/alerts/history` endpoint
- Frontend: Alert panel in dashboard (similar to stuck runs)
- Frontend: Alert detail view with trigger conditions
- Frontend: Alert acknowledgment/mute actions

## 6. Explore Mode (Grafana Pattern)

**Research Insight:**
- Grafana's "Explore" mode for ad-hoc queries
- Redash's "saved queries" as first-class objects
- Operators need flexible filtering beyond hard-coded views

**Current Gap:**
- Only pre-defined views (stuck runs, top errors)
- No ad-hoc query builder
- No saved query objects

**Implementation Needed:**
- Backend: `/api/operator/query` endpoint (flexible query DSL)
- Backend: `/api/operator/saved-queries` CRUD endpoints
- Frontend: "Explore" tab with query builder
- Frontend: Save/load queries
- Frontend: Query result visualization (table/timeline/chart)

## 7. Event-First Architecture (PostHog/Phoenix Pattern)

**Research Insight:**
- Append-only event ledger as source of truth
- Derived views computed from events
- OTel-aligned span model for tool calls

**Current Gap:**
- Events exist but not treated as primary artifact
- No event schema discipline
- No derived view recomputation

**Implementation Needed:**
- Backend: Formalize event schema (stable names + properties)
- Backend: Event ingestion API (if not already append-only)
- Backend: Materialized view refresh mechanism
- Documentation: Event catalog with schema definitions

## Priority Ranking (P0 = Must Have for V1)

**P0 - Core V1:**
1. Ground Truth table with full fields + stable refresh
2. Orphan resource panel + adopt/destroy actions
3. Session operations (pause/resume/destroy) + convergence
4. Provider event view

**P1 - High Value:**
5. Alert visualization (backend exists, just needs frontend)
6. Stable refresh (no flicker) for all tables

**P2 - Future Enhancement:**
7. Explore mode + saved queries
8. Event schema formalization + OTel alignment

## Implementation Strategy

**Phase 1: Backend API Completion (2-3 days)**
- Extend `/api/operator/sandboxes` with full ground truth fields
- Add `/api/operator/orphans` + adopt/destroy endpoints
- Add session operation endpoints (pause/resume/destroy)
- Add `/api/operator/provider-events` endpoint
- Add `/api/operator/alerts` endpoint

**Phase 2: Frontend Core Features (3-4 days)**
- Implement stable refresh (preserve old data until new arrives)
- Add orphan resource panel with actions
- Add session operation buttons to sandbox table
- Add provider events section to thread detail
- Add alert panel to dashboard

**Phase 3: E2E Testing (1-2 days)**
- Test pause/resume/destroy convergence
- Test orphan adopt/destroy flow
- Test alert triggering and display
- Verify no resource leaks

**Phase 4: Polish (1 day)**
- Loading states and error handling
- Confirmation dialogs for destructive actions
- Visual feedback for state convergence
- Documentation updates

## Estimated Total: 7-10 days for complete V1

## Next Steps

1. Review this gap analysis with team
2. Prioritize P0 items for immediate implementation
3. Create detailed API specs for new endpoints
4. Implement backend endpoints first (API-first approach)
5. Build frontend incrementally, testing each feature
6. E2E validation before marking V1 complete
