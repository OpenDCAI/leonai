# V1 Implementation Plan: P0 Features

Date: 2026-02-15

## Overview

This plan covers the P0 (must-have) features for V1:
1. Ground Truth table with full fields + stable refresh
2. Orphan resource panel + adopt/destroy actions
3. Session operations (pause/resume/destroy) + convergence
4. Provider event view

## Feature 1: Ground Truth Table Enhancement

### Backend Changes

**File:** `services/web/data_platform/sandbox_views.py`

```python
def list_active_sessions(limit: int = 100, status_filter: Optional[str] = None) -> list[dict]:
    """
    Return full ground truth fields for each session.

    New fields to add:
    - chat_session_id (from sandbox.db sessions table)
    - lease_id (from provider lease records)
    - instance_id (from provider instance records)
    - desired_state (from runtime or session config)
    - source (where this session came from: api/cli/resume)
    """
    # Query sandbox.db for sessions
    # Join with provider lease/instance data
    # Add desired_state from runtime if available
    # Return enriched records
```

**File:** `services/web/data_platform/api.py`

Update `/api/operator/sandboxes` response schema to include new fields.

### Frontend Changes

**File:** `frontend/operator/src/api.ts`

Update `listSandboxes()` return type to include new fields.

**File:** `frontend/operator/src/App.tsx`

```typescript
// Stable refresh pattern - preserve old data until new arrives
const [sandboxes, setSandboxes] = useState<any>(null);
const [sandboxesLoading, setSandboxesLoading] = useState(false);

const loadSandboxes = async () => {
  setSandboxesLoading(true);
  try {
    const newData = await listSandboxes(statusParam);
    // Only update after successful fetch
    setSandboxes(newData);
  } catch (e) {
    setErr(e);
    // Keep old data on error
  } finally {
    setSandboxesLoading(false);
  }
};

// Table columns to add:
// - Session ID (chat_session_id)
// - Lease ID
// - Instance ID
// - Desired State (with visual indicator if != observed_state)
// - Source
```

**File:** `frontend/operator/src/styles.css`

```css
/* State convergence indicator */
.stateConverged { color: var(--green); }
.stateDiverged { color: var(--yellow); animation: pulse 2s infinite; }

/* Stable table - no flash on refresh */
.table tbody { transition: opacity 0.15s; }
.table-loading tbody { opacity: 0.6; }
```

### Acceptance Criteria

- [ ] Sandboxes table shows all ground truth fields
- [ ] No flash/flicker on refresh (old data preserved until new arrives)
- [ ] Visual indicator when observed_state != desired_state
- [ ] Loading indicator doesn't clear existing data

---

## Feature 2: Orphan Resource Panel

### Backend Changes

**New File:** `services/web/data_platform/orphan_detection.py`

```python
from typing import List, Dict, Any
from pathlib import Path

def detect_orphans(sandbox_db_path: Path) -> List[Dict[str, Any]]:
    """
    Query all provider APIs for instances.
    Cross-reference with sandbox.db sessions.
    Return instances not tracked in sandbox.db.

    Returns:
    [
      {
        "provider": "daytona",
        "instance_id": "abc123",
        "created_at": "2026-02-15T10:00:00Z",
        "state": "running",
        "metadata": {...}
      }
    ]
    """
    # 1. Query sandbox.db for all known instance_ids
    # 2. Query each provider API for all instances
    # 3. Return instances not in sandbox.db
    pass

async def adopt_orphan(provider: str, instance_id: str, thread_id: str) -> Dict[str, Any]:
    """
    Create a session record in sandbox.db for an orphan instance.
    Link it to the specified thread_id.
    """
    # Insert into sandbox.db sessions table
    # Return new session record
    pass

async def destroy_orphan(provider: str, instance_id: str) -> Dict[str, Any]:
    """
    Call provider API to destroy the instance.
    Do NOT create a session record.
    """
    # Call provider destroy API
    # Return destruction result
    pass
```

**File:** `services/web/data_platform/api.py`

