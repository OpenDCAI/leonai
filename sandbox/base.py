"""Sandbox ABC — unified interface for execution environments.

A Sandbox bundles sub-capabilities by interaction surface:
- fs()    → FileSystemBackend  (consumed by FileSystemMiddleware)
- shell() → BaseExecutor       (consumed by CommandMiddleware)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sandbox.interfaces.executor import BaseExecutor
    from sandbox.interfaces.filesystem import FileSystemBackend


class Sandbox(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def working_dir(self) -> str: ...

    @property
    @abstractmethod
    def env_label(self) -> str: ...

    @abstractmethod
    def fs(self) -> FileSystemBackend | None: ...

    @abstractmethod
    def shell(self) -> BaseExecutor | None: ...

    def close(self) -> None:
        pass

    def ensure_session(self, thread_id: str) -> None:
        pass
