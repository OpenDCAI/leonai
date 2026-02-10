"""SandboxCapability - Wrapper that hides new architecture from agents.

This module provides the capability object that agents interact with.
It wraps the new architecture (ChatSession → Runtime → Terminal → Lease)
while maintaining the same interface as before.
"""

from __future__ import annotations

import asyncio
import shlex
import uuid
from typing import TYPE_CHECKING

from sandbox.interfaces.executor import AsyncCommand, BaseExecutor, ExecuteResult
from sandbox.interfaces.filesystem import FileSystemBackend

if TYPE_CHECKING:
    from sandbox.chat_session import ChatSession


class SandboxCapability:
    """Agent-facing capability object.

    Wraps ChatSession and provides access to command execution and filesystem.
    Agents see the same interface as before - all complexity is hidden.

    Usage:
        sandbox = sandbox_manager.get_sandbox(thread_id)
        result = await sandbox.command.execute("ls")
        content = sandbox.fs.read_file("/path/to/file")
    """

    def __init__(self, session: ChatSession):
        self._session = session
        self._command_wrapper = _CommandWrapper(session)
        self._fs_wrapper = _FileSystemWrapper(session)

    @property
    def command(self) -> BaseExecutor:
        """Get command executor."""
        return self._command_wrapper

    @property
    def fs(self) -> FileSystemBackend:
        """Get filesystem backend."""
        return self._fs_wrapper

    def touch(self) -> None:
        """Update session activity timestamp."""
        self._session.touch()


class _CommandWrapper(BaseExecutor):
    """Wrapper that delegates to runtime's execute method."""

    runtime_owns_cwd = True

    def __init__(self, session: ChatSession):
        super().__init__(default_cwd=session.terminal.get_state().cwd)
        self._session = session
        self._commands: dict[str, AsyncCommand] = {}
        self._tasks: dict[str, asyncio.Task[ExecuteResult]] = {}

    def _wrap_command(self, command: str, cwd: str | None, env: dict[str, str] | None) -> tuple[str, str]:
        wrapped = command
        if env:
            exports = "\n".join(f"export {k}={shlex.quote(v)}" for k, v in env.items())
            wrapped = f"{exports}\n{wrapped}"
        work_dir = cwd or self.default_cwd or self._session.terminal.get_state().cwd
        if work_dir:
            wrapped = f"cd {shlex.quote(work_dir)}\n{wrapped}"
        return wrapped, work_dir

    async def execute(
        self, command: str, cwd: str | None = None, timeout: float | None = None, env: dict[str, str] | None = None
    ):
        """Execute command via runtime."""
        self._session.touch()
        # @@@command-context - CommandMiddleware passes Cwd/env; preserve that context for remote runtimes.
        wrapped, _ = self._wrap_command(command, cwd, env)
        return await self._session.runtime.execute(wrapped, timeout)

    async def execute_async(self, command: str, cwd: str | None = None, env: dict[str, str] | None = None):
        """Execute command asynchronously via runtime and return command handle."""
        self._session.touch()
        wrapped, work_dir = self._wrap_command(command, cwd, env)
        command_id = f"cmd_{uuid.uuid4().hex[:12]}"
        async_cmd = AsyncCommand(
            command_id=command_id,
            command_line=command,
            cwd=work_dir,
        )
        self._commands[command_id] = async_cmd

        async def _run() -> ExecuteResult:
            try:
                result = await self._session.runtime.execute(wrapped, timeout=None)
            except Exception as exc:
                result = ExecuteResult(exit_code=1, stdout="", stderr=f"Error: {exc}")
            async_cmd.stdout_buffer = [result.stdout]
            async_cmd.stderr_buffer = [result.stderr]
            async_cmd.exit_code = result.exit_code
            async_cmd.done = True
            return result

        self._tasks[command_id] = asyncio.create_task(_run())
        return async_cmd

    async def get_status(self, command_id: str):
        """Get status for an async command."""
        return self._commands.get(command_id)

    async def wait_for(self, command_id: str, timeout: float | None = None):
        """Wait for async command completion."""
        async_cmd = self._commands.get(command_id)
        task = self._tasks.get(command_id)
        if async_cmd is None:
            return None
        if task is not None and not task.done():
            try:
                if timeout is None:
                    await task
                else:
                    await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
            except TimeoutError:
                return ExecuteResult(
                    exit_code=-1,
                    stdout="".join(async_cmd.stdout_buffer),
                    stderr="".join(async_cmd.stderr_buffer),
                    timed_out=True,
                    command_id=command_id,
                )
        return ExecuteResult(
            exit_code=async_cmd.exit_code or 0,
            stdout="".join(async_cmd.stdout_buffer),
            stderr="".join(async_cmd.stderr_buffer),
            timed_out=False,
            command_id=command_id,
        )

    def store_completed_result(self, command_id: str, command_line: str, cwd: str, result):
        """Store completed result for command_status lookup."""
        self._commands[command_id] = AsyncCommand(
            command_id=command_id,
            command_line=command_line,
            cwd=cwd,
            stdout_buffer=[result.stdout],
            stderr_buffer=[result.stderr],
            exit_code=result.exit_code,
            done=True,
        )


