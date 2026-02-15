"""SSE streaming service for agent execution."""

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

from core.monitor import AgentState
from sandbox.thread_context import set_current_thread_id

from ..utils.serializers import extract_text_content


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


async def stream_agent_execution(
    agent: Any,
    thread_id: str,
    message: str,
    app: Any,
) -> AsyncGenerator[dict[str, str], None]:
    """Stream agent execution with SSE events.

    Yields SSE events:
    - text: Token-level text streaming
    - tool_call: Tool invocation
    - tool_result: Tool completion
    - status: Runtime status updates
    - subagent_*: Sub-agent events
    - done: Execution complete
    - cancelled: Execution cancelled
    - error: Error occurred
    """
    task = None
    stream_gen = None
    try:
        config = {"configurable": {"thread_id": thread_id}}
        set_current_thread_id(thread_id)

        # Prime session before tool calls so lazy capability wrappers never race thread context propagation
        if hasattr(agent, "_sandbox"):
            await prime_sandbox(agent, thread_id)

        emitted_tool_call_ids: set[str] = set()
        pending_tool_calls: dict[str, dict] = {}  # Track in-flight tool calls for cancellation

        # Wrap astream in a task for cancellation support
        async def run_agent_stream():
            async for chunk in agent.agent.astream(
                {"messages": [{"role": "user", "content": message}]},
                config=config,
                stream_mode=["messages", "updates"],
            ):
                yield chunk

        # Create and track the task
        stream_gen = run_agent_stream()
        task = asyncio.create_task(stream_gen.__anext__())
        app.state.thread_tasks[thread_id] = task

        # Iterate through the stream
        while True:
            try:
                chunk = await task
                # Create next task immediately
                task = asyncio.create_task(stream_gen.__anext__())
                app.state.thread_tasks[thread_id] = task
            except StopAsyncIteration:
                break
            except Exception as stream_error:
                # Catch errors from the agent stream (e.g., API connection errors)
                import traceback

                traceback.print_exc()
                yield {"event": "error", "data": json.dumps({"error": str(stream_error)}, ensure_ascii=False)}
                break
            if not chunk:
                continue

            # stream_mode=["messages", "updates"] yields tuples: (mode, data)
            if not isinstance(chunk, tuple) or len(chunk) != 2:
                continue
            mode, data = chunk

            # --- Token-level streaming from "messages" mode ---
            if mode == "messages":
                msg_chunk, metadata = data
                msg_class = msg_chunk.__class__.__name__
                # Only stream AIMessageChunk tokens (not ToolMessage, HumanMessage, etc.)
                if msg_class == "AIMessageChunk":
                    content = extract_text_content(getattr(msg_chunk, "content", ""))
                    if content:
                        yield {
                            "event": "text",
                            "data": json.dumps({"content": content}, ensure_ascii=False),
                        }

            # --- Node-level updates from "updates" mode ---
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
                        # Skip AIMessage text — already streamed token-by-token via "messages" mode
                        # But still emit tool_calls from updates as a fallback
                        if msg_class == "AIMessage":
                            for tc in getattr(msg, "tool_calls", []):
                                tc_id = tc.get("id")
                                if tc_id and tc_id in emitted_tool_call_ids:
                                    continue
                                if tc_id:
                                    emitted_tool_call_ids.add(tc_id)
                                    # Track pending tool call
                                    pending_tool_calls[tc_id] = {
                                        "name": tc.get("name", "unknown"),
                                        "args": tc.get("args", {}),
                                    }
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
                            tc_id = getattr(msg, "tool_call_id", None)
                            # Remove from pending when tool completes
                            if tc_id:
                                pending_tool_calls.pop(tc_id, None)
                            yield {
                                "event": "tool_result",
                                "data": json.dumps(
                                    {
                                        "tool_call_id": tc_id,
                                        "name": getattr(msg, "name", "unknown"),
                                        "content": str(getattr(msg, "content", "")),
                                    },
                                    ensure_ascii=False,
                                ),
                            }
                            # Emit runtime status after each tool result
                            if hasattr(agent, "runtime"):
                                status = agent.runtime.get_status_dict()
                                status["current_tool"] = getattr(msg, "name", None)
                                yield {
                                    "event": "status",
                                    "data": json.dumps(status, ensure_ascii=False),
                                }

        # --- Forward sub-agent events ---
        if hasattr(agent, "runtime"):
            for tool_call_id, events in agent.runtime.get_pending_subagent_events():
                for event in events:
                    # Parse event data and add parent_tool_call_id
                    event_type = event.get("event", "")
                    event_data = json.loads(event.get("data", "{}"))
                    event_data["parent_tool_call_id"] = tool_call_id

                    # Emit with subagent_ prefix
                    yield {
                        "event": f"subagent_{event_type}",
                        "data": json.dumps(event_data, ensure_ascii=False),
                    }

        # Final status before done
        if hasattr(agent, "runtime"):
            yield {
                "event": "status",
                "data": json.dumps(agent.runtime.get_status_dict(), ensure_ascii=False),
            }
        yield {"event": "done", "data": json.dumps({"thread_id": thread_id})}
    except asyncio.CancelledError:
        # Write cancellation markers to checkpoint for pending tool calls
        cancelled_tool_call_ids = await write_cancellation_markers(agent, config, pending_tool_calls)

        yield {
            "event": "cancelled",
            "data": json.dumps(
                {
                    "message": "Run cancelled by user",
                    "cancelled_tool_call_ids": cancelled_tool_call_ids,
                }
            ),
        }
    except Exception as e:
        import traceback

        traceback.print_exc()
        yield {"event": "error", "data": json.dumps({"error": str(e)}, ensure_ascii=False)}
    finally:
        # Clean up task tracking and stream generator
        app.state.thread_tasks.pop(thread_id, None)
        if stream_gen is not None:
            await stream_gen.aclose()
        if agent and hasattr(agent, "runtime") and agent.runtime.current_state == AgentState.ACTIVE:
            agent.runtime.transition(AgentState.IDLE)


async def stream_task_agent_execution(
    thread_id: str,
    payload: Any,
    app: Any,
    sandbox_type: str,
) -> AsyncGenerator[dict[str, str], None]:
    """Stream task agent execution with real-time progress updates.

    Yields SSE events:
    - task_*: Task-specific events from TaskMiddleware
    - task_error: Error occurred
    """
    agent = None
    try:
        set_current_thread_id(thread_id)
        # Import here to avoid circular dependency
        from ..services.agent_pool import get_or_create_agent

        agent = await get_or_create_agent(app, sandbox_type, thread_id=thread_id)

        # Get TaskMiddleware from agent
        task_middleware = None
        if hasattr(agent, "middleware"):
            for mw in agent.middleware:
                if mw.__class__.__name__ == "TaskMiddleware":
                    task_middleware = mw
                    break

        if not task_middleware:
            yield {
                "event": "task_error",
                "data": json.dumps({"error": "TaskMiddleware not available"}, ensure_ascii=False),
            }
            return

        # Build task params
        params: TaskParams = {
            "SubagentType": payload.subagent_type,
            "Prompt": payload.prompt,
        }
        if payload.description:
            params["Description"] = payload.description
        if payload.model:
            params["Model"] = payload.model
        if payload.max_turns:
            params["MaxTurns"] = payload.max_turns

        # Stream task execution
        async for event in task_middleware.run_task_streaming(params):
            yield event

    except Exception as e:
        import traceback

        traceback.print_exc()
        yield {
            "event": "task_error",
            "data": json.dumps({"error": str(e)}, ensure_ascii=False),
        }
