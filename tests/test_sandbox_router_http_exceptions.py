import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.web.routers import sandbox as sandbox_router


def test_pick_folder_preserves_http_exception_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox_router.sys, "platform", "linux")

    def _cancelled(*_args, **_kwargs):
        return SimpleNamespace(returncode=1, stdout="")

    monkeypatch.setattr(sandbox_router.subprocess, "run", _cancelled)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(sandbox_router.pick_folder())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "User cancelled folder selection"
