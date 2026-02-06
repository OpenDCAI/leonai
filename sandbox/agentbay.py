"""AgentBaySandbox — cloud sandbox via Alibaba AgentBay.

Creates SandboxFileBackend and SandboxExecutor at init time,
caching them for the agent's lifetime.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from sandbox.base import Sandbox
from sandbox.config import SandboxConfig
from sandbox.manager import SandboxManager
from sandbox.providers.agentbay import AgentBayProvider
from sandbox.thread_context import get_current_thread_id

if TYPE_CHECKING:
    from middleware.command.base import BaseExecutor
    from middleware.filesystem.backend import FileSystemBackend


class AgentBaySandbox(Sandbox):
    """Cloud sandbox backed by AgentBay."""

    def __init__(
        self,
        config: SandboxConfig,
        db_path: Path | None = None,
    ) -> None:
        ab = config.agentbay
        api_key = ab.api_key or os.getenv("AGENTBAY_API_KEY")
        if not api_key:
            raise ValueError("AgentBay sandbox requires AGENTBAY_API_KEY")

        provider = AgentBayProvider(
            api_key=api_key,
            region_id=ab.region_id,
            default_context_path=ab.context_path,
            image_id=ab.image_id,
        )

        self._manager = SandboxManager(
            provider=provider,
            db_path=db_path,
            default_context_id=config.context_id,
        )
        self._config = config
        self._on_exit = config.on_exit

        # @@@ Cache session_id per thread to avoid hitting SQLite on every tool call
        _session_cache: dict[str, str] = {}

        def _get_session_id() -> str:
            thread_id = get_current_thread_id()
            if not thread_id:
                raise RuntimeError("No thread_id set. Call set_current_thread_id first.")
            if thread_id not in _session_cache:
                info = self._manager.get_or_create_session(thread_id)
                _session_cache[thread_id] = info.session_id
            return _session_cache[thread_id]

        # Create and cache backends
        from middleware.command.sandbox_executor import SandboxExecutor
        from middleware.filesystem.sandbox_backend import SandboxFileBackend

        self._fs = SandboxFileBackend(self._manager, _get_session_id)
        self._shell = SandboxExecutor(
            self._manager,
            _get_session_id,
            default_cwd=ab.context_path,
        )
        self._get_session_id = _get_session_id

        print(f"[AgentBaySandbox] Initialized (region={ab.region_id})")

    @property
    def name(self) -> str:
        return "agentbay"

    @property
    def working_dir(self) -> str:
        return self._config.agentbay.context_path

    @property
    def env_label(self) -> str:
        return "Remote Linux sandbox (Ubuntu)"

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
                    print(f"[AgentBaySandbox] Paused {count} session(s)")
            elif self._on_exit == "destroy":
                for session in self._manager.list_sessions():
                    self._manager.destroy_session(session["thread_id"])
                print("[AgentBaySandbox] Destroyed all sessions")
        except Exception as e:
            print(f"[AgentBaySandbox] Cleanup error: {e}")

    def ensure_session(self, thread_id: str) -> None:
        from sandbox.thread_context import set_current_thread_id

        set_current_thread_id(thread_id)
        self._get_session_id()
