"""RemoteSandbox — base class for all remote sandbox implementations.

Uses new architecture: Thread → ChatSession → Runtime → Terminal → Lease
"""

from __future__ import annotations

from pathlib import Path

from sandbox.base import Sandbox
from sandbox.capability import SandboxCapability
from sandbox.config import SandboxConfig
from sandbox.interfaces import BaseExecutor, FileSystemBackend
from sandbox.manager import SandboxManager
from sandbox.provider import SandboxProvider
from sandbox.thread_context import get_current_thread_id, set_current_thread_id


class RemoteSandbox(Sandbox):
    """Base class for remote sandboxes (AgentBay, Docker, E2B, Daytona).

    New architecture:
    - Uses SandboxCapability wrapper
    - Terminal state persists across sessions
    - Lease manages shared compute resources
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
        self._provider = provider
        self._manager = SandboxManager(
            provider=provider,
            db_path=db_path,
        )
        self._on_exit = config.on_exit

        # Cache capability per thread
        self._capability_cache: dict[str, SandboxCapability] = {}
        self._init_commands_run: set[str] = set()

    def _get_capability(self) -> SandboxCapability:
        """Get capability for current thread."""
        thread_id = get_current_thread_id()
        if not thread_id:
            raise RuntimeError("No thread_id set. Call set_current_thread_id first.")

        if thread_id not in self._capability_cache:
            capability = self._manager.get_sandbox(thread_id)

            # Run init commands on first access
            if self._config.init_commands and thread_id not in self._init_commands_run:
                self._run_init_commands(capability)
                self._init_commands_run.add(thread_id)

            self._capability_cache[thread_id] = capability

        return self._capability_cache[thread_id]

    def _run_init_commands(self, capability: SandboxCapability) -> None:
        """Run init commands on new session."""
        import asyncio

        for i, cmd in enumerate(self._config.init_commands, 1):
            result = asyncio.run(capability.command.execute(cmd))
            if result.exit_code != 0:
                raise RuntimeError(
                    f"Init command #{i} failed: {cmd}\n"
                    f"exit={result.exit_code}\n"
                    f"stderr={result.stderr}\n"
                    f"stdout={result.stdout}"
                )

    def fs(self) -> FileSystemBackend:
        # Return a lazy wrapper that defers capability lookup until actual use
        # This allows agent initialization before thread_id is set
        class LazyFSBackend:
            def __init__(self, remote_sandbox):
                self._remote = remote_sandbox
                # Set is_remote immediately so middleware can check it
                self.is_remote = True

            def __getattr__(self, name):
                # Defer to actual backend when methods are called
                return getattr(self._remote._get_capability().fs, name)

        return LazyFSBackend(self)  # type: ignore

    def shell(self) -> BaseExecutor:
        # Return a lazy wrapper that defers capability lookup until actual use
        class LazyExecutor:
            def __init__(self, remote_sandbox):
                self._remote = remote_sandbox
                # @@@lazy-remote-flag - CommandMiddleware probes is_remote during init; keep this side-effect free.
                self.is_remote = True
                # @@@lazy-shell-name - CommandMiddleware logs shell_name during init.
                # Expose a static label so hasattr/getattr won't trigger capability lookup before thread_id is set.
                self.shell_name = "remote"

            def __getattr__(self, name):
                # Defer to actual backend when methods are called
                return getattr(self._remote._get_capability().command, name)

        return LazyExecutor(self)  # type: ignore

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
                    )
                print(f"[{self.name}] Destroyed all sessions")
        except Exception as e:
            print(f"[{self.name}] Cleanup error: {e}")

    def ensure_session(self, thread_id: str) -> None:
        """Ensure session exists for thread."""
        set_current_thread_id(thread_id)
        # Clear cache to force re-fetch
        self._capability_cache.pop(thread_id, None)
        self._get_capability()

    def pause_thread(self, thread_id: str) -> bool:
        """Pause the sandbox session for a thread."""
        self._capability_cache.pop(thread_id, None)
        return self._manager.pause_session(thread_id)

    def resume_thread(self, thread_id: str) -> bool:
        """Resume the sandbox session for a thread."""
        self._capability_cache.pop(thread_id, None)
        return self._manager.resume_session(thread_id)
