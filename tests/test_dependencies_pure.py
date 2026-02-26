from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.web.core import dependencies


def _make_app() -> SimpleNamespace:
    return SimpleNamespace(state=SimpleNamespace(thread_sandbox={}, thread_cwd={}, agent_pool={}))


@pytest.mark.asyncio
async def test_get_thread_agent_preserves_http_exception(monkeypatch):
    async def _raise_policy(*_args, **_kwargs):
        raise HTTPException(status_code=429, detail="Rate limited")

    monkeypatch.setattr(dependencies, "resolve_thread_sandbox", lambda *_args, **_kwargs: "e2b")
    monkeypatch.setattr(dependencies, "get_or_create_agent", _raise_policy)

    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_thread_agent(_make_app(), "thread-1")

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == "Rate limited"


@pytest.mark.asyncio
async def test_get_thread_agent_wraps_unexpected_error_as_503(monkeypatch):
    async def _raise_unexpected(*_args, **_kwargs):
        raise RuntimeError("boot failed")

    monkeypatch.setattr(dependencies, "resolve_thread_sandbox", lambda *_args, **_kwargs: "e2b")
    monkeypatch.setattr(dependencies, "get_or_create_agent", _raise_unexpected)

    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_thread_agent(_make_app(), "thread-2")

    assert exc_info.value.status_code == 503
    assert "boot failed" in str(exc_info.value.detail)
