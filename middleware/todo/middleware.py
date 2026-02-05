"""
Todo Middleware - Task management and progress tracking

Tools:
- TaskCreate: Create a new task with subject, description, activeForm
- TaskGet: Get full details of a task by ID
- TaskList: List all tasks with summary info
- TaskUpdate: Update task status, dependencies, or delete
- TaskOutput: Get output from background tasks

Status flow: pending → in_progress → completed
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
    ToolCallRequest,
)
from langchain_core.messages import ToolMessage

from .types import Task, TaskStatus


class TodoMiddleware(AgentMiddleware):
    """
    Todo Middleware - Task management and progress tracking

    Features:
    - Create, read, update, delete tasks
    - Task dependencies (blocks/blockedBy)
    - Status tracking (pending → in_progress → completed)
    """

    TOOL_TASK_CREATE = "TaskCreate"
    TOOL_TASK_GET = "TaskGet"
    TOOL_TASK_LIST = "TaskList"
    TOOL_TASK_UPDATE = "TaskUpdate"

    def __init__(self, verbose: bool = True):
        """Initialize Todo middleware."""
        self._tasks: dict[str, Task] = {}
        self._counter = 0
        self.verbose = verbose

        if self.verbose:
            print("[TodoMiddleware] Initialized")

    def _generate_id(self) -> str:
        """Generate sequential task ID."""
        self._counter += 1
        return str(self._counter)

    def _get_tool_schemas(self) -> list[dict]:
        """Get task tool schemas."""
        return [
            {
                "type": "function",
                "function": {
                    "name": self.TOOL_TASK_CREATE,
                    "description": """Create a new task to track work progress.

Use this when:
- Starting a complex multi-step task
- User provides multiple items to work on
- You want to show progress to the user

