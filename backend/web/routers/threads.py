"""Thread management and execution endpoints."""

import asyncio
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from backend.web.core.dependencies import get_app, get_thread_agent, get_thread_lock
from backend.web.models.requests import (
    CreateThreadRequest,
    QueueModeRequest,
    RunRequest,
    SteerRequest,
    TaskAgentRequest,
)
from backend.web.services.agent_pool import get_or_create_agent, resolve_thread_sandbox
from backend.web.services.sandbox_service import destroy_thread_resources_sync
from backend.web.services.streaming_service import stream_agent_execution, stream_task_agent_execution
from backend.web.services.thread_service import list_threads_from_db
from backend.web.services.thread_state_service import (
    get_lease_status,
    get_sandbox_info,
    get_session_status,
    get_terminal_status,
)
from backend.web.utils.helpers import delete_thread_in_db
from backend.web.utils.serializers import serialize_message
from core.monitor import AgentState
from core.queue import QueueMode, get_queue_manager
from sandbox.thread_context import set_current_thread_id

router = APIRouter(prefix="/api/threads", tags=["threads"])


@router.post("")
async def create_thread(
    payload: CreateThreadRequest | None = None,
    app: Annotated[Any, Depends(get_app)] = None,
) -> dict[str, Any]:
    """Create a new thread with optional sandbox and cwd."""
    from backend.web.utils.helpers import save_thread_metadata

    sandbox_type = payload.sandbox if payload else "local"
    thread_id = str(uuid.uuid4())
    cwd = payload.cwd if payload else None
    app.state.thread_sandbox[thread_id] = sandbox_type
    if cwd:
        app.state.thread_cwd[thread_id] = cwd
    save_thread_metadata(thread_id, sandbox_type, cwd)
    return {"thread_id": thread_id, "sandbox": sandbox_type}


@router.get("")
async def list_threads(app: Annotated[Any, Depends(get_app)] = None) -> dict[str, Any]:
    """List all threads with metadata."""
    threads = await asyncio.to_thread(list_threads_from_db)
    # Enrich with sandbox info
    for t in threads:
        t["sandbox"] = resolve_thread_sandbox(app, t["thread_id"])
    return {"threads": threads}


@router.get("/{thread_id}")
async def get_thread_messages(
    thread_id: str,
    app: Annotated[Any, Depends(get_app)] = None,
) -> dict[str, Any]:
    """Get messages and sandbox info for a thread."""
    sandbox_type = resolve_thread_sandbox(app, thread_id)
    agent = await get_or_create_agent(app, sandbox_type, thread_id=thread_id)
    set_current_thread_id(thread_id)  # Set thread_id before accessing agent state
    config = {"configurable": {"thread_id": thread_id}}
    state = await agent.agent.aget_state(config)

    values = getattr(state, "values", {}) if state else {}
    messages = values.get("messages", []) if isinstance(values, dict) else []

    # Get sandbox session info (new architecture)
    sandbox_info = get_sandbox_info(agent, thread_id, sandbox_type)

    return {
        "thread_id": thread_id,
        "messages": [serialize_message(msg) for msg in messages],
        "sandbox": sandbox_info,
    }


@router.delete("/{thread_id}")
async def delete_thread(
    thread_id: str,
    app: Annotated[Any, Depends(get_app)] = None,
) -> dict[str, Any]:
    """Delete a thread and its resources."""
    sandbox_type = resolve_thread_sandbox(app, thread_id)
    pool_key = f"{thread_id}:{sandbox_type}"

    lock = await get_thread_lock(app, thread_id)
    async with lock:
        agent = app.state.agent_pool.get(pool_key)
        if agent and hasattr(agent, "runtime") and agent.runtime.current_state == AgentState.ACTIVE:
            raise HTTPException(status_code=409, detail="Cannot delete thread while run is in progress")
        try:
            await asyncio.to_thread(destroy_thread_resources_sync, thread_id, sandbox_type, app.state.agent_pool)
        except Exception as exc:
            raise HTTPException(status_code=409, detail=f"Failed to destroy sandbox resources: {exc}") from exc
        await asyncio.to_thread(delete_thread_in_db, thread_id)

    # Clean up thread-specific state
    app.state.thread_sandbox.pop(thread_id, None)
    app.state.thread_cwd.pop(thread_id, None)

    # Remove per-thread Agent from pool
    app.state.agent_pool.pop(pool_key, None)

    return {"ok": True, "thread_id": thread_id}


