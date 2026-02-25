# Database Abstraction Plan (Phase-2 + Phase-3)

## Objective

Remove direct SQL from key business paths and converge on repository boundaries with a single composition root.

## Architecture Decision

- Keep `Repository` as the primary boundary.
- Keep SQL parameterized; ORM is optional and deferred.
- Keep provider/runtime concerns separated from repository APIs.

## Delivered Repositories

1. `CheckpointRepo` (`checkpoints` + `writes`)
2. `ThreadConfigRepo` (`thread_config`)
3. `RunEventRepo` (`run_events`)
4. `FileOperationRepo` (`file_operations`)
5. `SummaryRepo` (`summaries`)
6. `EvalRepo` (`eval.db`: trajectories + metrics)

## Delivered Integration

- `StorageContainer` now wires all six phase-2 repos in one composition entrypoint.
- Existing service/TUI APIs are preserved while data access is delegated to repos.

## Security & Reliability Constraints

- All SQL remains parameterized.
- No silent fallback when repository operations fail (fail-loud behavior retained).
- No artifact/image files are part of this change set.

## Rollback

- Revert phase commits independently if needed:
  - `storage(phase2): add CheckpointRepo...`
  - `storage(phase2): add ThreadConfigRepo...`
  - `storage(phase2): add RunEventRepo...`
  - `storage(phase2): add FileOperationRepo...`
  - `storage(phase2): add SummaryRepo...`
  - `storage(phase2): add EvalRepo...`
  - `storage(phase3): add StorageContainer...`

## Verification Matrix

```bash
python -m pytest \
  tests/test_checkpoint_repo.py \
  tests/test_thread_config_repo.py \
  tests/test_run_event_repo.py \
  tests/test_file_operation_repo.py \
  tests/test_session_file_operations_cleanup.py \
  tests/test_eval_repo.py \
  tests/middleware/memory/test_summary_store.py -q
```

Expected: all pass.

## Deferred Scope

- Supabase backend adapters (follow-up implementation slice)
- ORM adoption inside selected repositories (only after boundary stability)
