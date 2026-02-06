"""DockerSandbox — local Docker container sandbox.

Same pattern as AgentBaySandbox but uses DockerProvider.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from sandbox.base import Sandbox
from sandbox.config import SandboxConfig
from sandbox.manager import SandboxManager
from sandbox.providers.docker import DockerProvider
from sandbox.thread_context import get_current_thread_id

if TYPE_CHECKING:
    from middleware.command.base import BaseExecutor
    from middleware.filesystem.backend import FileSystemBackend


class DockerSandbox(Sandbox):
    """Local Docker container sandbox."""

    def __init__(
        self,
        config: SandboxConfig,
        db_path: Path | None = None,
    ) -> None:
        dc = config.docker
        provider = DockerProvider(
            image=dc.image,
            mount_path=dc.mount_path,
        )

        self._manager = SandboxManager(
            provider=provider,
            db_path=db_path,
            default_context_id=config.context_id,
        )
        self._config = config
        self._on_exit = config.on_exit

        def _get_session_id() -> str:
            thread_id = get_current_thread_id()
            if not thread_id:
                raise RuntimeError("No thread_id set. Call set_current_thread_id first.")
            info = self._manager.get_or_create_session(thread_id)
            return info.session_id

        from middleware.command.sandbox_executor import SandboxExecutor
        from middleware.filesystem.sandbox_backend import SandboxFileBackend

        self._fs = SandboxFileBackend(self._manager, _get_session_id)
        self._shell = SandboxExecutor(
            self._manager, _get_session_id,
            default_cwd=dc.mount_path,
        )

        print(f"[DockerSandbox] Initialized (image={dc.image})")

    @property
    def name(self) -> str:
        return "docker"

    @property
    def working_dir(self) -> str:
        return self._config.docker.mount_path

    @property
    def env_label(self) -> str:
        return "Local Docker sandbox (Ubuntu)"

    def fs(self) -> FileSystemBackend:
        return self._fs

    def shell(self) -> BaseExecutor:
        return self._shell

    @property
    def manager(self) -> SandboxManager:
        return self._manager

    def close(self) -> None:
        try:
            if self._on_exit == "pause":
                count = self._manager.pause_all_sessions()
                if count > 0:
                    print(f"[DockerSandbox] Paused {count} session(s)")
            elif self._on_exit == "destroy":
                for session in self._manager.list_sessions():
                    self._manager.destroy_session(session["thread_id"])
                print("[DockerSandbox] Destroyed all sessions")
        except Exception as e:
            print(f"[DockerSandbox] Cleanup error: {e}")
