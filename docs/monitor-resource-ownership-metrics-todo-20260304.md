# Monitor Resource Ownership & Metrics TODO (2026-03-04)

## Scope Boundary
- Quota (organization-level hard limits) stays out-of-scope in this round.
- Reason: provider APIs for quota are not consistently available from current credentials/SDK paths.
- This round focuses on real ownership + runtime/static telemetry where we can collect facts.

## Target Outcomes
1. Resource panel shows real `thread_id` and real `agent_name` (not hardcoded default).
2. Resource metrics are collected and persisted in sandbox DB.
3. Collection runs at the two required hooks:
   - on lease instance creation
   - on backend startup + monitor refresh loop
4. Collector uses two modes:
   - running mode (runtime probe)
   - non-running mode (SDK/static probe)

## Implementation Plan (with LOC estimate)

### P1. Ownership plumbing (lease -> thread -> agent_name)
- Backend:
  - Add ownership resolver in monitor core (cross DB join: sandbox.db + leon.db).
  - Replace hardcoded `agentId/agentName` in resources overview payload.
- Frontend:
  - Show `thread_id` alongside agent name in resource allocation badges/detail.
- Estimated LOC:
  - backend: +120 ~ +180
  - frontend: +30 ~ +60
  - tests: +40 ~ +80

### P2. Resource snapshot persistence
- Add table in `sandbox.db` for latest metrics per lease.
- Suggested table: `lease_resource_snapshots` (upsert by lease_id).
- Store fields:
  - lease_id, provider_name, observed_state, probe_mode, collected_at
  - cpu_used, cpu_limit, memory_used_mb, memory_total_mb
  - disk_used_gb, disk_total_gb, network_rx_kbps, network_tx_kbps
  - probe_error
- Estimated LOC:
  - backend: +140 ~ +220
  - tests: +60 ~ +120

### P3. Probe service (running vs non-running)
- New monitor-core service module:
  - resolve active lease sessions
  - running probe: provider runtime metrics path
  - non-running probe: provider SDK/static metadata path (if available), otherwise explicit null + reason
- Fail loudly in logs and keep explicit error field in snapshot row.
- Estimated LOC:
  - backend: +220 ~ +320
  - tests: +70 ~ +130

### P4. Trigger hooks
- Hook A (create-time): after successful instance creation, trigger ownership+probe write.
- Hook B (startup/loop): run full refresh in monitor refresh loop task.
- Keep async path non-blocking for API threads.
- Estimated LOC:
  - backend: +80 ~ +130
  - tests: +30 ~ +60

### P5. Resources API integration
- `GET /api/monitor/resources` reads latest snapshots and ownership data.
- Preserve existing shape; replace unknown placeholders where facts exist.
- Keep unknown only when probe truly unavailable.
- Estimated LOC:
  - backend: +90 ~ +140
  - tests: +40 ~ +80

### P6. Frontend integration
- Render thread+agent ownership in allocation/detail panels.
- Keep UI minimal; do not add extra noisy status labels.
- Estimated LOC:
  - frontend: +40 ~ +80

## Commit Strategy (small steps)
1. doc + ownership backend skeleton
2. ownership frontend wiring
3. snapshot table + repository helpers
4. probe service + create/startup hooks
5. resources API wiring + tests
6. UI polish + e2e screenshot refresh

## Risk Notes
- Existing `thread_config.agent` currently may store name or id depending on caller; resolver must normalize both.
- Some providers cannot supply paused-state runtime metrics; store explicit nulls and reason, not fake values.

## Acceptance Checklist
- [ ] No `Default`/hardcoded agent name in resource API payload.
- [ ] Resource panel can identify `agent_name + thread_id` for live sessions.
- [ ] Snapshot row exists/updates after lease create and on refresh loop.
- [ ] Running providers show real metrics when SDK supports them.
- [ ] Paused providers do not pretend runtime metrics; null + reason is visible in API payload.
- [ ] All steps committed and pushed incrementally to `feat/resource-page`.
