"""Command Middleware - shell command execution.

Provides run_command and command_status tools.
"""

from __future__ import annotations

import asyncio
import json
import logging

from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from langchain.agents.middleware import AgentMiddleware, AgentState
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain.tools import ToolRuntime, tool
from langgraph.runtime import Runtime

from sandbox.shell_output import normalize_pty_result

from .base import AsyncCommand, BaseExecutor
from .dispatcher import get_executor, get_shell_info

RUN_COMMAND_TOOL_NAME = "run_command"
COMMAND_STATUS_TOOL_NAME = "command_status"

DEFAULT_TIMEOUT = 120.0
DEFAULT_WAIT_MS_BEFORE_ASYNC = 500


class CommandState(AgentState):
    """State for command middleware."""

    pass


class CommandMiddleware(AgentMiddleware[CommandState]):
    """
    Command execution middleware.

    Features:
    - run_command tool with CommandLine, Cwd, Blocking, Timeout params
    - command_status tool for async command queries
    - Extensible hook system for security checks
    - Auto-detects shell based on OS (zsh/bash/powershell)
    """

    state_schema = CommandState

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        default_timeout: float = DEFAULT_TIMEOUT,
        hooks: list[Any] | None = None,
        env: dict[str, str] | None = None,
        enabled_tools: dict[str, bool] | None = None,
        executor: BaseExecutor | None = None,
        verbose: bool = True,
    ) -> None:
        """
        Initialize CommandMiddleware.

        Args:
            workspace_root: Default working directory for commands
            default_timeout: Default timeout in seconds for blocking commands
            hooks: List of hook instances for command validation
            env: Additional environment variables
            executor: External executor (default: auto-detect OS shell)
            verbose: Whether to output detailed logs
        """
        AgentMiddleware.__init__(self)
        self._agent: Any = None

        # @@@ Don't resolve workspace_root for sandbox — macOS firmlinks break it
        if executor is not None and executor.is_remote:
            self.workspace_root = Path(workspace_root)
        else:
            self.workspace_root = Path(workspace_root).resolve()
        self.default_timeout = default_timeout
        self.hooks = hooks or []
        self.env = env
        self.enabled_tools = enabled_tools or {"run_command": True, "command_status": True}
        self.verbose = verbose

        # Use provided executor or auto-detect
        if executor is not None:
            self._executor = executor
        else:
            self._executor = get_executor(default_cwd=str(self.workspace_root))

        if self.verbose:
            executor_name = type(self._executor).__name__
            if hasattr(self._executor, "shell_name"):
                shell_label = self._executor.shell_name
            else:
                shell_info = get_shell_info()
                shell_label = shell_info["shell_name"]
            print(f"[Command] Initialized: {shell_label} (executor: {executor_name})")
            print(f"[Command] Workspace: {self.workspace_root}")
            print(f"[Command] Loaded {len(self.hooks)} hooks")

        @tool(RUN_COMMAND_TOOL_NAME)
        async def run_command_tool(
            *,
            runtime: ToolRuntime[CommandState],
            CommandLine: str,
            Cwd: str | None = None,
            Blocking: bool = True,
            Timeout: int | None = None,
        ) -> str:
            """Execute shell command. OS auto-detects shell (mac→zsh, linux→bash, win→powershell).

            Args:
                CommandLine: Command to execute
                Cwd: Working directory (optional, defaults to workspace root)
                Blocking: Wait for completion (default: true). If false, returns CommandId for status queries.
                Timeout: Timeout in seconds (optional, default: 120)
            """
            return await self._execute_command(
                command_line=CommandLine,
                cwd=Cwd,
                blocking=Blocking,
                timeout=Timeout,
            )

        @tool(COMMAND_STATUS_TOOL_NAME)
        async def command_status_tool(
            *,
            runtime: ToolRuntime[CommandState],
            CommandId: str,
            WaitDurationSeconds: int = 0,
        ) -> str:
            """Check status of a non-blocking command.

            Args:
                CommandId: ID returned by run_command with Blocking=false
                WaitDurationSeconds: Seconds to wait for completion (0 = immediate check)
            """
            return await self._get_command_status(
                command_id=CommandId,
                wait_seconds=WaitDurationSeconds,
            )

        self._run_command_tool = run_command_tool
        self._command_status_tool = command_status_tool
        self.tools = [self._run_command_tool, self._command_status_tool]

    def _check_hooks(self, command: str) -> tuple[bool, str]:
        """Run command through all hooks. Returns (allowed, error_message)."""
        context = {"workspace_root": str(self.workspace_root)}

        for hook in self.hooks:
            if not hook.enabled:
                continue

            result = hook.check_command(command, context)

            if not result.allow:
                return False, result.error_message

            if not result.continue_chain:
                break

        return True, ""

    async def _execute_command(
        self,
        command_line: str,
        cwd: str | None,
        blocking: bool,
        timeout: int | None,
    ) -> str:
        """Execute command with hook validation."""
        allowed, error_msg = self._check_hooks(command_line)
        if not allowed:
            return error_msg

        # @@@runtime-owned-cwd - Stateful runtimes (remote/local chat session shells) own cwd continuity.
        work_dir = cwd if self._executor.runtime_owns_cwd else (cwd or str(self.workspace_root))

        if blocking:
            return await self._execute_blocking(command_line, work_dir, timeout)
        else:
            return await self._execute_async(command_line, work_dir, timeout)

    async def _execute_blocking(self, command_line: str, work_dir: str | None, timeout: int | None) -> str:
        """Execute blocking command. SpillBuffer middleware handles oversized output."""
        timeout_secs = float(timeout) if timeout else self.default_timeout
        result = await self._executor.execute(
            command=command_line,
            cwd=work_dir,
            timeout=timeout_secs,
            env=self.env,
        )
        return result.to_tool_result()

    def set_agent(self, agent: Any) -> None:
        """Set parent agent for runtime access."""
        self._agent = agent

    async def _execute_async(self, command_line: str, work_dir: str | None, timeout: int | None) -> str:
        """Execute async command."""
        async_cmd = await self._executor.execute_async(
            command=command_line,
            cwd=work_dir,
            env=self.env,
        )

        if timeout and timeout > 0:
            await asyncio.sleep(min(timeout / 1000.0, 1.0))

        status = await self._executor.get_status(async_cmd.command_id)
        if status and status.done:
            result = await self._executor.wait_for(async_cmd.command_id)
            if result:
                return result.to_tool_result()

        # Start background monitoring for progress events
        runtime = getattr(self._agent, "runtime", None) if self._agent else None
        if runtime:
            asyncio.create_task(
                self._monitor_async_command(async_cmd.command_id, command_line, runtime)
            )

        return (
            f"Command started in background.\n"
            f"CommandId: {async_cmd.command_id}\n"
            f"Use command_status tool to check progress."
        )

    async def _monitor_async_command(
        self, command_id: str, command_line: str, runtime: Any
    ) -> None:
        """Poll async command and emit progress events every 2s."""
        while True:
            await asyncio.sleep(2.0)
            try:
                status = await self._executor.get_status(command_id)
            except Exception:
                logger.debug("Failed to get status for command %s", command_id)
                break
            if status is None:
                break

            output = self._merge_running_output(status)

            runtime.emit_activity_event({
                "event": "command_progress",
                "data": json.dumps({
                    "command_id": command_id,
                    "command_line": command_line,
                    "done": status.done,
                    "exit_code": status.exit_code,
                    "output_preview": output[-500:] if output else "",
                }, ensure_ascii=False),
            })

            if status.done:
                break

    def _clean_running_output(self, output: str, command_line: str) -> str:
        return normalize_pty_result(output, command_line)

    @staticmethod
    def _merge_running_output(status: AsyncCommand) -> str:
        stdout = "".join(status.stdout_buffer)
        stderr = "".join(status.stderr_buffer)
        if stdout and stderr:
            return f"{stdout}\n{stderr}".strip()
        return (stdout or stderr).strip()

    async def _get_command_status(
        self,
        command_id: str,
        wait_seconds: int,
    ) -> str:
        """Get status of async command."""
        if wait_seconds > 0:
            result = await self._executor.wait_for(command_id, timeout=float(min(wait_seconds, 60)))
            if result:
                # @@@status-timeout-semantics - wait timeout means command is still running, not done.
                if result.timed_out:
                    status = await self._executor.get_status(command_id)
                    if status is None:
                        return f"Error: Command {command_id} not found"
                    combined_output = self._merge_running_output(status)
                    cleaned_output = self._clean_running_output(combined_output, status.command_line)
                    return f"Status: running\nCommand: {status.command_line}\nOutput so far:\n{cleaned_output}"
                output = result.to_tool_result()
                return f"Status: done\nExit code: {result.exit_code}\n{output}"

        status = await self._executor.get_status(command_id)
        if status is None:
            return f"Error: Command {command_id} not found"

        if status.done:
            result = await self._executor.wait_for(command_id)
            if result:
                output = result.to_tool_result()
                return f"Status: done\nExit code: {result.exit_code}\n{output}"

        combined_output = self._merge_running_output(status)
        cleaned_output = self._clean_running_output(combined_output, status.command_line)
        return f"Status: running\nCommand: {status.command_line}\nOutput so far:\n{cleaned_output}"

    def before_agent(self, state: CommandState, runtime: Runtime) -> dict[str, Any] | None:
        return None

    async def abefore_agent(self, state: CommandState, runtime: Runtime) -> dict[str, Any] | None:
        return None

    def after_agent(self, state: CommandState, runtime: Runtime) -> None:
        pass

    async def aafter_agent(self, state: CommandState, runtime: Runtime) -> None:
        pass

    def wrap_model_call(self, request: ModelRequest, handler) -> ModelResponse:
        return handler(request)

    async def awrap_model_call(self, request: ModelRequest, handler) -> ModelResponse:
        return await handler(request)

    def wrap_tool_call(self, request, handler):
        return handler(request)

    async def awrap_tool_call(self, request, handler):
        return await handler(request)


__all__ = ["CommandMiddleware"]