Tasks are created with status 'pending'.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "Subject": {
                                "type": "string",
                                "description": "Brief task title in imperative form (e.g., 'Fix authentication bug')",
                            },
                            "Description": {
                                "type": "string",
                                "description": "Detailed description of what needs to be done",
                            },
                            "ActiveForm": {
                                "type": "string",
                                "description": "Present continuous form for spinner display (e.g., 'Fixing authentication bug')",
                            },
                            "Metadata": {
                                "type": "object",
                                "description": "Optional metadata to attach to the task",
                            },
                        },
                        "required": ["Subject", "Description"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": self.TOOL_TASK_GET,
                    "description": "Get full details of a task including description and dependencies.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "TaskId": {
                                "type": "string",
                                "description": "The task ID to retrieve",
                            },
                        },
                        "required": ["TaskId"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": self.TOOL_TASK_LIST,
                    "description": """List all tasks with summary info.

Returns for each task:
- id: Task identifier
- subject: Brief description
- status: pending/in_progress/completed
- owner: Assigned agent (if any)
- blockedBy: IDs of blocking tasks""",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": self.TOOL_TASK_UPDATE,
                    "description": """Update a task's status, dependencies, or other fields.

Status flow: pending → in_progress → completed
Use status='deleted' to remove a task.

IMPORTANT:
- Set status to 'in_progress' BEFORE starting work
- Set status to 'completed' only when FULLY done
- Use addBlocks/addBlockedBy to set dependencies""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "TaskId": {
                                "type": "string",
                                "description": "The task ID to update",
                            },
                            "Status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed", "deleted"],
                                "description": "New status for the task",
                            },
                            "Subject": {
                                "type": "string",
                                "description": "New subject for the task",
                            },
                            "Description": {
                                "type": "string",
                                "description": "New description for the task",
                            },
                            "ActiveForm": {
                                "type": "string",
                                "description": "New activeForm for the task",
                            },
                            "Owner": {
                                "type": "string",
                                "description": "Assign task to an agent",
                            },
                            "AddBlocks": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Task IDs that this task blocks",
                            },
                            "AddBlockedBy": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Task IDs that block this task",
                            },
                            "Metadata": {
                                "type": "object",
                                "description": "Metadata keys to merge (set key to null to delete)",
                            },
                        },
                        "required": ["TaskId"],
                    },
                },
            },
        ]

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Inject task tool definitions."""
        tools = list(request.tools or [])
        tools.extend(self._get_tool_schemas())
        return handler(request.override(tools=tools))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Inject task tool definitions (async)."""
        tools = list(request.tools or [])
        tools.extend(self._get_tool_schemas())
        return await handler(request.override(tools=tools))

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any],
    ) -> Any:
        """Handle task tool calls."""
        tool_call = request.tool_call
        tool_name = tool_call.get("name")

        if tool_name not in (
            self.TOOL_TASK_CREATE,
            self.TOOL_TASK_GET,
            self.TOOL_TASK_LIST,
            self.TOOL_TASK_UPDATE,
        ):
            return handler(request)

        return self._handle_tool_call(tool_call)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[Any]],
    ) -> Any:
        """Handle task tool calls (async)."""
        tool_call = request.tool_call
        tool_name = tool_call.get("name")

        if tool_name not in (
            self.TOOL_TASK_CREATE,
            self.TOOL_TASK_GET,
            self.TOOL_TASK_LIST,
            self.TOOL_TASK_UPDATE,
        ):
            return await handler(request)

        return self._handle_tool_call(tool_call)

    def _handle_tool_call(self, tool_call: dict) -> ToolMessage:
        """Handle task tool call."""
        tool_name = tool_call.get("name")
        tool_id = tool_call.get("id", "")
        args = tool_call.get("args", {})

        if tool_name == self.TOOL_TASK_CREATE:
            result = self._handle_create(args)
        elif tool_name == self.TOOL_TASK_GET:
            result = self._handle_get(args)
        elif tool_name == self.TOOL_TASK_LIST:
            result = self._handle_list()
        elif tool_name == self.TOOL_TASK_UPDATE:
            result = self._handle_update(args)
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        content = json.dumps(result, ensure_ascii=False, indent=2)
        return ToolMessage(content=content, tool_call_id=tool_id)

    def _handle_create(self, args: dict) -> dict:
        """Handle TaskCreate."""
        task_id = self._generate_id()

        task = Task(
            id=task_id,
            subject=args.get("Subject", ""),
            description=args.get("Description", ""),
            active_form=args.get("ActiveForm"),
            metadata=args.get("Metadata", {}),
        )

        self._tasks[task_id] = task

        return {
            "id": task_id,
            "status": "created",
            "task": task.to_summary(),
        }

    def _handle_get(self, args: dict) -> dict:
        """Handle TaskGet."""
        task_id = args.get("TaskId", "")

        if task_id not in self._tasks:
            return {"error": f"Task not found: {task_id}"}

        task = self._tasks[task_id]
        return task.to_detail()

    def _handle_list(self) -> dict:
        """Handle TaskList."""
        tasks = []
        for task in self._tasks.values():
            summary = task.to_summary()
            # Add blocked status
            summary["isBlocked"] = task.is_blocked(self._tasks)
            tasks.append(summary)

        return {
            "tasks": tasks,
            "total": len(tasks),
            "pending": sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING),
            "in_progress": sum(1 for t in self._tasks.values() if t.status == TaskStatus.IN_PROGRESS),
            "completed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED),
        }

    def _handle_update(self, args: dict) -> dict:
        """Handle TaskUpdate."""
        task_id = args.get("TaskId", "")

        if task_id not in self._tasks:
            return {"error": f"Task not found: {task_id}"}

        task = self._tasks[task_id]

        # Handle deletion
        status = args.get("Status")
        if status == "deleted":
            # Remove from other tasks' blocks/blockedBy
            for other_task in self._tasks.values():
                if task_id in other_task.blocks:
                    other_task.blocks.remove(task_id)
                if task_id in other_task.blocked_by:
                    other_task.blocked_by.remove(task_id)
            del self._tasks[task_id]
            return {"status": "deleted", "id": task_id}

        # Update status
        if status:
            task.status = TaskStatus(status)

        # Update other fields
        if "Subject" in args:
            task.subject = args["Subject"]
        if "Description" in args:
            task.description = args["Description"]
        if "ActiveForm" in args:
            task.active_form = args["ActiveForm"]
        if "Owner" in args:
            task.owner = args["Owner"]

        # Add dependencies
        if "AddBlocks" in args:
            for blocked_id in args["AddBlocks"]:
                if blocked_id not in task.blocks:
                    task.blocks.append(blocked_id)
                # Also update the blocked task's blockedBy
                if blocked_id in self._tasks:
                    if task_id not in self._tasks[blocked_id].blocked_by:
                        self._tasks[blocked_id].blocked_by.append(task_id)

        if "AddBlockedBy" in args:
            for blocker_id in args["AddBlockedBy"]:
                if blocker_id not in task.blocked_by:
                    task.blocked_by.append(blocker_id)
                # Also update the blocker task's blocks
                if blocker_id in self._tasks:
                    if task_id not in self._tasks[blocker_id].blocks:
                        self._tasks[blocker_id].blocks.append(task_id)

        # Merge metadata
        if "Metadata" in args:
            for key, value in args["Metadata"].items():
                if value is None:
                    task.metadata.pop(key, None)
                else:
                    task.metadata[key] = value

        return {
            "status": "updated",
            "task": task.to_summary(),
        }

    def get_tasks(self) -> dict[str, Task]:
        """Get all tasks (for external access)."""
        return self._tasks.copy()

    def get_active_task(self) -> Task | None:
        """Get the currently in_progress task (for UI display)."""
        for task in self._tasks.values():
            if task.status == TaskStatus.IN_PROGRESS:
                return task
        return None
