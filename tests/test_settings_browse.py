from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.web.routers import sandbox as sandbox_router
from backend.web.routers.settings import browse_filesystem
from backend.web.utils.helpers import extract_webhook_instance_id, resolve_local_workspace_path
from backend.web.routers import workspace as workspace_router
from backend.web.services import agent_pool


@pytest.mark.asyncio
async def test_browse_filesystem_keeps_404_for_missing_path(tmp_path):
    missing = tmp_path / "missing-dir"

    with pytest.raises(HTTPException) as exc_info:
        await browse_filesystem(path=str(missing))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Path does not exist"


@pytest.mark.asyncio
async def test_browse_filesystem_keeps_400_for_file_path(tmp_path):
    file_path = tmp_path / "not-a-directory.txt"
    file_path.write_text("x", encoding="utf-8")

    with pytest.raises(HTTPException) as exc_info:
        await browse_filesystem(path=str(file_path))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Path is not a directory"


def test_resolve_local_workspace_path_accepts_relative_workspace_root(tmp_path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    monkeypatch.chdir(tmp_path)

    resolved = resolve_local_workspace_path("src/main.py", local_workspace_root="workspace")

    assert resolved == (workspace_root / "src/main.py").resolve()

def test_extract_webhook_instance_id_trims_whitespace() -> None:
    assert extract_webhook_instance_id({"session_id": "  sess-123  "}) == "sess-123"
    assert extract_webhook_instance_id({"data": {"instance_id": "\n inst-9\t"}}) == "inst-9"
    assert extract_webhook_instance_id({"sandbox_id": "   "}) is None
@pytest.mark.asyncio
async def test_pick_folder_cancel_keeps_400(monkeypatch):
    monkeypatch.setattr(sandbox_router.sys, "platform", "darwin")
    monkeypatch.setattr(
        sandbox_router.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=""),
    )

    with pytest.raises(HTTPException) as exc_info:
        await sandbox_router.pick_folder()
    assert exc_info.value.status_code == 400
    assert "cancelled" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_pick_folder_timeout_is_408(monkeypatch):
    monkeypatch.setattr(sandbox_router.sys, "platform", "darwin")

    def _raise_timeout(*args, **kwargs):
        raise sandbox_router.subprocess.TimeoutExpired(cmd="osascript", timeout=60)

    monkeypatch.setattr(sandbox_router.subprocess, "run", _raise_timeout)

    with pytest.raises(HTTPException) as exc_info:
        await sandbox_router.pick_folder()
    assert exc_info.value.status_code == 408


def _make_app():
    return SimpleNamespace(state=SimpleNamespace(thread_cwd={}, thread_sandbox={}, agent_pool={}))


async def _raise_disabled(*_args, **_kwargs):
    raise HTTPException(status_code=403, detail="Sandbox is disabled")


@pytest.mark.asyncio
async def test_list_workspace_path_keeps_http_status(monkeypatch):
    monkeypatch.setattr(workspace_router, "resolve_thread_sandbox", lambda *_args, **_kwargs: "e2b")
    monkeypatch.setattr(agent_pool, "get_or_create_agent", _raise_disabled)

    with pytest.raises(HTTPException) as exc_info:
        await workspace_router.list_workspace_path("thread-1", app=_make_app())
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_read_workspace_file_keeps_http_status(monkeypatch):
    monkeypatch.setattr(workspace_router, "resolve_thread_sandbox", lambda *_args, **_kwargs: "e2b")
    monkeypatch.setattr(agent_pool, "get_or_create_agent", _raise_disabled)

    with pytest.raises(HTTPException) as exc_info:
        await workspace_router.read_workspace_file("thread-2", path="/tmp/x", app=_make_app())
    assert exc_info.value.status_code == 403