```python
@router.get("/api/operator/orphans")
async def operator_orphans() -> dict[str, Any]:
    items = detect_orphans(sandbox_db_path=dp_db_path)
    return {"items": items, "count": len(items)}

@router.post("/api/operator/orphans/{instance_id}/adopt")
async def operator_adopt_orphan(
    instance_id: str,
    provider: str = Query(...),
    thread_id: str = Query(...),
) -> dict[str, Any]:
    result = await adopt_orphan(provider, instance_id, thread_id)
    return result

@router.post("/api/operator/orphans/{instance_id}/destroy")
async def operator_destroy_orphan(
    instance_id: str,
    provider: str = Query(...),
) -> dict[str, Any]:
    result = await destroy_orphan(provider, instance_id)
    return result
```

### Frontend Changes

**File:** `frontend/operator/src/api.ts`

```typescript
export async function listOrphans() {
  return await http<any>("/api/operator/orphans");
}

export async function adoptOrphan(instanceId: string, provider: string, threadId: string) {
  return await http<any>(
    `/api/operator/orphans/${encodeURIComponent(instanceId)}/adopt?provider=${provider}&thread_id=${threadId}`,
    { method: "POST" }
  );
}

export async function destroyOrphan(instanceId: string, provider: string) {
  return await http<any>(
    `/api/operator/orphans/${encodeURIComponent(instanceId)}/destroy?provider=${provider}`,
    { method: "POST" }
  );
}
```

**File:** `frontend/operator/src/App.tsx`

```typescript
// Add to Dashboard component
const [orphans, setOrphans] = useState<any>(null);

const loadOrphans = async () => {
  try {
    setOrphans(await listOrphans());
  } catch (e) {
    setErr(e);
  }
};

// Add orphan panel to dashboard
{orphans?.count > 0 && (
  <div className="dashSection">
    <h2>⚠️ Orphan Resources ({orphans.count})</h2>
    <div className="issueBox">
      <div className="issueHeader">Untracked Instances</div>
      {orphans.items.map((o: any) => (
        <div key={o.instance_id} className="orphanItem">
          <div className="orphanInfo">
            <div className="orphanId">{o.instance_id}</div>
            <div className="orphanMeta">
              {o.provider} · {o.state} · <TimeAgo iso={o.created_at} />
            </div>
          </div>
          <div className="orphanActions">
            <button onClick={() => handleAdopt(o)}>Adopt</button>
            <button onClick={() => handleDestroy(o)} className="btn-danger">Destroy</button>
          </div>
        </div>
      ))}
    </div>
  </div>
)}
```

**File:** `frontend/operator/src/styles.css`

```css
.orphanItem {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-radius: 6px;
  background: var(--bg);
  border: 1px solid var(--yellow);
  margin-bottom: 8px;
}

.orphanActions {
  display: flex;
  gap: 8px;
}

.btn-danger {
  background: rgba(248,81,73,.15);
  border-color: var(--red);
  color: var(--red);
}

.btn-danger:hover {
  background: rgba(248,81,73,.25);
}
```

### Acceptance Criteria

- [ ] Orphan panel appears when orphans detected
- [ ] Shows provider, instance_id, state, created_at
- [ ] Adopt button prompts for thread_id, creates session record
- [ ] Destroy button shows confirmation, calls provider API
- [ ] Panel refreshes after adopt/destroy action
- [ ] Error handling for failed operations

---

## Feature 3: Session Operations

### Backend Changes

**File:** `services/web/data_platform/session_operations.py`

```python
async def pause_session(thread_id: str) -> Dict[str, Any]:
    """
    Set desired_state = 'paused' for session.
    Call provider pause API.
    Return operation result + convergence status.
    """
    # 1. Update sandbox.db: desired_state = 'paused'
    # 2. Call provider pause API
    # 3. Poll until observed_state = 'paused' (max 30s)
    # 4. Return convergence result
    pass

async def resume_session(thread_id: str) -> Dict[str, Any]:
    """Set desired_state = 'active', call provider resume."""
    pass

async def destroy_session(thread_id: str) -> Dict[str, Any]:
    """Set desired_state = 'destroyed', call provider destroy."""
    pass
```

