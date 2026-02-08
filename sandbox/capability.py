"""SandboxCapability - Wrapper that hides new architecture from agents.

This module provides the capability object that agents interact with.
It wraps the new architecture (ChatSession → Runtime → Terminal → Lease)
while maintaining the same interface as before.
"""

from __future__ import annotations

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


class _CommandWrapper(BaseExecutor):
    """Wrapper that delegates to runtime's execute method."""

    def __init__(self, session: ChatSession):
        super().__init__(default_cwd=session.terminal.get_state().cwd)
        self._session = session

    async def execute(self, command: str, cwd: str | None = None, timeout: float | None = None, env: dict[str, str] | None = None):
        """Execute command via runtime."""
        self._session.touch()
        return await self._session.runtime.execute(command, timeout)

    async def execute_async(self, command: str, cwd: str | None = None, env: dict[str, str] | None = None):
        """Not implemented for capability wrapper."""
        raise NotImplementedError("execute_async not supported in capability wrapper")

    async def get_status(self, command_id: str):
        """Not implemented for capability wrapper."""
        raise NotImplementedError("get_status not supported in capability wrapper")

    async def wait_for(self, command_id: str, timeout: float | None = None):
        """Not implemented for capability wrapper."""
        raise NotImplementedError("wait_for not supported in capability wrapper")

    def store_completed_result(self, command_id: str, command_line: str, cwd: str, result):
        """Not implemented for capability wrapper."""
        raise NotImplementedError("store_completed_result not supported in capability wrapper")


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
        instance = self._session.lease.get_instance()
        if not instance:
            # Ensure instance exists
            from sandbox.runtime import RemoteWrappedRuntime
            if isinstance(self._session.runtime, RemoteWrappedRuntime):
                instance = self._session.lease.ensure_active_instance(self._session.runtime.provider)
            else:
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