@router.post("/{thread_id}/steer")
async def steer_thread(thread_id: str, payload: SteerRequest) -> dict[str, Any]:
    """Add a message to the queue for steering."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")
    queue_manager = get_queue_manager()
    # Use the current default mode set by the user
    queue_manager.enqueue(payload.message)
    return {"ok": True, "thread_id": thread_id, "mode": queue_manager.get_mode().value}


@router.post("/{thread_id}/queue-mode")
async def set_thread_queue_mode(thread_id: str, payload: QueueModeRequest) -> dict[str, Any]:
    """Set queue mode for a thread."""
    try:
        mode = QueueMode(payload.mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid queue mode: {payload.mode}")
    queue_manager = get_queue_manager()
    queue_manager.set_mode(mode)
    return {"ok": True, "thread_id": thread_id, "mode": mode.value}


@router.get("/{thread_id}/queue-mode")
async def get_thread_queue_mode(thread_id: str) -> dict[str, Any]:
    """Get current queue mode for a thread."""
    queue_manager = get_queue_manager()
    return {"mode": queue_manager.get_mode().value}


@router.get("/{thread_id}/runtime")
async def get_thread_runtime(
    thread_id: str,
    app: Annotated[Any, Depends(get_app)] = None,
) -> dict[str, Any]:
    """Get runtime status for a thread."""
    from backend.web.utils.helpers import lookup_thread_model

    sandbox_type = resolve_thread_sandbox(app, thread_id)
    agent = await get_or_create_agent(app, sandbox_type, thread_id=thread_id)
    if not hasattr(agent, "runtime"):
        raise HTTPException(status_code=404, detail="Agent has no runtime monitor")
    status = agent.runtime.get_status_dict()
    # Include per-thread model
    status["model"] = lookup_thread_model(thread_id)
    return status


# Sandbox control endpoints for threads
@router.post("/{thread_id}/sandbox/pause")
async def pause_thread_sandbox(
    thread_id: str,
    agent: Annotated[Any, Depends(get_thread_agent)] = None,
) -> dict[str, Any]:
    """Pause sandbox for a thread."""
    try:
        ok = await asyncio.to_thread(agent._sandbox.pause_thread, thread_id)
        if not ok:
            raise HTTPException(409, f"Failed to pause sandbox for thread {thread_id}")
        return {"ok": ok, "thread_id": thread_id}
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e


@router.post("/{thread_id}/sandbox/resume")
async def resume_thread_sandbox(
    thread_id: str,
    agent: Annotated[Any, Depends(get_thread_agent)] = None,
) -> dict[str, Any]:
    """Resume paused sandbox for a thread."""
    try:
        ok = await asyncio.to_thread(agent._sandbox.resume_thread, thread_id)
        if not ok:
            raise HTTPException(409, f"Failed to resume sandbox for thread {thread_id}")
        return {"ok": ok, "thread_id": thread_id}
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e


@router.delete("/{thread_id}/sandbox")
async def destroy_thread_sandbox(
    thread_id: str,
    agent: Annotated[Any, Depends(get_thread_agent)] = None,
) -> dict[str, Any]:
    """Destroy sandbox session for a thread."""
    try:
        ok = await asyncio.to_thread(agent._sandbox.manager.destroy_session, thread_id)
        if not ok:
            raise HTTPException(404, f"No sandbox session found for thread {thread_id}")
        agent._sandbox._capability_cache.pop(thread_id, None)
        return {"ok": ok, "thread_id": thread_id}
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e


# Session/terminal/lease status endpoints
@router.get("/{thread_id}/session")
async def get_thread_session_status(
    thread_id: str,
    agent: Annotated[Any, Depends(get_thread_agent)] = None,
) -> dict[str, Any]:
    """Get ChatSession status for a thread."""
    try:
        return await get_session_status(agent, thread_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/{thread_id}/terminal")
async def get_thread_terminal_status(
    thread_id: str,
    agent: Annotated[Any, Depends(get_thread_agent)] = None,
) -> dict[str, Any]:
    """Get AbstractTerminal state for a thread."""
    try:
        return await get_terminal_status(agent, thread_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/{thread_id}/lease")
async def get_thread_lease_status(
    thread_id: str,
    agent: Annotated[Any, Depends(get_thread_agent)] = None,
) -> dict[str, Any]:
    """Get SandboxLease status for a thread."""
    try:
        return await get_lease_status(agent, thread_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


# Run endpoint (SSE streaming)
@router.post("/{thread_id}/runs")
async def run_thread(
    thread_id: str,
    payload: RunRequest,
    app: Annotated[Any, Depends(get_app)] = None,
) -> EventSourceResponse:
    """Execute agent run with SSE streaming."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    sandbox_type = resolve_thread_sandbox(app, thread_id)
    set_current_thread_id(thread_id)
    agent = await get_or_create_agent(app, sandbox_type, thread_id=thread_id)
    lock = await get_thread_lock(app, thread_id)
    async with lock:
        if hasattr(agent, "runtime") and not agent.runtime.transition(AgentState.ACTIVE):
            raise HTTPException(status_code=409, detail="Thread is already running")

    return EventSourceResponse(
        stream_agent_execution(agent, thread_id, payload.message, app, payload.enable_trajectory)
    )


@router.post("/{thread_id}/runs/cancel")
async def cancel_run(
    thread_id: str,
    app: Annotated[Any, Depends(get_app)] = None,
):
    """Cancel an active run for the given thread."""
    task = app.state.thread_tasks.get(thread_id)
    if not task:
        return {"ok": False, "message": "No active run found"}
    task.cancel()
    return {"ok": True, "message": "Run cancellation requested"}


@router.post("/{thread_id}/task-agent/stream")
async def stream_task_agent(
    thread_id: str,
    payload: TaskAgentRequest,
    app: Annotated[Any, Depends(get_app)] = None,
) -> EventSourceResponse:
    """Stream Task agent execution with real-time progress updates."""
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt cannot be empty")

    sandbox_type = resolve_thread_sandbox(app, thread_id)
    return EventSourceResponse(stream_task_agent_execution(thread_id, payload, app, sandbox_type))
