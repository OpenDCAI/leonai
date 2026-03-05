"""LocalSandbox with ChatSession-managed persistent terminal runtime."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from sandbox.base import Sandbox
from sandbox.manager import SandboxManager
from sandbox.providers.local import LocalSessionProvider  # noqa: F401 — re-export for back-compat
from sandbox.thread_context import get_current_thread_id, set_current_thread_id

if TYPE_CHECKING:
    from sandbox.capability import SandboxCapability
    from sandbox.interfaces.executor import BaseExecutor
    from sandbox.interfaces.filesystem import FileSystemBackend


class _LazyLocalExecutor:
    def __init__(self, sandbox: LocalSandbox):
        self._sandbox = sandbox
        self.is_remote = False
        self.runtime_owns_cwd = True
        self.shell_name = "local-session"

    def __getattr__(self, name: str):
        return getattr(self._sandbox._get_capability().command, name)


class LocalSandbox(Sandbox):
    def __init__(self, workspace_root: str, db_path: Path | None = None) -> None:
        self._workspace_root = workspace_root
        target_db = db_path or (Path.home() / ".leon" / "sandbox.db")
        self._provider = LocalSessionProvider(default_cwd=workspace_root)
        self._manager = SandboxManager(provider=self._provider, db_path=target_db)
        self._capability_cache: dict[str, SandboxCapability] = {}

    @property
    def name(self) -> str:
        return "local"

    @property
    def working_dir(self) -> str:
        return self._workspace_root

    @property
    def env_label(self) -> str:
        return "Local host"

    @property
    def manager(self) -> SandboxManager:
        return self._manager

    def _get_capability(self) -> SandboxCapability:
        thread_id = get_current_thread_id()
        if not thread_id:
            raise RuntimeError("No thread_id set. Call set_current_thread_id first.")
        if thread_id not in self._capability_cache:
            self._capability_cache[thread_id] = self._manager.get_sandbox(thread_id)
        return self._capability_cache[thread_id]

    def ensure_session(self, thread_id: str) -> None:
        set_current_thread_id(thread_id)
        self._capability_cache.pop(thread_id, None)
        self._get_capability()

    def pause_thread(self, thread_id: str) -> bool:
        self._capability_cache.pop(thread_id, None)
        return self._manager.pause_session(thread_id)

    def resume_thread(self, thread_id: str) -> bool:
        self._capability_cache.pop(thread_id, None)
        return self._manager.resume_session(thread_id)

    def fs(self) -> FileSystemBackend | None:
        return None

    def shell(self) -> BaseExecutor:
        return _LazyLocalExecutor(self)  # type: ignore[return-value]

    def close(self) -> None:
        for session in self._manager.list_sessions():
            self._manager.destroy_session(session["thread_id"])
