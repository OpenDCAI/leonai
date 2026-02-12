"""Subagent runner for executing task agents."""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from model_params import normalize_model_kwargs

from .types import AgentConfig, TaskParams, TaskResult


# Placeholder tool to ensure agent graph has a "tools" node.
#
# langchain's create_agent creates ToolNode only when:
#   available_tools = middleware_tools + regular_tools is non-empty
# where middleware_tools = [t for m in middleware for t in getattr(m, "tools", [])]
#
# Most middleware inject tools via wrap_model_call (dict schema), not self.tools.
# Only CommandMiddleware has self.tools (BaseTool instances).
# When subagent doesn't include CommandMiddleware, we need this placeholder.
@tool
def _placeholder_tool() -> str:
    """Internal placeholder - ensures ToolNode is created for middleware tools."""
    return ""


class SubagentRunner:
    """Execute subagent tasks with isolated tool sets."""

    def __init__(
        self,
        agents: dict[str, AgentConfig],
        parent_model: str,
        workspace_root: Path,
        api_key: str,
        model_kwargs: dict[str, Any] | None = None,
    ):
        self.agents = agents
        self.parent_model = parent_model
        self.workspace_root = workspace_root
        self.api_key = api_key
        self.model_kwargs = model_kwargs or {}
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._task_results: dict[str, TaskResult] = {}

    def _build_subagent_middleware(self, config: AgentConfig, all_middleware: list[Any]) -> list[Any]:
        """Build middleware stack for subagent based on allowed tools."""
        from middleware.command import CommandMiddleware
        from middleware.filesystem import FileSystemMiddleware
        from middleware.search import SearchMiddleware
        from middleware.web import WebMiddleware

        # Tool name to middleware class mapping
        tool_middleware_map = {
            "read_file": FileSystemMiddleware,
            "write_file": FileSystemMiddleware,
            "edit_file": FileSystemMiddleware,
            "multi_edit": FileSystemMiddleware,
            "list_dir": FileSystemMiddleware,
            "grep_search": SearchMiddleware,
            "find_by_name": SearchMiddleware,
            "run_command": CommandMiddleware,
            "command_status": CommandMiddleware,
            "web_search": WebMiddleware,
            "read_url_content": WebMiddleware,
        }

        # Determine which middleware classes are needed
        needed_classes = set()
        for tool_name in config.tools:
            if tool_name in tool_middleware_map:
                needed_classes.add(tool_middleware_map[tool_name])

        # Filter middleware and configure enabled tools
        filtered_middleware = []
        for mw in all_middleware:
            mw_class = type(mw)

            if mw_class in needed_classes:
                # Clone middleware with filtered tools
                if mw_class == FileSystemMiddleware:
                    enabled = {
                        "read_file": "read_file" in config.tools,
                        "write_file": "write_file" in config.tools,
                        "edit_file": "edit_file" in config.tools,
                        "multi_edit": "multi_edit" in config.tools,
                        "list_dir": "list_dir" in config.tools,
                    }
                    new_mw = FileSystemMiddleware(
                        workspace_root=mw.workspace_root,
                        max_file_size=mw.max_file_size,
                        allowed_extensions=mw.allowed_extensions,
                        hooks=mw.hooks,
                        enabled_tools=enabled,
                        operation_recorder=getattr(mw, "operation_recorder", None),
                    )
                    filtered_middleware.append(new_mw)

                elif mw_class == SearchMiddleware:
                    enabled = {
                        "grep_search": "grep_search" in config.tools,
                        "find_by_name": "find_by_name" in config.tools,
                    }
                    new_mw = SearchMiddleware(
                        workspace_root=mw.workspace_root,
                        max_results=mw.max_results,
                        max_file_size=mw.max_file_size,
                        prefer_system_tools=mw.prefer_system_tools,
                        enabled_tools=enabled,
                    )
                    filtered_middleware.append(new_mw)

                elif mw_class == CommandMiddleware:
                    enabled = {
                        "run_command": "run_command" in config.tools,
                        "command_status": "command_status" in config.tools,
                    }
                    new_mw = CommandMiddleware(
                        workspace_root=mw.workspace_root,
                        default_timeout=mw.default_timeout,
                        hooks=mw.hooks,
                        enabled_tools=enabled,
                    )
                    filtered_middleware.append(new_mw)

                elif mw_class == WebMiddleware:
                    enabled = {
                        "web_search": "web_search" in config.tools,
                        "read_url_content": "read_url_content" in config.tools,
                        "view_web_content": False,
                    }
                    new_mw = WebMiddleware(
                        tavily_api_key=getattr(mw, "_tavily_api_key", None),
                        exa_api_key=getattr(mw, "_exa_api_key", None),
                        firecrawl_api_key=getattr(mw, "_firecrawl_api_key", None),
                        jina_api_key=getattr(mw, "_jina_api_key", None),
                        max_search_results=mw.max_search_results,
                        timeout=mw.timeout,
                        enabled_tools=enabled,
                    )
                    filtered_middleware.append(new_mw)

        return filtered_middleware

    async def run(
        self,
        params: TaskParams,
        all_middleware: list[Any],
        checkpointer: Any,
    ) -> TaskResult:
        """Run a subagent task."""
        task_id = str(uuid.uuid4())[:8]
        subagent_type = params["SubagentType"]

        config = self.agents.get(subagent_type)
        if not config:
            available = ", ".join(sorted(self.agents.keys()))
            return TaskResult(
                task_id=task_id,
                status="error",
                error=f"Unknown agent: {subagent_type}. Available: {available}",
            )

        # Determine model
        model_name = params.get("Model") or config.model or self.parent_model

        # Build model (unified path via init_chat_model)
        model_kwargs = normalize_model_kwargs(model_name, self.model_kwargs)
        model = init_chat_model(model_name, api_key=self.api_key, **model_kwargs)

        # Build filtered middleware
        middleware = self._build_subagent_middleware(config, all_middleware)

        # Build system prompt
        system_prompt = self._build_system_prompt(config)

        # Create subagent with unique thread_id
        subagent_thread_id = f"subagent_{task_id}"
        max_turns = params.get("MaxTurns") or config.max_turns

        # Check if any middleware has self.tools (BaseTool instances).
        # Only need placeholder if no middleware has tools.
        middleware_has_tools = any(getattr(m, "tools", None) for m in middleware)
        tools = [] if middleware_has_tools else [_placeholder_tool]

        agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
            middleware=middleware,
            checkpointer=checkpointer,
        )

        # Execute
        prompt = params["Prompt"]
        description = params.get("Description", "")

        if params.get("RunInBackground"):
            # Background execution
            task = asyncio.create_task(self._execute_agent(agent, prompt, subagent_thread_id, max_turns, task_id))
            self._active_tasks[task_id] = task
            return TaskResult(
                task_id=task_id,
                status="running",
                result=f"Task started in background. Use TaskOutput with TaskId='{task_id}' to get results.",
            )
        else:
            # Synchronous execution
            return await self._execute_agent(agent, prompt, subagent_thread_id, max_turns, task_id)

    async def run_streaming(
        self,
        params: TaskParams,
        all_middleware: list[Any],
        checkpointer: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Run a subagent task with streaming output."""
        task_id = str(uuid.uuid4())[:8]
        subagent_type = params["SubagentType"]

        config = self.agents.get(subagent_type)
        if not config:
            available = ", ".join(sorted(self.agents.keys()))
            yield {
                "event": "task_error",
                "data": json.dumps(
                    {
                        "task_id": task_id,
                        "error": f"Unknown agent: {subagent_type}. Available: {available}",
                    }
                ),
            }
            return

        # Emit task start event
        yield {
            "event": "task_start",
            "data": json.dumps(
                {
                    "task_id": task_id,
                    "thread_id": f"subagent_{task_id}",
                    "subagent_type": subagent_type,
                    "description": params.get("Description", ""),
                }
            ),
        }

        # Determine model
        model_name = params.get("Model") or config.model or self.parent_model

        # Build model
        model_kwargs = normalize_model_kwargs(model_name, self.model_kwargs)
        model = init_chat_model(model_name, api_key=self.api_key, **model_kwargs)

        # Build filtered middleware
        middleware = self._build_subagent_middleware(config, all_middleware)

        # Build system prompt
        system_prompt = self._build_system_prompt(config)

        # Create subagent with unique thread_id
        subagent_thread_id = f"subagent_{task_id}"
        max_turns = params.get("MaxTurns") or config.max_turns

        # Check if any middleware has self.tools
        middleware_has_tools = any(getattr(m, "tools", None) for m in middleware)
        tools = [] if middleware_has_tools else [_placeholder_tool]

        agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
            middleware=middleware,
            checkpointer=checkpointer,
        )

        # Execute with streaming
        prompt = params["Prompt"]
        turns_used = 0
        emitted_tool_call_ids: set[str] = set()

        try:
            async for chunk in agent.astream(
                {"messages": [{"role": "user", "content": prompt}]},
                config={"configurable": {"thread_id": subagent_thread_id}},
                stream_mode=["messages", "updates"],
            ):
                if not chunk or not isinstance(chunk, tuple) or len(chunk) != 2:
                    continue

                mode, data = chunk

                # Token-level streaming from "messages" mode
                if mode == "messages":
                    msg_chunk, metadata = data
                    msg_class = msg_chunk.__class__.__name__
                    if msg_class == "AIMessageChunk":
                        content = self._extract_text_content(getattr(msg_chunk, "content", ""))
                        if content:
                            yield {
                                "event": "task_text",
                                "data": json.dumps({"task_id": task_id, "content": content}),
                            }

                # Node-level updates from "updates" mode
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
                                for tc in getattr(msg, "tool_calls", []):
                                    tc_id = tc.get("id")
                                    if tc_id and tc_id in emitted_tool_call_ids:
                                        continue
                                    if tc_id:
                                        emitted_tool_call_ids.add(tc_id)
                                    yield {
                                        "event": "task_tool_call",
                                        "data": json.dumps(
                                            {
                                                "task_id": task_id,
                                                "id": tc.get("id"),
                                                "name": tc.get("name", "unknown"),
                                                "args": tc.get("args", {}),
                                            }
                                        ),
                                    }
                            elif msg_class == "ToolMessage":
                                yield {
                                    "event": "task_tool_result",
                                    "data": json.dumps(
                                        {
                                            "task_id": task_id,
                                            "tool_call_id": getattr(msg, "tool_call_id", None),
                                            "name": getattr(msg, "name", "unknown"),
                                            "content": str(getattr(msg, "content", "")),
                                        }
                                    ),
                                }

            # Task completed
            yield {
                "event": "task_done",
                "data": json.dumps(
                    {
                        "task_id": task_id,
                        "thread_id": subagent_thread_id,
                        "status": "completed",
                    }
                ),
            }

        except Exception as e:
            yield {
                "event": "task_error",
                "data": json.dumps({"task_id": task_id, "error": str(e)}),
            }

    def _extract_text_content(self, raw_content: Any) -> str:
        """Extract text content from message content."""
        if isinstance(raw_content, str):
            return raw_content
        if isinstance(raw_content, list):
            parts: list[str] = []
            for block in raw_content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
            return "".join(parts)
        return str(raw_content)

    async def _execute_agent(
        self,
        agent: Any,
        prompt: str,
        thread_id: str,
        max_turns: int,
        task_id: str,
    ) -> TaskResult:
        """Execute agent and return result."""
        turns_used = 0
        try:
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": prompt}]},
                config={"configurable": {"thread_id": thread_id}},
            )

            # Extract final response
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                content = last_message.content if hasattr(last_message, "content") else str(last_message)
            else:
                content = "No response generated."

            turns_used = len([m for m in messages if hasattr(m, "role")])

            task_result = TaskResult(
                task_id=task_id,
                thread_id=thread_id,
                status="completed",
                result=content,
                turns_used=turns_used,
            )

        except Exception as e:
            task_result = TaskResult(
                task_id=task_id,
                thread_id=thread_id,
                status="error",
                error=str(e),
                turns_used=turns_used,
            )

        self._task_results[task_id] = task_result
        return task_result

    def _build_system_prompt(self, config: AgentConfig) -> str:
        """Build system prompt for subagent."""
        prompt = f"""You are a specialized sub-agent: {config.name}

{config.system_prompt}

**Context:**
- Workspace: `{self.workspace_root}`
- Available tools: {", ".join(config.tools)}

**Important Rules:**
1. All file paths must be absolute paths.
2. File operations are restricted to the workspace.
3. Complete your task efficiently and report your findings.
"""
        return prompt

    def get_task_status(self, task_id: str) -> TaskResult:
        """Get status of a background task."""
        # Check if completed
        if task_id in self._task_results:
            return self._task_results[task_id]

        # Check if still running
        if task_id in self._active_tasks:
            task = self._active_tasks[task_id]
            if task.done():
                try:
                    return task.result()
                except Exception as e:
                    return TaskResult(
                        task_id=task_id,
                        status="error",
                        error=str(e),
                    )
            else:
                return TaskResult(
                    task_id=task_id,
                    status="running",
                    result="Task is still running...",
                )

        return TaskResult(
            task_id=task_id,
            status="error",
            error=f"Unknown task_id: {task_id}",
        )
