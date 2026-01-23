"""Shell Middleware with session persistence via Runtime.context."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain.agents.middleware import AgentMiddleware, AgentState
from langchain.agents.middleware.shell_tool import ShellToolMiddleware
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain.tools import tool, ToolRuntime
from langgraph.runtime import Runtime
from typing_extensions import NotRequired

from .hooks import load_hooks

BASH_TOOL_TYPE = "bash_20250124"
BASH_TOOL_NAME = "bash"


class ShellState(AgentState):
    shell_session_id: NotRequired[str]


@dataclass
class ShellContext:
    session_pool: dict[str, Any]


class ShellMiddleware(AgentMiddleware[ShellState]):
    """Shell middleware with persistent bash sessions."""

    state_schema = ShellState
    context_schema = ShellContext

    def __init__(
        self,
        workspace_root: str | None = None,
        *,
        startup_commands: tuple[str, ...] | list[str] | str | None = None,
        shutdown_commands: tuple[str, ...] | list[str] | str | None = None,
        allow_system_python: bool = True,
        env: dict[str, Any] | None = None,
        hooks_dir: str | Path | None = None,
        hook_config: dict[str, Any] | None = None,
    ) -> None:
        if workspace_root is None:
            raise ValueError("workspace_root required")

        AgentMiddleware.__init__(self)
        
        self.workspace_root = Path(workspace_root).resolve()
        
        if allow_system_python and env is None:
            env = {"PATH": os.environ.get("PATH", "")}

        if startup_commands is None:
            startup_commands = [f"echo 'Shell: {self.workspace_root}'"]
            if allow_system_python:
                startup_commands.append("which python3 && python3 --version || echo 'No Python'")

        self._shell_tool = ShellToolMiddleware(
            workspace_root=str(self.workspace_root),
            startup_commands=startup_commands,
            shutdown_commands=shutdown_commands,
            tool_name=BASH_TOOL_NAME,
            shell_command=("/bin/bash",),
            env=env,
        )
        
        @tool(BASH_TOOL_NAME)
        def bash_tool(
            *,
            runtime: ToolRuntime[ShellContext, ShellState],
            command: str | None = None,
            restart: bool = False,
        ) -> str:
            """Execute bash commands in a persistent shell session."""
            session_pool = runtime.context.session_pool
            session_id = runtime.state.get("shell_session_id")
            
            if not session_id:
                return "Error: No shell session initialized"
            if session_id not in session_pool:
                return f"Error: Session {session_id} not found in pool"
            
            return self._shell_tool._run_shell_tool(
                session_pool[session_id],
                {"command": command, "restart": restart},
                tool_call_id=runtime.tool_call_id,
            )
        
        self._bash_tool = bash_tool
        
        self.hooks = load_hooks(
            hooks_dir=hooks_dir,
            workspace_root=self.workspace_root,
            **(hook_config or {}),
        )

        self.tools = [self._bash_tool]
        print(f"[Shell] Loaded {len(self.hooks)} hooks")

    def _get_or_create_session(self, session_pool: dict[str, Any], session_id: str) -> Any:
        if session_id not in session_pool:
            resources = self._shell_tool._create_resources()
            resources.finalizer.detach()
            session_pool[session_id] = resources
            print(f"[Shell] Created session: {session_id}")
        return session_pool[session_id]


    def before_agent(self, state: ShellState, runtime: Runtime[ShellContext]) -> dict[str, Any] | None:
        session_pool = runtime.context.session_pool
        session_id = state.get("shell_session_id") or f"shell_{uuid.uuid4().hex[:8]}"
        session_resources = self._get_or_create_session(session_pool, session_id)
        
        return {
            "shell_session_id": session_id,
            "shell_session_resources": session_resources,
        }

    async def abefore_agent(self, state: ShellState, runtime: Runtime[ShellContext]) -> dict[str, Any] | None:
        return self.before_agent(state, runtime)

    def after_agent(self, state: ShellState, runtime: Runtime[ShellContext]) -> None:
        pass

    async def aafter_agent(self, state: ShellState, runtime: Runtime[ShellContext]) -> None:
        pass

    def wrap_model_call(self, request: ModelRequest, handler) -> ModelResponse:
        tools = [t for t in request.tools if getattr(t, "name", None) != BASH_TOOL_NAME]
        tools.append({"type": BASH_TOOL_TYPE, "name": BASH_TOOL_NAME})
        return handler(request.override(tools=tools))

    async def awrap_model_call(self, request: ModelRequest, handler) -> ModelResponse:
        tools = [t for t in request.tools if getattr(t, "name", None) != BASH_TOOL_NAME]
        tools.append({"type": BASH_TOOL_TYPE, "name": BASH_TOOL_NAME})
        return await handler(request.override(tools=tools))


__all__ = ["ShellMiddleware"]
