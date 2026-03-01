"""SSE streaming service for agent execution."""

import asyncio
import json
import uuid as _uuid
from collections.abc import AsyncGenerator
from typing import Any

from backend.web.services.event_buffer import RunEventBuffer
from backend.web.services.event_store import cleanup_old_runs
from backend.web.utils.serializers import extract_text_content
from core.monitor import AgentState
from storage.contracts import RunEventRepo
from sandbox.thread_context import set_current_run_id, set_current_thread_id


def _resolve_run_event_repo(agent: Any) -> RunEventRepo | None:
    storage_container = getattr(agent, "storage_container", None)
    if storage_container is None:
        return None

    # @@@runtime-storage-consumer - runtime run lifecycle must consume injected storage container, not assignment-only wiring.
    return storage_container.run_event_repo()


async def prime_sandbox(agent: Any, thread_id: str) -> None:
    """Prime sandbox session before tool calls to avoid race conditions."""

    def _prime_sandbox() -> None:
        mgr = agent._sandbox.manager
        mgr.enforce_idle_timeouts()
        terminal = mgr.terminal_store.get(thread_id)
        if terminal:
            existing = mgr.session_manager.get(thread_id, terminal.terminal_id)
            if existing and existing.status == "paused":
                if not agent._sandbox.resume_thread(thread_id):
                    raise RuntimeError(f"Failed to resume paused session for thread {thread_id}")
        agent._sandbox.ensure_session(thread_id)
        terminal = mgr.terminal_store.get(thread_id)
        lease = mgr.lease_store.get(terminal.lease_id) if terminal else None
        if lease:
            lease_status = lease.refresh_instance_status(mgr.provider)
            if lease_status == "paused" and mgr.provider_capability.can_resume:
                if not agent._sandbox.resume_thread(thread_id):
                    raise RuntimeError(f"Failed to auto-resume paused sandbox for thread {thread_id}")

    await asyncio.to_thread(_prime_sandbox)


async def write_cancellation_markers(
    agent: Any,
    config: dict[str, Any],
    pending_tool_calls: dict[str, dict],
) -> list[str]:
    """Write cancellation markers to checkpoint for pending tool calls.

    Returns:
        List of cancelled tool call IDs
    """
    cancelled_tool_call_ids = []
    if not pending_tool_calls or not agent:
        return cancelled_tool_call_ids

    try:
        from langchain_core.messages import ToolMessage
        from langgraph.checkpoint.base import create_checkpoint

        checkpointer = agent.agent.checkpointer
        if not checkpointer:
            return cancelled_tool_call_ids

        # aget_tuple returns CheckpointTuple with .checkpoint and .metadata
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        if not checkpoint_tuple:
            return cancelled_tool_call_ids

        checkpoint = checkpoint_tuple.checkpoint
        metadata = checkpoint_tuple.metadata or {}

        # Create ToolMessage for each pending tool call
        cancel_messages = []
        for tc_id, tc_info in pending_tool_calls.items():
            cancelled_tool_call_ids.append(tc_id)
            cancel_messages.append(
                ToolMessage(
                    content="任务被用户取消",
                    tool_call_id=tc_id,
                    name=tc_info["name"],
                )
            )

        # Update checkpoint with cancellation markers
        updated_channel_values = checkpoint["channel_values"].copy()
        updated_channel_values["messages"] = list(updated_channel_values.get("messages", []))
        updated_channel_values["messages"].extend(cancel_messages)

        # Prepare new versions for checkpoint
        new_versions = {k: int(v) + 1 for k, v in checkpoint["channel_versions"].items()}

        # Build complete checkpoint with all required fields
        new_checkpoint = create_checkpoint(checkpoint, None, metadata.get("step", 0))
        # Override channel_values with our updated messages
        new_checkpoint["channel_values"] = updated_channel_values

        # Write updated checkpoint
        await checkpointer.aput(
            config,
            new_checkpoint,
            {
                "source": "update",
                "step": metadata.get("step", 0),
                "writes": {},
            },
            new_versions,
        )
    except Exception as e:
        import traceback

        print(f"Failed to write cancellation markers: {e}")
        traceback.print_exc()

    return cancelled_tool_call_ids


