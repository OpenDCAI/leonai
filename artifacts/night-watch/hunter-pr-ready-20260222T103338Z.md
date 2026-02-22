[proposer:hunter]

## Proposed PR Title
backend/web: fail startup on missing sandbox SDKs and harden thread delete provider reconciliation

## Proposed PR Body
### Summary
- add explicit backend dependency parity check for configured non-local sandbox providers at app startup
- harden thread-delete resource cleanup by reconciling provider from sandbox DB when thread metadata/provider manager keys drift
- add focused regression tests for startup dependency failure and delete-thread provider mismatch recovery

### Scope
- `backend/web/requirements.txt`
- `backend/web/services/sandbox_service.py`
- `backend/web/core/lifespan.py`
- `tests/test_backend_startup_delete_hardening.py`

## Validation
Command:
`uv run pytest -q tests/test_backend_startup_delete_hardening.py`

Output:
```text
Using CPython 3.12.3 interpreter at: /usr/bin/python3.12
Creating virtual environment at: .venv
   Building leonai @ file:///home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-pr-ready
      Built leonai @ file:///home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-pr-ready
Installed 85 packages in 51ms
..                                                                       [100%]
2 passed in 1.22s
```

## FE Screenshot
Absolute path:
`/home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-pr-ready/artifacts/night-watch/hunter-pr-ready-20260222T103338Z.png`

Exact command:
`node /home/ubuntu/codex-smoke/tools/webshot.mjs http://127.0.0.1:5272/ /home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-pr-ready/artifacts/night-watch/hunter-pr-ready-20260222T103338Z.png`

## Rollout Notes
- rollout marker: `[proposer:hunter]`
- rollout PR URL: `https://github.com/OpenDCAI/leonai/pull/70`
- rollout screenshot absolute path: `/home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-pr-ready/artifacts/night-watch/hunter-pr-ready-20260222T103338Z.png`
- rollout screenshot command evidence: `node /home/ubuntu/codex-smoke/tools/webshot.mjs http://127.0.0.1:5272/ /home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-pr-ready/artifacts/night-watch/hunter-pr-ready-20260222T103338Z.png`

## Self-review Verdict
- verdict: pass, candidate is minimal and scoped to dependency-parity hardening

## Risks
- malformed sandbox JSON now fails startup earlier because parity check parses each config file directly
- dependency check only validates module importability, not runtime credential validity
- provider reconciliation fallback depends on `abstract_terminals` row presence; schema drift could change behavior
