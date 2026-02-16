# Leon Operator Console V4 - Complete Overhaul

## What Changed

**Removed tabs entirely.** The console is now a **single-page dashboard** with a two-column layout.

## Design Philosophy

### Before (V1-V3): Data Viewer
- Tabs for different "views" of data
- Search tab with unclear purpose
- Thread inspector was just an input box
- Sandboxes showed only active sessions
- No sense of "what's happening now"

### After (V4): Operator Dashboard
- **Single page** showing everything at once
- **Left column**: System health + active sandboxes
- **Right column**: Search + thread inspector
- **Auto-refresh** every 10 seconds
- **Click-to-navigate**: Click any thread_id → jumps to inspector

## Layout

```
┌─────────────────────────────────────────────────────────┐
│ Leon Operator Console                                   │
├─────────────────────────────────────────────────────────┤
│ ● All systems operational  │  Last 24h · Auto-refresh  │
├──────────────────┬──────────────────────────────────────┤
│ System Overview  │ Search                               │
│ ┌──┬──┬──┬──┐   │ [input box]                          │
│ │4 │0 │4 │1 │   │ [results...]                         │
│ └──┴──┴──┴──┘   │                                      │
│ Running/Done/... │ Thread Inspector                     │
│                  │ [input box]                          │
│ Active Sandboxes │ [run list]                           │
│ [sandbox cards]  │ [event timeline]                     │
└──────────────────┴──────────────────────────────────────┘
```

## Key Features

### 1. Status Bar (Top)
- Green indicator: "All systems operational"
- Yellow indicator: "System has issues" (if errors or stuck runs)
- Auto-refresh timer (10s)
- Manual refresh button
- Loading spinner

### 2. System Overview (Left Column)
- **Stat boxes**: Running, Completed, Errors (red), Stuck (yellow)
- **Issue boxes**: Only show when problems exist
  - Stuck runs with clickable thread_ids
  - Recent errors with counts
- **Active sandboxes**: Cards showing provider, status, cwd
  - Click card → jumps to thread inspector

### 3. Search (Right Column, Top)
- Input box for searching threads/runs/text
- Results show as clickable cards
- Click result → jumps to thread inspector

### 4. Thread Inspector (Right Column, Bottom)
- Input box for thread_id (or click from elsewhere)
- Shows all runs for that thread
- Click run → loads event timeline
- "Tail events" button for live debugging
- Collapsible run details (JSON)

## User Workflow

### Monitoring
1. Open dashboard → see system status immediately
2. Left column shows: running count, completed count, active sandboxes
3. Auto-refreshes every 10s

### Triage
1. Status bar turns yellow if issues detected
2. Red "Errors" stat box appears
3. Yellow "Stuck" stat box appears
4. Issue boxes show details
5. Click thread_id → jumps to inspector

### Investigation
1. Click sandbox card or stuck run → thread_id auto-fills
2. See all runs for that thread
3. Click run → see event timeline
4. Click "Tail events" → live updates
5. Expand run details for full JSON

### Search
1. Type thread_id, run_id, or text
2. Results appear below
3. Click result → jumps to inspector

## Technical Details

### Auto-Refresh
- Loads overview + sandboxes every 10s
- Uses `setInterval` with cleanup on unmount
- Shows spinner during refresh
- Errors don't break the loop

### Cross-Navigation
- All thread_ids are clickable
- Clicking sets `selectedThread` state
- Thread inspector auto-loads runs
- Smooth scroll to inspector section

### Event Tailing
- Uses refs to avoid stale closure bug
- Polls every 1s when tailing
- Auto-scrolls to new events
- Stop button to cancel

### Responsive
- Two-column grid on desktop (1fr 1fr)
- Single column on mobile (<1200px)
- Sections stack vertically

## File Changes

### App.tsx (389 lines)
- Single `Dashboard` component (no tabs)
- `ThreadDetail` component for inspector
- Auto-refresh with `useEffect`
- Cross-navigation with `setSelectedThread`

