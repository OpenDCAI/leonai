"""RemoteSandbox — base class for all remote sandbox implementations.

Extracts common logic shared by AgentBaySandbox, DockerSandbox, E2BSandbox:
- Session cache + _get_session_id closure
- SandboxFileBackend + SandboxExecutor creation
- fs() / shell() / manager property
- close() (pause/destroy)
- ensure_session()
"""

from __future__ import annotations

from pathlib import Path

from sandbox.base import Sandbox
from sandbox.config import SandboxConfig
from sandbox.executor import SandboxExecutor
from sandbox.file_backend import SandboxFileBackend
from sandbox.interfaces import BaseExecutor, FileSystemBackend
from sandbox.manager import SandboxManager
from sandbox.provider import SandboxProvider
from sandbox.thread_context import get_current_thread_id, set_current_thread_id


class RemoteSandbox(Sandbox):
    """Base class for remote sandboxes (AgentBay, Docker, E2B).

    Subclasses create a provider and call super().__init__().
    They only need to implement: name, working_dir, env_label.
    """

    def __init__(
        self,
        provider: SandboxProvider,
        config: SandboxConfig,
        default_cwd: str,
        db_path: Path | None = None,
    ) -> None:
        self._config = config
        self._default_cwd = default_cwd
        self._manager = SandboxManager(
            provider=provider,
            db_path=db_path,
            on_session_ready=self._run_init_commands if config.init_commands else None,
        )
        self._on_exit = config.on_exit

        # Cache session_id per thread to avoid hitting SQLite on every tool call
        _session_cache: dict[str, str] = {}

        def _get_session_id() -> str:
            thread_id = get_current_thread_id()
            if not thread_id:
                raise RuntimeError("No thread_id set. Call set_current_thread_id first.")
            if thread_id not in _session_cache:
                info = self._manager.get_or_create_session(thread_id)
                _session_cache[thread_id] = info.session_id
            return _session_cache[thread_id]

        self._get_session_id = _get_session_id
        self._fs = SandboxFileBackend(self._manager, _get_session_id)
        self._shell = SandboxExecutor(
            self._manager,
            _get_session_id,
            default_cwd=default_cwd,
        )

    def _run_init_commands(self, session_id: str, reason: str) -> None:
        for i, cmd in enumerate(self._config.init_commands, 1):
            result = self._manager.provider.execute(session_id, cmd, cwd=self._default_cwd)
            if result.error or result.exit_code != 0:
                raise RuntimeError(
                    f"Init command #{i} failed ({reason}): {cmd}\n"
                    f"exit={result.exit_code} error={result.error or ''}\n"
                    f"output={result.output or ''}"
                )

    def fs(self) -> FileSystemBackend:
        return self._fs

    def shell(self) -> BaseExecutor:
        return self._shell

    @property
    def manager(self) -> SandboxManager:
        """Expose manager for sandbox TUI widget."""
        return self._manager

    def close(self) -> None:
        try:
            if self._on_exit == "pause":
                count = self._manager.pause_all_sessions()
                if count > 0:
                    print(f"[{self.name}] Paused {count} session(s)")
            elif self._on_exit == "destroy":
                for session in self._manager.list_sessions():
                    self._manager.destroy_session(
                        thread_id=session["thread_id"],
                        session_id=session["session_id"],
                    )
                print(f"[{self.name}] Destroyed all sessions")
        except Exception as e:
            print(f"[{self.name}] Cleanup error: {e}")

    def ensure_session(self, thread_id: str) -> None:
        set_current_thread_id(thread_id)
        self._get_session_id()