# ---------------------------------------------------------------------------
# Producer: runs agent, writes events to buffer
# ---------------------------------------------------------------------------


async def _run_agent_to_buffer(
    agent: Any,
    thread_id: str,
    message: str,
    app: Any,
    enable_trajectory: bool,
    buf: RunEventBuffer,
) -> None:
    """Run agent execution and write all SSE events into *buf*."""
    from backend.web.services.event_store import append_event

    run_id = buf.run_id
    run_event_repo = _resolve_run_event_repo(agent)

    async def emit(event: dict, message_id: str | None = None) -> None:
        seq = await append_event(
            thread_id,
            run_id,
            event,
            message_id,
            run_event_repo=run_event_repo,
        )
        try:
            data = json.loads(event.get("data", "{}")) if isinstance(event.get("data"), str) else event.get("data", {})
        except (json.JSONDecodeError, TypeError):
            data = event.get("data", {})
        if isinstance(data, dict):
            data["_seq"] = seq
            data["_run_id"] = run_id
            if message_id:
                data["message_id"] = message_id
            event = {**event, "data": json.dumps(data, ensure_ascii=False)}
        await buf.put(event)

    task = None
    stream_gen = None
    pending_tool_calls: dict[str, dict] = {}
    try:
        config = {"configurable": {"thread_id": thread_id}}
        if hasattr(agent, "_current_model_config"):
            config["configurable"].update(agent._current_model_config)
        from core.queue import get_queue_manager

        config["configurable"]["queue_mode"] = get_queue_manager().get_mode(thread_id=thread_id).value
        set_current_thread_id(thread_id)
        # @@@web-run-context - web runs have no TUI checkpoint; use run_id to group file ops per run.
        set_current_run_id(run_id)

        # Trajectory tracing (eval system)
        tracer = None
        if enable_trajectory:
            try:
                from eval.tracer import TrajectoryTracer

                cost_calc = getattr(
                    getattr(getattr(agent, "runtime", None), "token", None),
                    "cost_calculator",
                    None,
                )
                tracer = TrajectoryTracer(
                    thread_id=thread_id,
                    user_message=message,
                    cost_calculator=cost_calc,
                )
                config["callbacks"] = [tracer]
            except ImportError:
                pass

        # Observation provider: provider from thread config, credentials from global config
        obs_handler = None
        obs_active = None
        try:
            from backend.web.utils.helpers import load_thread_config

            thread_cfg = load_thread_config(thread_id)
            obs_provider = thread_cfg.observation_provider if thread_cfg else None

            if obs_provider:
                from config.observation_loader import ObservationLoader

                obs_config = ObservationLoader().load()

                if obs_provider == "langfuse":
                    from langfuse import Langfuse
                    from langfuse.langchain import CallbackHandler as LangfuseHandler

                    cfg = obs_config.langfuse
                    if cfg.secret_key and cfg.public_key:
                        obs_active = "langfuse"
                        # Initialize global Langfuse client (CallbackHandler uses it)
                        Langfuse(
                            public_key=cfg.public_key,
                            secret_key=cfg.secret_key,
                            host=cfg.host or "https://cloud.langfuse.com",
                        )
                        obs_handler = LangfuseHandler(public_key=cfg.public_key)
                        config.setdefault("callbacks", []).append(obs_handler)
                        config.setdefault("metadata", {})["langfuse_session_id"] = thread_id
                elif obs_provider == "langsmith":
                    from langchain_core.tracers.langchain import LangChainTracer
                    from langsmith import Client as LangSmithClient

                    cfg = obs_config.langsmith
                    if cfg.api_key:
                        obs_active = "langsmith"
                        ls_client = LangSmithClient(
                            api_key=cfg.api_key,
                            api_url=cfg.endpoint or "https://api.smith.langchain.com",
                        )
                        obs_handler = LangChainTracer(
                            client=ls_client,
                            project_name=cfg.project or "default",
                        )
                        config.setdefault("callbacks", []).append(obs_handler)
                        config.setdefault("metadata", {})["session_id"] = thread_id
        except ImportError as imp_err:
            print(f"[streaming_service] Observation provider '{obs_provider}' requires missing package: {imp_err}. Install with: uv pip install 'leonai[{obs_provider}]'")
        except Exception as obs_err:
            print(f"[streaming_service] Observation handler error: {obs_err}")

        if hasattr(agent, "_sandbox"):
            await prime_sandbox(agent, thread_id)

        emitted_tool_call_ids: set[str] = set()

        async def run_agent_stream():
            async for chunk in agent.agent.astream(
                {"messages": [{"role": "user", "content": message}]},
                config=config,
                stream_mode=["messages", "updates"],
            ):
                yield chunk

        stream_gen = run_agent_stream()
        task = asyncio.create_task(stream_gen.__anext__())
        app.state.thread_tasks[thread_id] = task

        while True:
            try:
                chunk = await task
                task = asyncio.create_task(stream_gen.__anext__())
                app.state.thread_tasks[thread_id] = task
            except StopAsyncIteration:
                break
            except Exception as stream_error:
                import traceback

                traceback.print_exc()
                await emit({"event": "error", "data": json.dumps({"error": str(stream_error)}, ensure_ascii=False)})
                break
            if not chunk:
                continue

            if not isinstance(chunk, tuple) or len(chunk) != 2:
                continue
            mode, data = chunk

            if mode == "messages":
                msg_chunk, metadata = data
                msg_class = msg_chunk.__class__.__name__
                if msg_class == "AIMessageChunk":
                    content = extract_text_content(getattr(msg_chunk, "content", ""))
                    chunk_msg_id = getattr(msg_chunk, "id", None)
                    if content:
                        await emit(
                            {
                                "event": "text",
                                "data": json.dumps({"content": content}, ensure_ascii=False),
                            },
                            message_id=chunk_msg_id,
                        )

            elif mode == "updates":
                if not isinstance(data, dict):
                    continue
                for _node_name, node_update in data.items():
                    if not isinstance(node_update, dict):
                        continue
                    messages = node_update.get("messages", [])
                    if not isinstance(messages, list):
                        messages = [messages]
                    for msg in messages:
                        msg_class = msg.__class__.__name__
                        if msg_class == "AIMessage":
                            ai_msg_id = getattr(msg, "id", None)
                            for tc in getattr(msg, "tool_calls", []):
                                tc_id = tc.get("id")
                                if tc_id and tc_id in emitted_tool_call_ids:
                                    continue
                                if tc_id:
                                    emitted_tool_call_ids.add(tc_id)
                                    pending_tool_calls[tc_id] = {
                                        "name": tc.get("name", "unknown"),
                                        "args": tc.get("args", {}),
                                    }
                                await emit(
                                    {
                                        "event": "tool_call",
                                        "data": json.dumps(
                                            {
                                                "id": tc.get("id"),
                                                "name": tc.get("name", "unknown"),
                                                "args": tc.get("args", {}),
                                            },
                                            ensure_ascii=False,
                                        ),
                                    },
                                    message_id=ai_msg_id,
                                )
                        elif msg_class == "ToolMessage":
                            tc_id = getattr(msg, "tool_call_id", None)
                            tool_msg_id = getattr(msg, "id", None)
                            if tc_id:
                                pending_tool_calls.pop(tc_id, None)
                            await emit(
                                {
                                    "event": "tool_result",
                                    "data": json.dumps(
                                        {
                                            "tool_call_id": tc_id,
                                            "name": getattr(msg, "name", "unknown"),
                                            "content": str(getattr(msg, "content", "")),
                                        },
                                        ensure_ascii=False,
                                    ),
                                },
                                message_id=tool_msg_id,
                            )
                            if hasattr(agent, "runtime"):
                                status = agent.runtime.get_status_dict()
                                status["current_tool"] = getattr(msg, "name", None)
                                await emit(
                                    {
                                        "event": "status",
                                        "data": json.dumps(status, ensure_ascii=False),
                                    }
                                )

        # Forward sub-agent events
        if hasattr(agent, "runtime"):
            for tool_call_id, events in agent.runtime.get_pending_subagent_events():
                for event in events:
                    event_type = event.get("event", "")
                    event_data = json.loads(event.get("data", "{}"))
                    event_data["parent_tool_call_id"] = tool_call_id
                    await emit(
                        {
                            "event": f"subagent_{event_type}",
                            "data": json.dumps(event_data, ensure_ascii=False),
                        }
                    )

        # Final status
        if hasattr(agent, "runtime"):
            await emit(
                {
                    "event": "status",
                    "data": json.dumps(agent.runtime.get_status_dict(), ensure_ascii=False),
                }
            )

        # Persist trajectory
        if tracer is not None:
            try:
                from eval.storage import TrajectoryStore

                trajectory = tracer.to_trajectory()
                if hasattr(agent, "runtime"):
                    tracer.enrich_from_runtime(trajectory, agent.runtime)
                store = TrajectoryStore()
                store.save_trajectory(trajectory)
            except Exception:
                import traceback

                traceback.print_exc()

        await emit({"event": "done", "data": json.dumps({"thread_id": thread_id})})
    except asyncio.CancelledError:
        cancelled_tool_call_ids = await write_cancellation_markers(agent, config, pending_tool_calls)
        await emit(
            {
                "event": "cancelled",
                "data": json.dumps(
                    {
                        "message": "Run cancelled by user",
                        "cancelled_tool_call_ids": cancelled_tool_call_ids,
                    }
                ),
            }
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        await emit({"event": "error", "data": json.dumps({"error": str(e)}, ensure_ascii=False)})
    finally:
        # Flush observation handler
        if obs_handler is not None:
            try:
                if obs_active == "langfuse":
                    from langfuse import get_client
                    get_client().flush()
                elif obs_active == "langsmith":
                    obs_handler.wait_for_futures()
            except Exception:
                pass
        await buf.mark_done()
        app.state.thread_tasks.pop(thread_id, None)
        app.state.thread_event_buffers.pop(thread_id, None)
        if stream_gen is not None:
            await stream_gen.aclose()
        if agent and hasattr(agent, "runtime") and agent.runtime.current_state == AgentState.ACTIVE:
            agent.runtime.transition(AgentState.IDLE)
        try:
            await cleanup_old_runs(thread_id, keep_latest=1, run_event_repo=run_event_repo)
        except Exception:
            pass
        if run_event_repo is not None:
            run_event_repo.close()


# ---------------------------------------------------------------------------
# Orchestrator: creates buffer + launches background task
# ---------------------------------------------------------------------------


def start_agent_run(
    agent: Any,
    thread_id: str,
    message: str,
    app: Any,
    enable_trajectory: bool = False,
) -> RunEventBuffer:
    """Create a RunEventBuffer and launch the agent producer as a background task."""

    buf = RunEventBuffer()
    buf.run_id = str(_uuid.uuid4())
    app.state.thread_event_buffers[thread_id] = buf
    bg_task = asyncio.create_task(_run_agent_to_buffer(agent, thread_id, message, app, enable_trajectory, buf))
    # Store the background task so cancel_run can still cancel it
    app.state.thread_tasks[thread_id] = bg_task
    return buf


# ---------------------------------------------------------------------------
# Consumer: reads from buffer and yields SSE dicts
# ---------------------------------------------------------------------------


async def observe_run_events(
    buf: RunEventBuffer,
    after: int = 0,
) -> AsyncGenerator[dict[str, str], None]:
    """Consume events from a RunEventBuffer. Yields SSE event dicts.

    Safe to abort — does not affect the producer or agent state.
    When *after* > 0, skip events whose injected ``_seq`` <= after.
    Sends heartbeat comments every 30s to keep the connection alive.
    Each event includes an ``id`` field for Last-Event-ID reconnection.
    """
    # Tell the browser to reconnect after 5s if the connection drops
    yield {"retry": 5000}

    cursor = 0
    while True:
        events, cursor = await buf.read_with_timeout(cursor, timeout=30)
        if events is None and not buf.finished.is_set():
            yield {"comment": "keepalive"}
            continue
        if not events and buf.finished.is_set():
            break
        if not events:
            continue
        for event in events:
            # Parse data once, reuse for both after-filtering and id injection
            parsed_data = None
            try:
                parsed_data = json.loads(event.get("data", "{}"))
            except (json.JSONDecodeError, TypeError):
                pass

            if after > 0 and isinstance(parsed_data, dict):
                if parsed_data.get("_seq", 0) <= after:
                    continue

            # Inject SSE id from _seq for Last-Event-ID support
            seq_id = str(parsed_data["_seq"]) if isinstance(parsed_data, dict) and "_seq" in parsed_data else None
            if seq_id:
                yield {**event, "id": seq_id}
            else:
                yield event


# ---------------------------------------------------------------------------
# Task agent: buffer-based producer (same pattern as main agent)
# ---------------------------------------------------------------------------


def start_task_agent_run(
    thread_id: str,
    payload: Any,
    app: Any,
    sandbox_type: str,
) -> RunEventBuffer:
    """Create a RunEventBuffer and launch task agent as background task."""

    buf = RunEventBuffer()
    buf.run_id = str(_uuid.uuid4())
    app.state.thread_event_buffers[thread_id] = buf
    bg_task = asyncio.create_task(_run_task_agent_to_buffer(thread_id, payload, app, sandbox_type, buf))
    app.state.thread_tasks[thread_id] = bg_task
    return buf


async def _run_task_agent_to_buffer(
    thread_id: str,
    payload: Any,
    app: Any,
    sandbox_type: str,
    buf: RunEventBuffer,
) -> None:
    """Task agent producer — writes events to buffer."""
    try:
        set_current_thread_id(thread_id)
        from backend.web.services.agent_pool import get_or_create_agent

        agent = await get_or_create_agent(app, sandbox_type, thread_id=thread_id)

        # Get TaskMiddleware from agent
        task_middleware = None
        if hasattr(agent, "middleware"):
            for mw in agent.middleware:
                if mw.__class__.__name__ == "TaskMiddleware":
                    task_middleware = mw
                    break

        if not task_middleware:
            await buf.put(
                {
                    "event": "task_error",
                    "data": json.dumps({"error": "TaskMiddleware not available"}, ensure_ascii=False),
                }
            )
            return

        # Build task params
        params: dict[str, Any] = {
            "SubagentType": payload.subagent_type,
            "Prompt": payload.prompt,
        }
        if payload.description:
            params["Description"] = payload.description
        if payload.model:
            params["Model"] = payload.model
        if payload.max_turns:
            params["MaxTurns"] = payload.max_turns

        # Stream task execution into buffer
        async for event in task_middleware.run_task_streaming(params):
            await buf.put(event)

        await buf.put({"event": "done", "data": json.dumps({"thread_id": thread_id})})
    except Exception as e:
        import traceback

        traceback.print_exc()
        await buf.put(
            {
                "event": "task_error",
                "data": json.dumps({"error": str(e)}, ensure_ascii=False),
            }
        )
    finally:
        await buf.mark_done()
        app.state.thread_tasks.pop(thread_id, None)
        app.state.thread_event_buffers.pop(thread_id, None)
