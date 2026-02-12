"""SandboxCapability - Wrapper that hides new architecture from agents.

This module provides the capability object that agents interact with.
It wraps the new architecture (ChatSession → Runtime → Terminal → Lease)
while maintaining the same interface as before.
"""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

from sandbox.interfaces.executor import BaseExecutor
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

    def resolve_session_info(self, provider_name: str):
        """Resolve current session info without exposing internal session object."""
        from sandbox.provider import SessionInfo

        instance = self._session.lease.get_instance()
        provider = getattr(self._session.runtime, "provider", None)
        if not instance and provider is not None:
            instance = self._session.lease.ensure_active_instance(provider)
        return SessionInfo(
            session_id=instance.instance_id if instance else "local",
            provider=provider_name,
            status="running",
        )


class _CommandWrapper(BaseExecutor):
    """Wrapper that delegates to runtime's execute method."""

    runtime_owns_cwd = True

    def __init__(self, session: ChatSession):
        super().__init__(default_cwd=session.terminal.get_state().cwd)
        self._session = session

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
        return await self._session.runtime.start_command(wrapped, work_dir)

    async def get_status(self, command_id: str):
        """Get status for an async command."""
        return await self._session.runtime.get_command(command_id)

    async def wait_for(self, command_id: str, timeout: float | None = None):
        """Wait for async command completion."""
        return await self._session.runtime.wait_for_command(command_id, timeout=timeout)

    def store_completed_result(self, command_id: str, command_line: str, cwd: str, result):
        """Store completed result for command_status lookup."""
        self._session.runtime.store_completed_result(command_id, command_line, cwd, result)


class _FileSystemWrapper(FileSystemBackend):
    """Wrapper that delegates to provider via lease."""

    is_remote = True

    def __init__(self, session: ChatSession):
        self._session = session

    def _get_provider(self):
        """Get provider from session's lease."""
        provider = getattr(self._session.runtime, "provider", None)
        if provider is None:
            raise RuntimeError("FileSystem operations only supported for remote runtimes")
        return provider

    def _get_instance_id(self) -> str:
        """Get active instance ID."""
        # @@@lease-convergence - File operations can also wake paused instances; always converge through lease.
        provider = getattr(self._session.runtime, "provider", None)
        if provider is not None:
            instance = self._session.lease.ensure_active_instance(provider)
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
