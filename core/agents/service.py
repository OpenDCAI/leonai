"""AgentService - Registers Agent/TaskOutput/TaskStop tools into ToolRegistry.

Wraps SubagentRunner to provide CC-compatible Agent tool interface,
with AgentRegistry integration for name-based routing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from core.agents.registry import AgentEntry, AgentRegistry
from core.runtime.registry import ToolEntry, ToolMode, ToolRegistry
from core.task.registry import BackgroundTaskRegistry
from core.task.subagent import SubagentRunner
from core.task.types import TaskParams, TaskResult

logger = logging.getLogger(__name__)

AGENT_SCHEMA = {
    "name": "Agent",
    "description": (
        "Launch a new agent to handle complex tasks autonomously. "
        "Use subagent_type to select a specialized agent, or omit for default."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "subagent_type": {
                "type": "string",
                "description": "Type of agent to spawn (e.g. 'Explore', 'Coder')",
            },
            "prompt": {
                "type": "string",
                "description": "Task for the agent",
            },
            "name": {
                "type": "string",
                "description": "Name for the agent (used for SendMessage routing)",
            },
            "description": {
                "type": "string",
                "description": "Short description of what agent will do",
            },
            "run_in_background": {
                "type": "boolean",
                "default": False,
                "description": "Run agent as a background task",
            },
            "resume": {
                "type": "string",
                "description": "Agent ID to resume",
            },
            "max_turns": {
                "type": "integer",
                "description": "Maximum turns",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in milliseconds",
                "default": 300000,
            },
        },
        "required": ["prompt"],
    },
}

TASK_OUTPUT_SCHEMA = {
    "name": "TaskOutput",
    "description": "Get the output of a background task by its TaskId.",
    "parameters": {
        "type": "object",
        "properties": {
            "TaskId": {
                "type": "string",
                "description": "The task ID returned when starting a background task",
            },
        },
        "required": ["TaskId"],
    },
}

TASK_STOP_SCHEMA = {
    "name": "TaskStop",
    "description": "Stop a running background task.",
    "parameters": {
        "type": "object",
        "properties": {
            "TaskId": {
                "type": "string",
                "description": "The task ID to stop",
            },
        },
        "required": ["TaskId"],
    },
}


class AgentService:
    """Registers Agent, TaskOutput, TaskStop tools into ToolRegistry.

    Wraps SubagentRunner for actual agent execution, and uses AgentRegistry
    for name -> thread_id mapping (enabling SendMessage routing).
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        subagent_runner: SubagentRunner,
        agent_registry: AgentRegistry,
        task_registry: BackgroundTaskRegistry,
        all_middleware: list[Any],
        current_thread_id: str | None = None,
    ):
        self._subagent_runner = subagent_runner
        self._agent_registry = agent_registry
        self._task_registry = task_registry
        self._all_middleware = all_middleware
        self._current_thread_id = current_thread_id

        tool_registry.register(ToolEntry(
            name="Agent",
            mode=ToolMode.INLINE,
            schema=AGENT_SCHEMA,
            handler=self._handle_agent,
            source="AgentService",
        ))
        tool_registry.register(ToolEntry(
            name="TaskOutput",
            mode=ToolMode.INLINE,
            schema=TASK_OUTPUT_SCHEMA,
            handler=self._handle_task_output,
            source="AgentService",
        ))
        tool_registry.register(ToolEntry(
            name="TaskStop",
            mode=ToolMode.INLINE,
            schema=TASK_STOP_SCHEMA,
            handler=self._handle_task_stop,
            source="AgentService",
        ))

    async def _handle_agent(
        self,
        prompt: str,
        subagent_type: str = "General",
        name: str | None = None,
        description: str | None = None,
        run_in_background: bool = False,
        resume: str | None = None,
        max_turns: int | None = None,
        timeout: int = 300000,
    ) -> str:
        """Handle Agent tool call - spawn a sub-agent via SubagentRunner."""
        agent_id = str(uuid.uuid4())[:8]
        agent_name = name or f"agent-{agent_id}"

        params: TaskParams = {
            "SubagentType": subagent_type,
            "Prompt": prompt,
        }
        if description:
            params["Description"] = description
        if run_in_background:
            params["RunInBackground"] = True
        if resume:
            params["Resume"] = resume
        if max_turns is not None:
            params["MaxTurns"] = max_turns

        result: TaskResult = await self._subagent_runner.run(
            params=params,
            all_middleware=self._all_middleware,
            parent_thread_id=self._current_thread_id,
        )

        # Register agent in AgentRegistry for name-based routing
        thread_id = result.thread_id or f"subagent_{result.task_id}"
        await self._agent_registry.register(AgentEntry(
            agent_id=agent_id,
            name=agent_name,
            thread_id=thread_id,
            status="running" if result.status == "running" else result.status,
            parent_agent_id=self._current_thread_id,
            subagent_type=subagent_type,
        ))

        if result.status == "completed":
            await self._agent_registry.update_status(agent_id, "completed")

        return self._format_result(result, agent_name)

    async def _handle_task_output(self, TaskId: str) -> str:
        """Get output of a background task."""
        result = await self._subagent_runner.get_task_status(TaskId)

        if result.status == "running":
            # Include buffered text if available
            entry = await self._task_registry.get(TaskId)
            if entry and entry.text_buffer:
                partial = "".join(entry.text_buffer[-50:])
                return json.dumps({
                    "task_id": TaskId,
                    "status": "running",
                    "partial_output": partial,
                }, ensure_ascii=False)
            return json.dumps({"task_id": TaskId, "status": "running"})

        return json.dumps({
            "task_id": TaskId,
            "status": result.status,
            "result": result.result,
            "error": result.error,
        }, ensure_ascii=False)

    async def _handle_task_stop(self, TaskId: str) -> str:
        """Stop a running background task."""
        entry = await self._task_registry.get(TaskId)
        if not entry:
            return f"Error: task '{TaskId}' not found"

        if entry.status != "running":
            return f"Task {TaskId} is already {entry.status}"

        # Cancel the async task
        if entry._async_task and not entry._async_task.done():
            entry._async_task.cancel()
            await self._task_registry.update(TaskId, status="error", error="Stopped by user")
            return f"Task {TaskId} stopped"

        return f"Task {TaskId} has no cancellable process"

    def _format_result(self, result: TaskResult, agent_name: str) -> str:
        """Format TaskResult for LLM consumption."""
        data: dict[str, Any] = {
            "task_id": result.task_id,
            "agent_name": agent_name,
            "status": result.status,
        }
        if result.result:
            data["result"] = result.result
        if result.error:
            data["error"] = result.error
        if result.thread_id:
            data["thread_id"] = result.thread_id
        return json.dumps(data, ensure_ascii=False)
