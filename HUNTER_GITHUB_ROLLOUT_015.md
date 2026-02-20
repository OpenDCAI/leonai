[proposer:hunter]
# HUNTER_GITHUB_ROLLOUT_015

Date (UTC): 2026-02-20

## Scope
- Narrow fix for GPT-5 OpenAI parameter normalization when `model_provider` uses mixed casing.
- Regression coverage added in `tests/test_model_params.py`.

## Rollout Notes
- MARKER: HUNTER_GITHUB_ROLLOUT_015
- PR URL: https://github.com/OpenDCAI/leonai/pull/52
- Exact verification commands:
  - `uv run --with pytest pytest tests/test_model_params.py`
  - `uv run --with ruff ruff check core/model_params.py tests/test_model_params.py`

## Screenshot Artifact
- Page URL: `http://127.0.0.1:5272/`
- Absolute artifact path: `/home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-pr015/artifacts/pr015-leon-fe.png`
- Exact capture command:
  - `node /home/ubuntu/codex-smoke/tools/webshot.mjs http://127.0.0.1:5272/ /home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-pr015/artifacts/pr015-leon-fe.png`
