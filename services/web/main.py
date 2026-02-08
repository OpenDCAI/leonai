from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agent import create_leon_agent
from middleware.monitor import AgentState
from middleware.queue import QueueMode, get_queue_manager
from sandbox.thread_context import set_current_thread_id
from tui.config import ConfigManager

DB_PATH = Path.home() / ".leon" / "leon.db"


class RunRequest(BaseModel):
    message: str


class SteerRequest(BaseModel):
    message: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    config_manager = ConfigManager()
    config_manager.load_to_env()

    agent = create_leon_agent(workspace_root=Path.cwd(), verbose=True)
    app.state.agent = agent
    app.state.thread_locks: dict[str, asyncio.Lock] = {}
    app.state.thread_locks_guard = asyncio.Lock()

    try:
        yield
    finally:
        agent.close()


app = FastAPI(title="Leon Web Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _get_thread_lock(app_obj: FastAPI, thread_id: str) -> asyncio.Lock:
    async with app_obj.state.thread_locks_guard:
        lock = app_obj.state.thread_locks.get(thread_id)
        if lock is None:
            lock = asyncio.Lock()
            app_obj.state.thread_locks[thread_id] = lock
        return lock


def _extract_text_content(raw_content: Any) -> str:
    if isinstance(raw_content, str):
        return raw_content
    if isinstance(raw_content, list):
        text_parts: list[str] = []
        for block in raw_content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif isinstance(block, str):
                text_parts.append(block)
        return "".join(text_parts)
    return str(raw_content)


def _serialize_message(msg: Any) -> dict[str, Any]:
    return {
        "type": msg.__class__.__name__,
        "content": getattr(msg, "content", ""),
        "tool_calls": getattr(msg, "tool_calls", []),
        "tool_call_id": getattr(msg, "tool_call_id", None),
    }


def _list_threads_from_db() -> list[dict[str, str]]:
    if not DB_PATH.exists():
        return []

    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT DISTINCT thread_id
            FROM checkpoints
            WHERE thread_id IS NOT NULL
            ORDER BY thread_id
            """
        ).fetchall()

    return [{"thread_id": row["thread_id"]} for row in rows if row["thread_id"]]


def _delete_thread_in_db(thread_id: str) -> None:
    if not DB_PATH.exists():
        return

    tables_to_clean = [
        "checkpoints",
        "checkpoint_writes",
        "checkpoint_blobs",
        "writes",
        "file_operations",
    ]

    with sqlite3.connect(str(DB_PATH)) as conn:
        existing_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

        for table in tables_to_clean:
            if table in existing_tables:
                conn.execute(f"DELETE FROM {table} WHERE thread_id = ?", (thread_id,))
        conn.commit()


@app.post("/api/threads")
async def create_thread() -> dict[str, str]:
    return {"thread_id": str(uuid.uuid4())}


@app.get("/api/threads")
async def list_threads() -> dict[str, list[dict[str, str]]]:
    return {"threads": _list_threads_from_db()}


@app.get("/api/threads/{thread_id}")
async def get_thread_messages(thread_id: str) -> dict[str, Any]:
    lock = await _get_thread_lock(app, thread_id)
    async with lock:
        config = {"configurable": {"thread_id": thread_id}}
        state = await app.state.agent.agent.aget_state(config)

    values = getattr(state, "values", {}) if state else {}
    messages = values.get("messages", []) if isinstance(values, dict) else []
    return {
        "thread_id": thread_id,
        "messages": [_serialize_message(msg) for msg in messages],
    }


@app.delete("/api/threads/{thread_id}")
async def delete_thread(thread_id: str) -> dict[str, bool | str]:
    lock = await _get_thread_lock(app, thread_id)
    async with lock:
        _delete_thread_in_db(thread_id)
    return {"ok": True, "thread_id": thread_id}


@app.post("/api/threads/{thread_id}/steer")
async def steer_thread(thread_id: str, payload: SteerRequest) -> dict[str, Any]:
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    queue_manager = get_queue_manager()
    queue_manager.enqueue(payload.message, mode=QueueMode.STEER)
    return {"ok": True, "thread_id": thread_id, "mode": QueueMode.STEER.value}


@app.post("/api/threads/{thread_id}/runs")
async def run_thread(thread_id: str, payload: RunRequest) -> EventSourceResponse:
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    async def event_stream() -> AsyncGenerator[dict[str, str], None]:
        lock = await _get_thread_lock(app, thread_id)
        async with lock:
            agent = app.state.agent
            config = {"configurable": {"thread_id": thread_id}}
            set_current_thread_id(thread_id)

            # @@@ Streaming parser mirrors TUI runner chunk semantics so web and CLI stay consistent.
            if hasattr(agent, "_sandbox") and agent._sandbox.name != "local":
                agent._sandbox.ensure_session(thread_id)

            if hasattr(agent, "runtime"):
                agent.runtime.transition(AgentState.ACTIVE)

            try:
                async for chunk in agent.agent.astream(
                    {"messages": [{"role": "user", "content": payload.message}]},
                    config=config,
                    stream_mode="updates",
                ):
                    if not chunk:
                        continue

                    for _node_name, node_update in chunk.items():
                        if not isinstance(node_update, dict):
                            continue

                        messages = node_update.get("messages", [])
                        if not isinstance(messages, list):
                            messages = [messages]

                        for msg in messages:
                            msg_class = msg.__class__.__name__

                            if msg_class == "AIMessage":
                                content = _extract_text_content(getattr(msg, "content", ""))
                                if content:
                                    yield {
                                        "event": "text",
                                        "data": json.dumps({"content": content}, ensure_ascii=False),
                                    }

                                tool_calls = getattr(msg, "tool_calls", [])
                                for tc in tool_calls:
                                    yield {
                                        "event": "tool_call",
                                        "data": json.dumps(
                                            {
                                                "id": tc.get("id"),
                                                "name": tc.get("name", "unknown"),
                                                "args": tc.get("args", {}),
                                            },
                                            ensure_ascii=False,
                                        ),
                                    }

                            elif msg_class == "ToolMessage":
                                yield {
                                    "event": "tool_result",
                                    "data": json.dumps(
                                        {
                                            "tool_call_id": getattr(msg, "tool_call_id", None),
                                            "name": getattr(msg, "name", "unknown"),
                                            "content": str(getattr(msg, "content", "")),
                                        },
                                        ensure_ascii=False,
                                    ),
                                }

                yield {"event": "done", "data": json.dumps({"thread_id": thread_id})}
            except Exception as e:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)}, ensure_ascii=False),
                }
            finally:
                if hasattr(agent, "runtime") and agent.runtime.current_state == AgentState.ACTIVE:
                    agent.runtime.transition(AgentState.IDLE)

    return EventSourceResponse(event_stream())
