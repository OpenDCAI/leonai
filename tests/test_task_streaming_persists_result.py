import asyncio

import pytest

from middleware.task.subagent import SubagentRunner
from middleware.task.types import AgentConfig


class _StubAgent:
    def __init__(self):
        self._chunks = []

    async def astream(self, _input, *, config, stream_mode):
        # Emit one token chunk and then end.
        yield (
            "messages",
            (
                type("AIMessageChunk", (), {"content": "hello"})(),
                {},
            ),
        )
        yield (
            "updates",
            {
                "node": {
                    "messages": [type("AIMessage", (), {"tool_calls": []})()],
                }
            },
        )


@pytest.mark.asyncio
async def test_run_streaming_stores_task_result(monkeypatch, tmp_path):
    agents = {
        "general": AgentConfig(
            name="general",
            description="stub",
            system_prompt="stub",
            tools=[],
            model=None,
            max_turns=1,
        )
    }

    runner = SubagentRunner(
        agents=agents,
        parent_model="gpt-4",
        workspace_root=tmp_path,
        api_key="test",
        model_kwargs={},
    )

    # Avoid real model/agent construction.
    monkeypatch.setattr("middleware.task.subagent.init_chat_model", lambda *a, **k: object())
    monkeypatch.setattr("middleware.task.subagent.create_agent", lambda *a, **k: _StubAgent())

    params = {"SubagentType": "general", "Prompt": "hi"}
    events = []
    async for ev in runner.run_streaming(params=params, all_middleware=[], checkpointer=None):
        events.append(ev)

    assert any(e["event"] == "task_start" for e in events)
    assert any(e["event"] == "task_text" for e in events)
    assert any(e["event"] == "task_done" for e in events)

    task_id = None
    for e in events:
        if e["event"] == "task_start":
            import json

            task_id = json.loads(e["data"])["task_id"]
            break
    assert task_id

    result = runner.get_task_status(task_id)
    assert result.status == "completed"
    assert (result.result or "").startswith("hello")
