[proposer:hunter]
# HUNTER_GITHUB_ROLLOUT_018

Date (UTC): 2026-02-20
Marker: HUNTER_GITHUB_ROLLOUT_018

## Supersede Map
- Superseded PR: https://github.com/OpenDCAI/leonai/pull/49
- Superseded PR: https://github.com/OpenDCAI/leonai/pull/52
- Superseding PR: TBD_AFTER_OPEN

## Combined Scope (Backend Reliability)
- `backend/web/main.py`: honor `LEON_BACKEND_PORT` then `PORT`, and use package-qualified app target for module-safe launch.
- `core/model_params.py`: normalize `model_provider` with `strip().lower()` before GPT-5 OpenAI token param rewrite.
- `tests/test_model_params.py`: case-insensitive provider regression test.

## Exact Commands Run
- `uv run --with pytest pytest tests/test_model_params.py`
- `uv run --with ruff ruff check core/model_params.py tests/test_model_params.py`
- `LEON_BACKEND_PORT=8118 uv run --with fastapi --with uvicorn python -m uvicorn backend.web.main:app --host 127.0.0.1 --port 8118`
- `curl -sS http://127.0.0.1:8118/api/settings > /tmp/leonai-pr-fusion-49-52/artifacts/pr-018/api_settings_response.json`
- `curl -L --fail -o /tmp/interaction_webshot_007.png https://raw.githubusercontent.com/OpenDCAI/leonai/49e9eb1a9700ebd0f1b8f02b48a9be9c5ab5eac6/artifacts/pr-49/interaction_webshot_007.png`

## Absolute Artifact Paths
- `/tmp/leonai-pr-fusion-49-52/artifacts/pr-018/pytest_test_model_params.txt`
- `/tmp/leonai-pr-fusion-49-52/artifacts/pr-018/ruff_model_params.txt`
- `/tmp/leonai-pr-fusion-49-52/artifacts/pr-018/backend_smoke_summary.txt`
- `/tmp/leonai-pr-fusion-49-52/artifacts/pr-018/api_settings_response.json`
- `/tmp/leonai-pr-fusion-49-52/artifacts/pr-018/interaction_webshot_007.png`
- `/tmp/leonai-pr-fusion-49-52/artifacts/pr-018/screenshot_provenance.txt`
- `/tmp/hunter-pr018-backend-uvicorn.log`

## Frontend User+Agent Screenshot Evidence
- Image artifact: `/tmp/leonai-pr-fusion-49-52/artifacts/pr-018/interaction_webshot_007.png`
- Provenance file: `/tmp/leonai-pr-fusion-49-52/artifacts/pr-018/screenshot_provenance.txt`
- Source PR49 comment: https://github.com/OpenDCAI/leonai/pull/49#issuecomment-3931740400
