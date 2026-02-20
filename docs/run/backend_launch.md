# Backend Launch (Canonical)

Run backend from repository root only.

## Exact Command
```bash
LEON_BACKEND_PORT=8102 uv run python -m uvicorn backend.web.main:app --host 127.0.0.1 --port 8102
```

## Environment
- `LEON_BACKEND_PORT`: desk-assigned backend port (set explicitly; example uses `8102`).
- `PORT`: optional generic port env used in app codepaths, but canonical launch sets `--port` directly for deterministic behavior.

## Quick Smoke
```bash
curl http://127.0.0.1:8102/api/settings
```

## Anti-Pattern (Do Not Use)
- `cd backend/web && python main.py`
- Why: import resolution depends on current working directory and can fail with `ModuleNotFoundError: backend`.
