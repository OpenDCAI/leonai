import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.web.routers import sandbox as sandbox_router


def test_pick_folder_cancel_keeps_400(monkeypatch):
    monkeypatch.setattr(sandbox_router.sys, "platform", "darwin")
    monkeypatch.setattr(
        sandbox_router.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=""),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(sandbox_router.pick_folder())
    assert exc_info.value.status_code == 400
    assert "cancelled" in str(exc_info.value.detail).lower()


def test_pick_folder_timeout_is_408(monkeypatch):
    monkeypatch.setattr(sandbox_router.sys, "platform", "darwin")

    def _raise_timeout(*args, **kwargs):
        raise sandbox_router.subprocess.TimeoutExpired(cmd="osascript", timeout=60)

    monkeypatch.setattr(sandbox_router.subprocess, "run", _raise_timeout)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(sandbox_router.pick_folder())
    assert exc_info.value.status_code == 408