**File:** `services/web/data_platform/api.py`

```python
@router.post("/api/operator/sessions/{thread_id}/pause")
async def operator_pause_session(thread_id: str) -> dict[str, Any]:
    result = await pause_session(thread_id)
    return result

@router.post("/api/operator/sessions/{thread_id}/resume")
async def operator_resume_session(thread_id: str) -> dict[str, Any]:
    result = await resume_session(thread_id)
    return result

@router.post("/api/operator/sessions/{thread_id}/destroy")
async def operator_destroy_session(thread_id: str) -> dict[str, Any]:
    result = await destroy_session(thread_id)
    return result
```

### Frontend Changes

**File:** `frontend/operator/src/api.ts`

```typescript
export async function pauseSession(threadId: string) {
  return await http<any>(`/api/operator/sessions/${encodeURIComponent(threadId)}/pause`, {
    method: "POST",
  });
}

export async function resumeSession(threadId: string) {
  return await http<any>(`/api/operator/sessions/${encodeURIComponent(threadId)}/resume`, {
    method: "POST",
  });
}

export async function destroySession(threadId: string) {
  return await http<any>(`/api/operator/sessions/${encodeURIComponent(threadId)}/destroy`, {
    method: "POST",
  });
}
```

**File:** `frontend/operator/src/App.tsx`

```typescript
// Add action column to sandboxes table
<td>
  <div className="sessionActions">
    {s.chat_status === 'active' && (
      <button onClick={() => handlePause(s.thread_id)} title="Pause">⏸</button>
    )}
    {s.chat_status === 'idle' && (
      <button onClick={() => handleResume(s.thread_id)} title="Resume">▶️</button>
    )}
    <button onClick={() => handleDestroy(s.thread_id)} className="btn-danger" title="Destroy">🗑</button>
  </div>
</td>

// Operation handlers with optimistic UI
const handlePause = async (threadId: string) => {
  // Optimistic update
  setSandboxes((prev: any) => ({
    ...prev,
    items: prev.items.map((s: any) =>
      s.thread_id === threadId ? { ...s, desired_state: 'paused', converging: true } : s
    ),
  }));

  try {
    await pauseSession(threadId);
    // Refresh to get actual state
    await loadSandboxes();
  } catch (e) {
    setErr(e);
    // Revert optimistic update
    await loadSandboxes();
  }
};
```

**File:** `frontend/operator/src/styles.css`

```css
.sessionActions {
  display: flex;
  gap: 4px;
}

.sessionActions button {
  padding: 4px 8px;
  font-size: 14px;
}

/* Converging indicator */
.converging {
  position: relative;
}

.converging::after {
  content: "⏳";
  position: absolute;
  right: -20px;
  animation: pulse 1s infinite;
}
```

### Acceptance Criteria

- [ ] Action buttons appear in sandbox table (pause/resume/destroy)
- [ ] Buttons show only for valid states (pause for active, resume for idle)
- [ ] Optimistic UI update on button click
- [ ] Convergence indicator while operation in progress
- [ ] Confirmation dialog for destroy action
- [ ] Error handling with rollback on failure
- [ ] State converges within one refresh cycle (10s)

---

## Feature 4: Provider Event View

### Backend Changes

**File:** `services/web/data_platform/provider_events.py`

```python
def list_provider_events(
    thread_id: Optional[str] = None,
    provider: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Query provider webhook/event logs.

    Returns:
    [
      {
        "event_id": "evt_123",
        "provider": "daytona",
        "event_type": "workspace.started",
        "thread_id": "abc",
        "instance_id": "xyz",
        "payload": {...},
        "received_at": "2026-02-15T10:00:00Z"
      }
    ]
    """
    # Query provider event logs (webhook records, API events)
    # Filter by thread_id/provider if specified
    # Return sorted by received_at desc
    pass
```

**File:** `services/web/data_platform/api.py`

