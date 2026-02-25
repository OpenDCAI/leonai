import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.web.routers import workspace as workspace_router
from backend.web.services import agent_pool


def _make_app():
    return SimpleNamespace(state=SimpleNamespace(thread_cwd={}, thread_sandbox={}, agent_pool={}))


async def _raise_disabled(*_args, **_kwargs):
    raise HTTPException(status_code=403, detail="Sandbox is disabled")


def test_list_workspace_path_keeps_http_status(monkeypatch):
    monkeypatch.setattr(workspace_router, "resolve_thread_sandbox", lambda *_args, **_kwargs: "e2b")
    monkeypatch.setattr(agent_pool, "get_or_create_agent", _raise_disabled)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(workspace_router.list_workspace_path("thread-1", app=_make_app()))
    assert exc_info.value.status_code == 403


def test_read_workspace_file_keeps_http_status(monkeypatch):
    monkeypatch.setattr(workspace_router, "resolve_thread_sandbox", lambda *_args, **_kwargs: "e2b")
    monkeypatch.setattr(agent_pool, "get_or_create_agent", _raise_disabled)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(workspace_router.read_workspace_file("thread-2", path="/tmp/x", app=_make_app()))
    assert exc_info.value.status_code == 403
