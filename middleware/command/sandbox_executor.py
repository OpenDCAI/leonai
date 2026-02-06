"""Sandbox command executor.

Delegates command execution to SandboxProvider.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from middleware.command.base import AsyncCommand, BaseExecutor, ExecuteResult

if TYPE_CHECKING:
    from sandbox.manager import SandboxManager


class SandboxExecutor(BaseExecutor):
    """Executor that runs commands in a sandbox via SandboxProvider.

    Args:
        manager: SandboxManager for provider access
        get_session_id: Callable that returns the current session ID
    """

    shell_name = "sandbox"
    shell_command = ()
    _is_sandbox = True  # marker for middleware to skip local-only logic

    # Store completed results for command_status retrieval
    _completed: dict[str, AsyncCommand] = {}

    def __init__(
        self,
        manager: SandboxManager,
        get_session_id: Callable[[], str],
        default_cwd: str | None = None,
    ) -> None:
        super().__init__(default_cwd=default_cwd)
        self._manager = manager
        self._get_session_id = get_session_id
        self._completed: dict[str, AsyncCommand] = {}

    @property
    def _provider(self):
        return self._manager.provider

    async def execute(
        self,
        command: str,
        cwd: str | None = None,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> ExecuteResult:
        """Execute command in sandbox synchronously."""
        session_id = self._get_session_id()

        # Convert timeout: seconds → milliseconds, cap at 50000ms
        timeout_ms = 30000
        if timeout is not None:
            timeout_ms = min(int(timeout * 1000), 50000)

        # Prepend cd if cwd specified
        actual_cmd = command
        if cwd:
            actual_cmd = f"cd {cwd} && {command}"

        import asyncio
        result = await asyncio.to_thread(
            self._provider.execute,
            session_id,
            actual_cmd,
            timeout_ms=timeout_ms,
        )

        return ExecuteResult(
            exit_code=result.exit_code,
            stdout=result.output or "",
            stderr=result.error or "",
        )

    async def execute_async(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> AsyncCommand:
        """Sandbox doesn't support true async — execute synchronously and mark done."""
        import uuid

        cmd_id = f"sbx_{uuid.uuid4().hex[:12]}"
        result = await self.execute(command, cwd=cwd, env=env)

        async_cmd = AsyncCommand(
            command_id=cmd_id,
            command_line=command,
            cwd=cwd or self.default_cwd or "",
            stdout_buffer=[result.stdout],
            stderr_buffer=[result.stderr] if result.stderr else [],
            exit_code=result.exit_code,
            done=True,
        )
        self._completed[cmd_id] = async_cmd
        return async_cmd

    async def get_status(self, command_id: str) -> AsyncCommand | None:
        return self._completed.get(command_id)

    async def wait_for(
        self,
        command_id: str,
        timeout: float | None = None,
    ) -> ExecuteResult | None:
        cmd = self._completed.get(command_id)
        if cmd is None:
            return None
        return ExecuteResult(
            exit_code=cmd.exit_code or 0,
            stdout="".join(cmd.stdout_buffer),
            stderr="".join(cmd.stderr_buffer),
        )

    def store_completed_result(
        self,
        command_id: str,
        command_line: str,
        cwd: str,
        result: ExecuteResult,
    ) -> None:
        self._completed[command_id] = AsyncCommand(
            command_id=command_id,
            command_line=command_line,
            cwd=cwd,
            stdout_buffer=[result.stdout],
            stderr_buffer=[result.stderr] if result.stderr else [],
            exit_code=result.exit_code,
            done=True,
        )
