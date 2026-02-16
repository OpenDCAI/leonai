# Leon Operator Console Frontend - Design Handoff

## Project Context
**Location**: `/Users/lexicalmathical/Codebase/ACP/leonai/frontend/operator/`
**Purpose**: Operator console (中台) for monitoring Leon AI system - runs, sandboxes, events, errors
**Backend**: Proxied at `/api` (port 8001), returns JSON for overview, search, sandboxes, threads, runs, events

## Evolution History

### V0: Original "JSON Dumper"
- Every tab just rendered raw JSON in `<pre>` blocks
- No semantic rendering, no structure
- Stale closure bug: `afterId` captured at creation time, polling always re-fetched same events
- No cross-navigation between tabs
- Massive code duplication

### V1: First Structured Rewrite
**What we did:**
- Created proper structured views for all tabs
- Overview: stat cards (runs_by_status), stuck_runs table, top_errors list
- Sandboxes: table with columns (thread, provider, chat status, state, last active, cwd)
- Search: typed result cards with status badges, clickable thread_id links
- Thread: event timeline with type-specific formatting (text, tool_call/tool_result collapsible, errors highlighted)
- Fixed stale closure bug using refs for `afterId` and `runId`
- Added cross-navigation: clicking thread_id jumps to Thread tab
- Zero new dependencies (React-only)

**Build passed** but user feedback: "very strange and not informative/self-explanatory enough"

### V2: Information Architecture Redesign
**Root causes identified:**
- Radial gradient background looked like gaming site, not ops dashboard
- Cryptic labels ("3 DONE", "1 SANDBOXES") with no context
- Sparse layout wasted space — when healthy, page was 90% empty
- Developer noise in footer ("Backend: proxied at /api")
- No empty states or guidance text
- Thread tab had just an input box with no instructions
- Search had no hint about what's searchable