### styles.css (172 lines)
- `.statusBar` - system status header
- `.dashGrid` - two-column layout
- `.statGrid` - stat boxes
- `.issueBox` - error/stuck run alerts
- `.sandboxCard` - clickable sandbox cards
- `.searchBox` - search input + button
- `.runList` - run cards with selection state
- All existing timeline/badge/button styles

### components.tsx (unchanged)
- All components work as-is
- `StatusBadge`, `EventItem`, `TimeAgo`, etc.

## What's Still Missing (V1 Requirements)

**IMPORTANT:** V4 is a UI layout improvement only. It does NOT implement the full V1 requirements.

See `V1_GAP_ANALYSIS.md` and `V1_IMPLEMENTATION_PLAN.md` for complete details.

### P0 Features Not Yet Implemented

1. **Ground Truth Table** - Missing fields:
   - chat_session_id, lease_id, instance_id
   - desired_state (vs observed_state)
   - source (api/cli/resume)
   - No stable refresh (flickers on reload)

2. **Orphan Resource Panel** - Not implemented:
   - No orphan detection
   - No adopt/destroy actions
   - Can't see untracked instances

3. **Session Operations** - Not implemented:
   - No pause/resume/destroy buttons
   - No convergence tracking
   - No operation feedback

4. **Provider Event View** - Not implemented:
   - No webhook/event history
   - Can't trace state changes
   - No troubleshooting timeline

### P1 Features Not Yet Implemented

5. **Alert Visualization** - Backend exists, frontend missing:
   - No alert panel
   - No alert history
   - No acknowledgment/mute actions

6. **Explore Mode** - Not implemented:
   - No ad-hoc query builder
   - No saved queries
   - Only hard-coded views

### Other Gaps

- No URL state persistence
- No TypeScript types (all `any`)
- No action buttons (restart/kill/clear)

## Testing Checklist

- [x] Build passes (204KB JS, 7.3KB CSS)
- [x] Type-check passes
- [x] Status bar shows correct indicator
- [x] Stat boxes show correct counts
- [x] Auto-refresh works (10s interval)
- [x] Manual refresh button works
- [x] Sandbox cards render
- [x] Click sandbox → fills thread_id
- [x] Search input works
- [x] Thread inspector loads runs
- [x] Click run → loads events
- [x] Tail events works (no stale closure)
- [x] Event timeline renders
- [ ] Test with stuck runs (need real data)
- [ ] Test with errors (need real data)
- [ ] Test search results (need real data)

## Design Principles

1. **Everything visible at once** - No hidden tabs, no navigation
2. **Auto-refresh** - Always showing current state
3. **Click-to-navigate** - Thread IDs are links, not copy-paste
4. **Progressive disclosure** - Issues only show when they exist
5. **Responsive** - Works on desktop and mobile
6. **Fast** - Parallel API calls, efficient rendering

## Comparison to V3

| V3 (Tabs) | V4 (Dashboard) |
|-----------|----------------|
| 3 tabs (Overview, Sandboxes, Thread) | Single page, two columns |
| Manual navigation between tabs | Click thread_id → auto-navigate |
| Thread inspector = empty input box | Thread inspector = input + run list + timeline |
| Sandboxes = separate tab | Sandboxes = left column, always visible |
| No auto-refresh | Auto-refresh every 10s |
| Search = separate tab | Search = right column, always visible |

## Why This Works

**Operators need to see everything at once:**
- System health (stats)
- Active sessions (sandboxes)
- Problem areas (errors, stuck runs)
- Investigation tools (search, inspector)

**No more "where do I go to see X?"** - It's all on one page.

**No more "is this data stale?"** - Auto-refresh every 10s.

**No more "how do I get to that thread?"** - Click it.

This is a **monitoring dashboard**, not a data viewer.
