from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.web.routers import sandbox as sandbox_router


@pytest.mark.asyncio
async def test_pick_folder_cancel_preserves_400(monkeypatch):
    monkeypatch.setattr(sandbox_router.sys, "platform", "darwin")
    monkeypatch.setattr(
        sandbox_router.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout=""),
    )

    with pytest.raises(HTTPException) as exc_info:
        await sandbox_router.pick_folder()

    assert exc_info.value.status_code == 400
    assert "cancelled" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_pick_folder_preserves_explicit_http_exception(monkeypatch):
    monkeypatch.setattr(sandbox_router.sys, "platform", "darwin")

    def _raise_http(*_args, **_kwargs):
        raise HTTPException(status_code=409, detail="Selection locked")

    monkeypatch.setattr(sandbox_router.subprocess, "run", _raise_http)

    with pytest.raises(HTTPException) as exc_info:
        await sandbox_router.pick_folder()

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Selection locked"
