"""LocalSandbox with ChatSession-managed persistent terminal runtime."""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from sandbox.base import Sandbox
from sandbox.manager import SandboxManager
from sandbox.provider import Metrics, ProviderCapability, ProviderExecResult, SandboxProvider, SessionInfo
from sandbox.thread_context import get_current_thread_id, set_current_thread_id

if TYPE_CHECKING:
    from sandbox.capability import SandboxCapability
    from sandbox.interfaces.executor import BaseExecutor
    from sandbox.interfaces.filesystem import FileSystemBackend


@dataclass
class LocalSessionProvider(SandboxProvider):
    name: str = "local"
    db_path: Path = Path.home() / ".leon" / "sandbox.db"

    def get_capability(self) -> ProviderCapability:
        return ProviderCapability(
            can_pause=True,
            can_resume=True,
            can_destroy=True,
            supports_webhook=False,
        )

    def create_session(self, context_id: str | None = None) -> SessionInfo:
        session_id = context_id or f"local-{uuid.uuid4().hex[:12]}"
        return SessionInfo(session_id=session_id, provider="local", status="running")

    def destroy_session(self, session_id: str, sync: bool = True) -> bool:
        return True

    def pause_session(self, session_id: str) -> bool:
        return True

    def resume_session(self, session_id: str) -> bool:
        return True

    def get_session_status(self, session_id: str) -> str:
        with sqlite3.connect(str(self.db_path), timeout=5) as conn:
            row = conn.execute(
                """
                SELECT status
                FROM sandbox_instances
                WHERE instance_id = ?
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        if not row or not row[0]:
            return "detached"
        status = str(row[0]).lower()
        if status in {"running", "paused", "unknown"}:
            return status
        if status in {"stopped", "dead", "deleted"}:
            return "detached"
        return "unknown"

    def execute(
        self,
        session_id: str,
        command: str,
        timeout_ms: int = 30000,
        cwd: str | None = None,
    ) -> ProviderExecResult:
        raise RuntimeError("Local provider execute() is unsupported; use runtime shell execution.")

    def read_file(self, session_id: str, path: str) -> str:
        raise RuntimeError("Local provider read_file() is unsupported.")

    def write_file(self, session_id: str, path: str, content: str) -> str:
        raise RuntimeError("Local provider write_file() is unsupported.")

    def list_dir(self, session_id: str, path: str) -> list[dict]:
        raise RuntimeError("Local provider list_dir() is unsupported.")

    def get_metrics(self, session_id: str) -> Metrics | None:
        return None


class LocalSandbox(Sandbox):
    def __init__(self, workspace_root: str, db_path: Path | None = None) -> None:
        self._workspace_root = workspace_root
        target_db = db_path or (Path.home() / ".leon" / "sandbox.db")
        self._provider = LocalSessionProvider(db_path=target_db)
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
        class LazyLocalExecutor:
            def __init__(self, sandbox: LocalSandbox):
                self._sandbox = sandbox
                self.is_remote = False
                self.runtime_owns_cwd = True
                self.shell_name = "local-session"

            def __getattr__(self, name: str):
                return getattr(self._sandbox._get_capability().command, name)

        return LazyLocalExecutor(self)  # type: ignore[return-value]

    def close(self) -> None:
        for session in self._manager.list_sessions():
            self._manager.destroy_session(session["thread_id"])
