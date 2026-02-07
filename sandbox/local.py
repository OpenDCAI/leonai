"""LocalSandbox — passthrough to host OS.

No isolation. FileSystemMiddleware and CommandMiddleware use their defaults.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sandbox.base import Sandbox

if TYPE_CHECKING:
    from sandbox.interfaces.executor import BaseExecutor
    from sandbox.interfaces.filesystem import FileSystemBackend


class LocalSandbox(Sandbox):
    """Local execution — no sandbox, direct host access."""

    def __init__(self, workspace_root: str) -> None:
        self._workspace_root = workspace_root

    @property
    def name(self) -> str:
        return "local"

    @property
    def working_dir(self) -> str:
        return self._workspace_root

    @property
    def env_label(self) -> str:
        return "Local host"

    def fs(self) -> FileSystemBackend | None:
        return None  # FileSystemMiddleware defaults to LocalBackend

    def shell(self) -> BaseExecutor | None:
        return None  # CommandMiddleware defaults to OS auto-detect
