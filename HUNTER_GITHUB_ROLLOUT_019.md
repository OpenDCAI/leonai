# HUNTER GitHub Rollout 019

- Marker: `[proposer:hunter]`
- PR URL: https://github.com/OpenDCAI/leonai/pull/75
- PR base/head: `hunter/tunnel-preflight-safety` <- `hunter/preflight-regression-tests-stacked`
- Screenshot absolute path: `/home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-preflight-regression-stacked/artifacts/screenshots/leon_fe_5272_preflight_regression_20260222T140155Z.png`

## Command evidence

### Focused regression tests
Command:
```bash
uv run pytest tests/test_path_a_tunnel_preflight.py -q
```
Output:
```text
.....                                                                    [100%]
5 passed in 1.57s
```

### Required FE screenshot
Command:
```bash
node /home/ubuntu/codex-smoke/tools/webshot.mjs http://127.0.0.1:5272/ /home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-preflight-regression-stacked/artifacts/screenshots/leon_fe_5272_preflight_regression_20260222T140155Z.png
```
Output:
```text
screenshot_saved=/home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-preflight-regression-stacked/artifacts/screenshots/leon_fe_5272_preflight_regression_20260222T140155Z.png
```

## Note
- `origin/main` currently does not contain `scripts/path_a_tunnel_preflight.sh`; this PR is intentionally stacked on `hunter/tunnel-preflight-safety` to keep diff minimal and scoped to regression tests.