**Changes made:**
- **Visual**: Flat dark theme (--bg: #0f1117, --surface: #161922), removed gradients, GitHub/Grafana aesthetic
- **Labels**: "Total runs", "Running now", "Completed", "Active sandboxes" instead of "DONE"/"SANDBOXES"
- **Healthy states**: Explicit green boxes saying "No stuck runs", "No errors in the last 24h"
- **Context**: Time shown at top ("Last 24h · 3:52:22 PM")
- **Guidance**: Every tab has description text explaining what it does
- **Removed**: Footer with "Backend: proxied at /api" (developer noise)

**Build passed** but user feedback: "still quite strange... murky and strange... don't really get the point of this search pane"

## Current Issues (V2)

### 1. Search Tab Confusion
User doesn't understand the purpose of the Search tab. Looking at the API:
- Endpoint: `/api/search?q={query}`
- Returns: `{items: [{type, summary, thread_id, run_id, updated_at}]}`
- Purpose unclear from UI — what does it search? Why would I use this vs Thread inspector?

**Hypothesis**: Search is redundant. If you have a thread_id, you go to Thread tab. If you don't, what are you searching for? The description says "Search across runs, events, terminal commands, and sandbox sessions by ID or text" but that's too vague.

### 2. "Murky and Strange" UI
Despite flat theme, something still feels off. Possible issues:
- Too much uppercase text (panel headers, badges)
- Inconsistent information density (Overview is dense, other tabs are sparse)
- Color palette might be too muted (everything is shades of gray/blue)
- Navigation feels disconnected (tabs don't show what's inside)
- No visual hierarchy — everything has same weight

### 3. Missing Operator Workflows
The UI shows data but doesn't support actual operator tasks:
- **Triage**: When something breaks, how do I find the problem?
- **Investigation**: How do I drill from error → thread → events?
- **Monitoring**: What should I look at first when I open this?
- **Action**: Can I restart stuck runs? Kill sandboxes? Clear errors?

## API Surface (from api.ts)

```typescript
// Overview
GET /api/overview → {
  runs_by_status: {done, running, error, cancelled},
  stuck_runs: {count, cutoff_started_before, items: [{run_id, thread_id, started_at, input_message}]},
  top_errors: [{error, count, last_seen_at}],
  sandboxes: {active_sessions_count},
  window_hours: 24,
  generated_at: ISO8601
}

// Search
GET /api/search?q={query} → {
  items: [{type, summary, thread_id, run_id, updated_at}],
  count
}

// Sandboxes
GET /api/sandboxes → {
  items: [{thread_id, terminal_id, provider_name, chat_status, observed_state, last_active_at, cwd}],
  count
}

// Thread
GET /api/threads/{id}/runs → {thread_id, items: [{run_id, thread_id, sandbox, input_message, status, started_at, finished_at, error}]}
GET /api/threads/{id}/diagnostics → (unknown shape)
GET /api/threads/{id}/commands → (unknown shape)

// Run
GET /api/runs/{id} → {run_id, thread_id, sandbox, input_message, status, started_at, finished_at, error}
GET /api/runs/{id}/events?after_event_id={n} → {
  run_id, after_event_id,
  items: [{event_id, run_id, thread_id, event_type, payload, created_at}]
}
```

## Event Types (from EventItem component)
- `text`, `text_full`, `text_delta` → blue dot, shows content
- `tool_call` → blue dot, collapsible, shows name + args
- `tool_result` → green dot, collapsible, shows content
- `error` → red dot, highlighted, shows error
- `run_done`, `run_cancelled` → green/yellow dot
- `status` → gray dot, dimmed (state updates)

## Design Principles (from CLAUDE.md)
- **Minimal implementation**: Only write code that directly solves the problem
- **Print-based debugging**: No match-based, add console.log
- **@@@ comments**: Only for tricky parts
- **Fail loudly**: Never hide errors
- **No bureaucratic fluff**: Direct, factual communication

## Next Steps for V3

### Option A: Remove Search, Simplify to 3 Tabs
- **Overview**: Health dashboard (current)
- **Threads**: Merge Thread + Search — show recent threads list, click to inspect
- **Sandboxes**: Current sandboxes table

Rationale: Search is confusing and redundant. If you know the thread_id, you paste it. If you don't, you look at Overview (stuck runs, errors) or Sandboxes (active sessions) to find it.

### Option B: Redesign Search as "Recent Activity"
- Show recent runs/threads in chronological order
- Click to jump to Thread inspector
- Make it the default landing tab (not Overview)

Rationale: Operators want to see "what just happened" first, not aggregate stats.

### Option C: Workflow-Oriented Redesign
- **Triage**: Errors + stuck runs (current Overview top section)
- **Monitor**: Active runs + sandboxes (live view)
- **Inspect**: Thread/run deep dive (current Thread tab)
- **History**: Recent activity log (redesigned Search)

Rationale: Organize by operator task, not by data type.

## V3: Workflow-Oriented Redesign (IMPLEMENTED)

**Decision**: Chose Option A + workflow improvements. Removed Search tab entirely, redesigned Overview to be action-oriented.

### Changes Made

**1. Removed Search Tab**
- Deleted entire Search component (lines 184-239)
- Removed from tab navigation
- Removed `search` import from api.ts
- Rationale: Redundant with Thread inspector. If you have a thread_id, paste it in Thread tab. If you don't, find it via Overview (stuck runs/errors) or Sandboxes (active sessions).

**2. Redesigned Overview for Triage**
- **Health status header**: Shows "⚠️ Issues detected" or "✓ All systems operational" at top
- **Alert cards**: Large, prominent cards for errors and stuck runs (48px font, colored borders)
- **Status overview**: 4 stat cards showing Running, Completed, Active sandboxes, Total
- **Critical issues first**: Errors and stuck runs shown before stats when present
- **Removed**: "No stuck runs" / "No errors" green boxes (noise when healthy)
- **Improved**: Stuck runs table no longer has description text (obvious what it is)

**3. Simplified All Tabs**
- **Removed uppercase text**: Panel headers, section titles no longer use `text-transform: uppercase`
- **Removed description paragraphs**: "Live sandbox sessions with..." etc. — obvious from context
- **Larger page titles**: 20px font-weight 600 instead of 13px uppercase
- **Consistent layout**: All tabs use same header pattern (title + spacer + actions)

**4. Visual Improvements**
- **Color palette**: Switched to GitHub dark theme colors (better contrast)
  - --bg: #0d1117 (was #0f1117)
  - --accent: #58a6ff (was #5b9bf5)
  - --green: #3fb950 (was #3ddc84)
  - --red: #f85149 (was #f5555d)
- **Better button contrast**: Hover state now #21262d with #444c56 border
- **Improved badges**: Slightly more padding (3px vs 2px), better opacity (.15 vs .12)
- **Event timeline**: Better spacing, font-weight 500 on labels, line-height 1.5

**5. Information Hierarchy**
- **Page titles**: 20px bold (was 13px uppercase)
- **Section labels**: 14px semibold (was 12px uppercase)
- **Counts**: Shown inline with labels ("3 active sandboxes" vs "SANDBOXES: 3")
- **Alert cards**: 48px numbers for critical issues (vs 32px for normal stats)

### Build Status
✅ Type-check passes
✅ Build passes (207KB JS, 7.8KB CSS)
✅ Search tab removed successfully
✅ No runtime errors
⏳ Awaiting user feedback on "murky" feeling

### Key Metrics
- **Lines of code**:
  - App.tsx: 469 → 390 lines (-79, removed Search)
  - styles.css: 185 → 193 lines (+8, added alert cards)
  - components.tsx: 199 lines (unchanged)
- **Bundle size**: 208KB → 207KB (-1KB)
- **Tabs**: 4 → 3 (removed Search)

## Technical Debt

### Option A: Remove Search, Simplify to 3 Tabs
- **Overview**: Health dashboard (current)
- **Threads**: Merge Thread + Search — show recent threads list, click to inspect
- **Sandboxes**: Current sandboxes table

Rationale: Search is confusing and redundant. If you know the thread_id, you paste it. If you don't, you look at Overview (stuck runs, errors) or Sandboxes (active sessions) to find it.

### Option B: Redesign Search as "Recent Activity"
- Show recent runs/threads in chronological order
- Click to jump to Thread inspector
- Make it the default landing tab (not Overview)

Rationale: Operators want to see "what just happened" first, not aggregate stats.

### Option C: Workflow-Oriented Redesign
- **Triage**: Errors + stuck runs (current Overview top section)
- **Monitor**: Active runs + sandboxes (live view)
- **Inspect**: Thread/run deep dive (current Thread tab)
- **History**: Recent activity log (redesigned Search)

Rationale: Organize by operator task, not by data type.

## Technical Debt
- No TypeScript types for API responses (all `any`)
- No error retry logic
- No WebSocket for live updates (polling only)
- No pagination (assumes small datasets)
- No keyboard shortcuts
- No URL state (can't bookmark a thread inspection)

## Files
- `src/App.tsx` — main component, all tab logic (469 lines)
- `src/components.tsx` — reusable UI (StatCard, StatusBadge, EventItem, etc.)
- `src/styles.css` — flat dark theme (185 lines)
- `src/api.ts` — API layer (unchanged since V0)
- `src/main.tsx` — React bootstrap
- `vite.config.ts` — proxy config

## Build Status
✅ Type-check passes
✅ Build passes (208KB JS, 7.5KB CSS)
✅ No runtime errors
❌ UX unclear ("murky and strange")
