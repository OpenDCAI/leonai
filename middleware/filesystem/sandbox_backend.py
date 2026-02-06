"""Sandbox filesystem backend.

Delegates all I/O to SandboxProvider via SandboxManager.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from middleware.filesystem.backend import (
    DirEntry,
    DirListResult,
    FileReadResult,
    FileSystemBackend,
    FileWriteResult,
)

if TYPE_CHECKING:
    from sandbox.manager import SandboxManager


class SandboxFileBackend(FileSystemBackend):
    """Backend that delegates to a SandboxProvider.

    Args:
        manager: SandboxManager for provider access
        get_session_id: Callable that returns the current session ID
    """

    _is_sandbox = True  # marker for middleware to skip local-only logic

    def __init__(
        self,
        manager: SandboxManager,
        get_session_id: Callable[[], str],
    ) -> None:
        self._manager = manager
        self._get_session_id = get_session_id

    @property
    def _provider(self):
        return self._manager.provider

    def read_file(self, path: str) -> FileReadResult:
        session_id = self._get_session_id()
        content = self._provider.read_file(session_id, path)
        return FileReadResult(content=content, size=len(content))

    def write_file(self, path: str, content: str) -> FileWriteResult:
        session_id = self._get_session_id()
        try:
            self._provider.write_file(session_id, path, content)
            return FileWriteResult(success=True)
        except Exception as e:
            return FileWriteResult(success=False, error=str(e))

    def file_exists(self, path: str) -> bool:
        """Check existence by attempting to read or list parent.

        Sandbox providers don't have a dedicated exists() method,
        so we try reading the file and catch errors.
        """
        session_id = self._get_session_id()
        try:
            self._provider.read_file(session_id, path)
            return True
        except Exception:
            # Could be a directory — try list_dir
            try:
                self._provider.list_dir(session_id, path)
                return True
            except Exception:
                return False

    def file_mtime(self, path: str) -> float | None:
        # Sandbox has no local mtime — staleness detection gracefully degrades
        return None

    def file_size(self, path: str) -> int | None:
        # Not reliably available from sandbox providers
        return None

    def is_dir(self, path: str) -> bool:
        session_id = self._get_session_id()
        try:
            self._provider.list_dir(session_id, path)
            return True
        except Exception:
            return False

    def list_dir(self, path: str) -> DirListResult:
        session_id = self._get_session_id()
        try:
            items = self._provider.list_dir(session_id, path)
            entries = []
            for item in items:
                name = item.get("name", "?")
                item_type = item.get("type", "file")
                size = item.get("size", 0)
                entries.append(DirEntry(
                    name=name,
                    is_dir=(item_type == "directory"),
                    size=size,
                ))
            return DirListResult(entries=entries)
        except Exception as e:
            return DirListResult(error=str(e))