class _FileSystemWrapper(FileSystemBackend):
    """Wrapper that delegates to provider via lease."""

    is_remote = True

    def __init__(self, session: ChatSession):
        self._session = session

    def _get_provider(self):
        """Get provider from session's lease."""
        # Provider is passed to runtime, we need to access it
        from sandbox.runtime import RemoteWrappedRuntime

        if isinstance(self._session.runtime, RemoteWrappedRuntime):
            return self._session.runtime.provider
        raise RuntimeError("FileSystem operations only supported for remote runtimes")

    def _get_instance_id(self) -> str:
        """Get active instance ID."""
        # @@@lease-convergence - File operations can also wake paused instances; always converge through lease.
        from sandbox.runtime import RemoteWrappedRuntime

        if isinstance(self._session.runtime, RemoteWrappedRuntime):
            instance = self._session.lease.ensure_active_instance(self._session.runtime.provider)
        else:
            instance = self._session.lease.get_instance()
            if not instance:
                raise RuntimeError("No active instance")
        return instance.instance_id

    def read_file(self, path: str):
        """Read file via provider."""
        from sandbox.interfaces.filesystem import FileReadResult

        self._session.touch()
        provider = self._get_provider()
        instance_id = self._get_instance_id()

        content = provider.read_file(instance_id, path)
        return FileReadResult(content=content, size=len(content))

    def write_file(self, path: str, content: str):
        """Write file via provider."""
        from sandbox.interfaces.filesystem import FileWriteResult

        self._session.touch()
        provider = self._get_provider()
        instance_id = self._get_instance_id()

        try:
            provider.write_file(instance_id, path, content)
            return FileWriteResult(success=True)
        except Exception as e:
            return FileWriteResult(success=False, error=str(e))

    def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        provider = self._get_provider()
        instance_id = self._get_instance_id()

        try:
            provider.read_file(instance_id, path)
            return True
        except Exception:
            return False

    def file_mtime(self, path: str) -> float | None:
        """Not available for remote sandbox."""
        return None

    def file_size(self, path: str) -> int | None:
        """Not available for remote sandbox."""
        return None

    def is_dir(self, path: str) -> bool:
        """Check if path is directory."""
        provider = self._get_provider()
        instance_id = self._get_instance_id()

        try:
            provider.list_dir(instance_id, path)
            return True
        except Exception:
            return False

    def list_dir(self, path: str):
        """List directory contents."""
        from sandbox.interfaces.filesystem import DirEntry, DirListResult

        provider = self._get_provider()
        instance_id = self._get_instance_id()

        try:
            items = provider.list_dir(instance_id, path)
            entries = []
            for item in items:
                name = item.get("name", "?")
                item_type = item.get("type", "file")
                size = item.get("size", 0)
                entries.append(
                    DirEntry(
                        name=name,
                        is_dir=(item_type == "directory"),
                        size=size,
                    )
                )
            return DirListResult(entries=entries)
        except Exception as e:
            return DirListResult(error=str(e))
