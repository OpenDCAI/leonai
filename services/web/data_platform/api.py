from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from . import store
from .dashboards import overview as dashboards_overview
from .search import search_all
from .sandbox_views import list_active_sessions, list_thread_commands


def create_router(*, db_path: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/api/threads/{thread_id}/runs")
    async def list_thread_runs(
        thread_id: str,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        items = store.list_runs(db_path=db_path, thread_id=thread_id, limit=limit, offset=offset)
        return {"thread_id": thread_id, "items": [i.__dict__ for i in items]}

    @router.get("/api/runs/{run_id}")
    async def get_run(run_id: str) -> dict[str, Any]:
        item = store.get_run(db_path=db_path, run_id=run_id)
        if not item:
            raise HTTPException(404, f"Run not found: {run_id}")
        return item.__dict__

    @router.get("/api/runs/{run_id}/events")
    async def get_run_events(
        run_id: str,
        after_event_id: int = Query(default=0, ge=0),
        limit: int = Query(default=200, ge=1, le=1000),
    ) -> dict[str, Any]:
        events = store.list_events(db_path=db_path, run_id=run_id, after_event_id=after_event_id, limit=limit)
        return {
            "run_id": run_id,
            "after_event_id": after_event_id,
            "items": [
                {
                    "event_id": e.event_id,
                    "run_id": e.run_id,
                    "thread_id": e.thread_id,
                    "event_type": e.event_type,
                    "payload": e.payload,
                    "created_at": e.created_at,
                }
                for e in events
            ],
            "next_after_event_id": (events[-1].event_id if events else after_event_id),
        }

    return router


def create_operator_router(*, dp_db_path: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/api/operator/search")
    async def operator_search(
        q: str = Query(..., min_length=1),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        items = search_all(dp_db_path=dp_db_path, q=q, limit=limit)
        return {"q": q, "items": items, "count": len(items)}

    @router.get("/api/operator/sandboxes")
    async def operator_sandboxes(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
        items = list_active_sessions(limit=limit)
        return {"items": items, "count": len(items)}

    @router.get("/api/operator/threads/{thread_id}/commands")
    async def operator_thread_commands(
        thread_id: str,
        limit: int = Query(default=200, ge=1, le=1000),
    ) -> dict[str, Any]:
        items = list_thread_commands(thread_id=thread_id, limit=limit)
        return {"thread_id": thread_id, "items": items, "count": len(items)}

    @router.get("/api/operator/threads/{thread_id}/diagnostics")
    async def operator_thread_diagnostics(thread_id: str, request: Request) -> dict[str, Any]:
        # @@@print-not-match - Diagnostics should show raw runtime/DB truth, not guess via heuristics.
        # @@@e2e-evidence - See `teams/log/leonai/data_platform/2026-02-15_e2e_diagnostics.md`
        app = request.app

        latest_run = store.get_latest_run_for_thread(db_path=dp_db_path, thread_id=thread_id)
        last_event_id = store.get_last_event_id_for_run(db_path=dp_db_path, run_id=latest_run.run_id) if latest_run else 0

        # In-memory state (best-effort). Do not create agents here; only report what is already live.
        agent = None
        agent_pool = getattr(getattr(app, "state", None), "agent_pool", {}) or {}
        for k, v in agent_pool.items():
            if str(k).startswith(f"{thread_id}:"):
                agent = v
                break
        runtime = None
        if agent is not None and hasattr(agent, "runtime"):
            runtime = agent.runtime.get_status_dict()

        lock_obj = (getattr(getattr(app, "state", None), "thread_locks", {}) or {}).get(thread_id)
        lock_locked = None
        if lock_obj is not None and hasattr(lock_obj, "locked"):
            lock_locked = bool(lock_obj.locked())

        task_obj = (getattr(getattr(app, "state", None), "thread_tasks", {}) or {}).get(thread_id)
        task_info = None
        if task_obj is not None:
            task_info = {
                "exists": True,
                "done": bool(task_obj.done()) if hasattr(task_obj, "done") else None,
                "cancelled": bool(task_obj.cancelled()) if hasattr(task_obj, "cancelled") else None,
            }

        sessions = [s for s in list_active_sessions(limit=200) if s.get("thread_id") == thread_id]
        commands = list_thread_commands(thread_id=thread_id, limit=200)

        return {
            "thread_id": thread_id,
            "data_platform": {
                "latest_run": (latest_run.__dict__ if latest_run else None),
                "latest_run_last_event_id": last_event_id,
            },
            "runtime": runtime,
            "in_memory": {
                "thread_lock_locked": lock_locked,
                "thread_task": task_info or {"exists": False},
                "agent_pool_has_agent": agent is not None,
            },
            "sandbox_db": {
                "active_sessions": sessions,
                "commands": commands,
            },
        }

    @router.get("/api/operator/dashboards/overview")
    async def operator_dashboards_overview(
        window_hours: int = Query(default=24, ge=1, le=24 * 30),
        stuck_after_sec: int = Query(default=600, ge=1, le=24 * 3600),
    ) -> dict[str, Any]:
        return dashboards_overview(dp_db_path=dp_db_path, window_hours=window_hours, stuck_after_sec=stuck_after_sec)

    return router
