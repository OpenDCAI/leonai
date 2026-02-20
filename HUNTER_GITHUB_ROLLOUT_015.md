[proposer:hunter]
# HUNTER_GITHUB_ROLLOUT_015

Date (UTC): 2026-02-20

## Scope
- Oversized-PR remediation for `#51` (`51 files, +2734/-2698`).
- First minimal independent follow-up slice only: declare missing backend runtime dependency in package metadata.

## Minimal Slice Opened
- Branch: `hunter/pr51-remediation-fastapi-dep`
- Change set:
  - `pyproject.toml`: add direct dependency `fastapi>=0.129.0`
  - `uv.lock`: lock refresh for direct fastapi dependency
- Rationale: clean environment `uv run` on `origin/dev` failed with `ModuleNotFoundError: fastapi` when importing backend modules/tests.

## Screenshot Evidence
- URL: https://raw.githubusercontent.com/OpenDCAI/leonai/hunter/pr51-remediation-fastapi-dep/artifacts/pr-51-remediation/pr51-home.png
- Absolute path: `/tmp/leonai-pr51-review/artifacts/pr-51-remediation/pr51-home.png`
- Exact command: `node /home/ubuntu/codex-smoke/tools/webshot.mjs http://127.0.0.1:5272/ /tmp/leonai-pr51-review/artifacts/pr-51-remediation/pr51-home.png`

## Validation
- `uv run python -c "import fastapi; print(fastapi.__version__)"` => `0.129.0`
- Baseline failure observed before this slice:
  - `uv run pytest tests/test_sse_refactor.py -q`
  - error: `ImportError: cannot import name 'stream_agent_execution' ...`

## Marker + URL
- `[rollout-notes:hunter-015] https://github.com/OpenDCAI/leonai/blob/hunter/pr51-remediation-fastapi-dep/HUNTER_GITHUB_ROLLOUT_015.md`

## GitHub Evidence URLs
- Remediation review (`CHANGES_REQUESTED`) on `#51`:
  - https://github.com/OpenDCAI/leonai/pull/51#pullrequestreview-3831901714
- Remediation comment on `#51` (screenshot fields + self-review):
  - https://github.com/OpenDCAI/leonai/pull/51#issuecomment-3934261204
- First minimal follow-up PR:
  - https://github.com/OpenDCAI/leonai/pull/54
