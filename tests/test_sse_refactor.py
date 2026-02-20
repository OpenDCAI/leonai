"""Focused regression tests for backend SSE execution path."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sse_starlette.sse import EventSourceResponse

from backend.web.models.requests import RunRequest
from backend.web.services.streaming_service import stream_agent_execution
from core.monitor import AgentState


class AIMessageChunk:
    def __init__(self, content: str):
        self.content = content


class _FakeRuntime:
    def __init__(self) -> None:
        self.current_state = AgentState.ACTIVE
        self.transitions: list[AgentState] = []

    def transition(self, state: AgentState) -> bool:
        self.transitions.append(state)
        self.current_state = state
        return True

    def get_pending_subagent_events(self):
        return []

    def get_status_dict(self):
        return {"state": self.current_state.value}


class _FakeLock:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _make_app():
    return SimpleNamespace(state=SimpleNamespace(thread_tasks={}))


def _import_threads_module():
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))
    loaded = sys.modules.get("config")
    if loaded and "tests/config" in str(getattr(loaded, "__file__", "")):
        del sys.modules["config"]
    from backend.web.routers import threads as threads_module

    return threads_module


@pytest.mark.asyncio
async def test_stream_agent_execution_emits_text_status_done_and_cleans_task():
    runtime = _FakeRuntime()

    class _InnerAgent:
        async def astream(self, *_args, **_kwargs):
            yield ("messages", (AIMessageChunk("hello"), {}))

    agent = SimpleNamespace(agent=_InnerAgent(), runtime=runtime)
    app = _make_app()

    events = []
    # @@@stream-drain - Exhaust async SSE generator to assert ordering + cleanup side effects.
    async for event in stream_agent_execution(agent, "t-1", "ping", app):
        events.append(event)

    assert [e["event"] for e in events] == ["text", "status", "done"]
    assert json.loads(events[0]["data"]) == {"content": "hello"}
    assert json.loads(events[2]["data"]) == {"thread_id": "t-1"}
    assert app.state.thread_tasks == {}
    assert runtime.transitions[-1] == AgentState.IDLE


@pytest.mark.asyncio
async def test_stream_agent_execution_surfaces_error_event_when_stream_fails():
    runtime = _FakeRuntime()

    class _InnerAgent:
        async def astream(self, *_args, **_kwargs):
            raise RuntimeError("boom")
            yield  # pragma: no cover

    agent = SimpleNamespace(agent=_InnerAgent(), runtime=runtime)
    app = _make_app()

    events = []
    async for event in stream_agent_execution(agent, "t-2", "ping", app):
        events.append(event)

    assert events[0]["event"] == "error"
    assert "boom" in json.loads(events[0]["data"])["error"]
    assert events[-1]["event"] == "done"
    assert app.state.thread_tasks == {}


@pytest.mark.asyncio
async def test_run_thread_rejects_empty_message():
    threads = _import_threads_module()
    with pytest.raises(HTTPException) as exc:
        await threads.run_thread("thread-1", RunRequest(message="   "), app=_make_app())
    assert exc.value.status_code == 400
    assert exc.value.detail == "message cannot be empty"


@pytest.mark.asyncio
async def test_run_thread_returns_sse_response_and_applies_model_override(monkeypatch):
    threads = _import_threads_module()
    lock = _FakeLock()
    runtime = _FakeRuntime()
    override_calls: list[str] = []

    def _update_config(*, model: str):
        override_calls.append(model)

    agent = SimpleNamespace(runtime=runtime, update_config=_update_config)

    async def _fake_get_agent(*_args, **_kwargs):
        return agent

    async def _fake_get_lock(*_args, **_kwargs):
        return lock

    async def _fake_to_thread(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    monkeypatch.setattr(threads, "resolve_thread_sandbox", lambda *_args, **_kwargs: "local")
    monkeypatch.setattr(threads, "get_or_create_agent", _fake_get_agent)
    monkeypatch.setattr(threads, "get_thread_lock", _fake_get_lock)
    monkeypatch.setattr(threads.asyncio, "to_thread", _fake_to_thread)

    app = _make_app()
    response = await threads.run_thread(
        "thread-2",
        RunRequest(message="hello", model="openai/gpt-5-mini"),
        app=app,
    )

    assert isinstance(response, EventSourceResponse)
    assert override_calls == ["openai/gpt-5-mini"]
    assert runtime.transitions[0] == AgentState.ACTIVE
