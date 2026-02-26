from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.web.routers import workspace as workspace_router
from backend.web.services import agent_pool


def _make_app() -> SimpleNamespace:
    return SimpleNamespace(state=SimpleNamespace(thread_cwd={}, thread_sandbox={}, agent_pool={}))


async def _raise_disabled(*_args, **_kwargs):
    raise HTTPException(status_code=403, detail="Sandbox is disabled")


def _make_remote_agent(
    read_error: Exception | None = None,
    list_error: Exception | None = None,
) -> SimpleNamespace:
    class _Fs:
        def read_file(self, _path: str):
            if read_error:
                raise read_error
            return SimpleNamespace(content="ok", size=2)

        def list_dir(self, _path: str):
            if list_error:
                raise list_error
            return SimpleNamespace(error=None, entries=[])

    class _Manager:
        def get_sandbox(self, _thread_id: str):
            return SimpleNamespace(
                fs=_Fs(),
                _session=SimpleNamespace(terminal=SimpleNamespace(get_state=lambda: SimpleNamespace(cwd="/tmp"))),
            )

    return SimpleNamespace(_sandbox=SimpleNamespace(name="e2b", manager=_Manager()))


@pytest.mark.asyncio
async def test_list_workspace_path_preserves_http_exception_from_agent_init(monkeypatch):
    monkeypatch.setattr(workspace_router, "resolve_thread_sandbox", lambda *_args, **_kwargs: "e2b")
    monkeypatch.setattr(agent_pool, "get_or_create_agent", _raise_disabled)

    with pytest.raises(HTTPException) as exc_info:
        await workspace_router.list_workspace_path("thread-1", app=_make_app())

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Sandbox is disabled"


@pytest.mark.asyncio
async def test_read_workspace_file_preserves_http_exception_from_agent_init(monkeypatch):
    monkeypatch.setattr(workspace_router, "resolve_thread_sandbox", lambda *_args, **_kwargs: "e2b")
    monkeypatch.setattr(agent_pool, "get_or_create_agent", _raise_disabled)

    with pytest.raises(HTTPException) as exc_info:
        await workspace_router.read_workspace_file("thread-2", path="/tmp/x", app=_make_app())

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Sandbox is disabled"


@pytest.mark.asyncio
async def test_read_workspace_file_preserves_http_exception_from_remote_fs(monkeypatch):
    async def _get_agent(*_args, **_kwargs):
        return _make_remote_agent(read_error=HTTPException(status_code=409, detail="Conflict"))

    monkeypatch.setattr(workspace_router, "resolve_thread_sandbox", lambda *_args, **_kwargs: "e2b")
    monkeypatch.setattr(agent_pool, "get_or_create_agent", _get_agent)

    with pytest.raises(HTTPException) as exc_info:
        await workspace_router.read_workspace_file("thread-3", path="/tmp/x", app=_make_app())

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Conflict"


@pytest.mark.asyncio
async def test_list_workspace_path_preserves_http_exception_from_remote_fs(monkeypatch):
    async def _get_agent(*_args, **_kwargs):
        return _make_remote_agent(list_error=HTTPException(status_code=429, detail="Rate limited"))

    monkeypatch.setattr(workspace_router, "resolve_thread_sandbox", lambda *_args, **_kwargs: "e2b")
    monkeypatch.setattr(agent_pool, "get_or_create_agent", _get_agent)

    with pytest.raises(HTTPException) as exc_info:
        await workspace_router.list_workspace_path("thread-4", path="/tmp/x", app=_make_app())

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == "Rate limited"