```python
@router.get("/api/operator/provider-events")
async def operator_provider_events(
    thread_id: str = Query(None),
    provider: str = Query(None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    items = list_provider_events(thread_id=thread_id, provider=provider, limit=limit)
    return {"items": items, "count": len(items)}
```

### Frontend Changes

**File:** `frontend/operator/src/api.ts`

```typescript
export async function getProviderEvents(threadId?: string, provider?: string) {
  const u = new URL("/api/operator/provider-events", window.location.origin);
  if (threadId) u.searchParams.set("thread_id", threadId);
  if (provider) u.searchParams.set("provider", provider);
  return await http<any>(u.pathname + u.search);
}
```

**File:** `frontend/operator/src/App.tsx`

```typescript
// Add to ThreadDetail component
const [providerEvents, setProviderEvents] = useState<any>(null);

useEffect(() => {
  const loadProviderEvents = async () => {
    try {
      setProviderEvents(await getProviderEvents(threadId));
    } catch (e) {
      setErr(e);
    }
  };
  void loadProviderEvents();
}, [threadId]);

// Render provider events section
{providerEvents && (
  <>
    <h3>Provider Events ({providerEvents.count})</h3>
    <div className="timeline">
      {providerEvents.items.map((ev: any) => (
        <div key={ev.event_id} className="evt evt-provider">
          <div className="evtLabel">
            <strong>{ev.event_type}</strong> · {ev.provider}
          </div>
          <div className="evtPre">{JSON.stringify(ev.payload, null, 2)}</div>
          <span className="evtMeta">
            <TimeAgo iso={ev.received_at} />
          </span>
        </div>
      ))}
    </div>
  </>
)}
```

**File:** `frontend/operator/src/styles.css`

```css
.evt-provider {
  background: rgba(210,153,34,.06);
}

.evt-provider::before {
  background: var(--yellow);
}
```

### Acceptance Criteria

- [ ] Provider events section appears in thread detail panel
- [ ] Shows event_type, provider, payload, timestamp
- [ ] Events sorted by received_at (newest first)
- [ ] Timeline format consistent with run events
- [ ] Can filter by thread_id (automatic in thread detail)
- [ ] Helps explain state transitions (manual verification)

---

## Implementation Order

1. **Day 1-2:** Backend API implementation
   - Extend sandbox_views.py for ground truth fields
   - Implement orphan_detection.py
   - Implement session_operations.py
   - Implement provider_events.py
   - Add all API endpoints

2. **Day 3:** Ground Truth table + stable refresh
   - Update frontend API types
   - Implement stable refresh pattern
   - Add new table columns
   - Add state convergence indicator

3. **Day 4:** Orphan resource panel
   - Add orphan panel to dashboard
   - Implement adopt/destroy handlers
   - Add confirmation dialogs
   - Test orphan detection flow

4. **Day 5:** Session operations
   - Add action buttons to sandbox table
   - Implement operation handlers
   - Add optimistic UI updates
   - Test convergence behavior

5. **Day 6:** Provider event view
   - Add provider events section to thread detail
   - Implement event timeline rendering
   - Test event filtering

6. **Day 7:** E2E testing + polish
   - Test all operations end-to-end
   - Verify no resource leaks
   - Add loading states
   - Fix edge cases

## Testing Strategy

**Backend Tests:**
- Unit tests for orphan detection logic
- Unit tests for session operations
- Integration tests for API endpoints
- Mock provider APIs for testing

**Frontend Tests:**
- Component tests for new panels
- Integration tests for operation flows
- Manual E2E testing in dev environment

**E2E Validation:**
- Create orphan instance → verify detection → adopt → verify session created
- Create session → pause → verify convergence → resume → verify convergence
- Trigger provider event → verify appears in UI
- Refresh during operation → verify no flicker

## Success Metrics

- [ ] All P0 features implemented and tested
- [ ] No flicker on refresh (stable data)
- [ ] Orphans discoverable and actionable
- [ ] Session operations converge within 10s
- [ ] Provider events visible for troubleshooting
- [ ] Zero resource leaks in testing
- [ ] API-first: all UI actions simulatable via curl
