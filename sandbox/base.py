"""Sandbox ABC — unified interface for execution environments.

A Sandbox bundles sub-capabilities by interaction surface:
- fs()    → FileSystemBackend  (consumed by FileSystemMiddleware)
- shell() → BaseExecutor       (consumed by CommandMiddleware)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from middleware.command.base import BaseExecutor
    from middleware.filesystem.backend import FileSystemBackend


class Sandbox(ABC):
    """Abstract sandbox — one instance per agent lifetime."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Identifier: 'local', 'agentbay', 'docker', ..."""
        ...

    @property
    @abstractmethod
    def working_dir(self) -> str:
        """Default working directory inside this sandbox."""
        ...

    @property
    @abstractmethod
    def env_label(self) -> str:
        """Human-readable label for system prompt."""
        ...

    @abstractmethod
    def fs(self) -> FileSystemBackend | None:
        """FileSystem backend, or None to use default (LocalBackend)."""
        ...

    @abstractmethod
    def shell(self) -> BaseExecutor | None:
        """Shell executor, or None to use default (OS auto-detect)."""
        ...

    def close(self) -> None:
        """Clean up on agent exit. Default: no-op."""
        pass

    def ensure_session(self, thread_id: str) -> None:
        """Eagerly create/resume session for thread. Default: no-op.

        Called before agent.invoke() to avoid lazy SQLite access
        during async tool calls.
        """
        pass
