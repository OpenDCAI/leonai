"""LocalPersistentShellRuntime — local PTY-backed persistent shell."""

from __future__ import annotations

import asyncio
import shlex
from collections.abc import Callable
from typing import TYPE_CHECKING

from sandbox.interfaces.executor import ExecuteResult
from sandbox.runtimes.base import (
    PhysicalTerminalRuntime,
    _SubprocessPtySession,
    _parse_env_output,
)

if TYPE_CHECKING:
    from sandbox.lease import SandboxLease
    from sandbox.terminal import AbstractTerminal


class LocalPersistentShellRuntime(PhysicalTerminalRuntime):
    """Local persistent shell runtime (for local provider).

    Uses a persistent PTY-backed shell session.
    """

    def __init__(
        self,
        terminal: AbstractTerminal,
        lease: SandboxLease,
        shell_command: tuple[str, ...] = ("/bin/bash",),
    ):
        super().__init__(terminal, lease)
        self.shell_command = shell_command
        self._pty_session: _SubprocessPtySession | None = None
        self._session = None
        self._session_lock = asyncio.Lock()
        self._baseline_env: dict[str, str] | None = None

    def _ensure_session_sync(self, timeout: float | None) -> _SubprocessPtySession:
        if self._pty_session and self._pty_session.is_alive():
            return self._pty_session

        state = self.terminal.get_state()
        self._pty_session = _SubprocessPtySession(list(self.shell_command), cwd=state.cwd)
        self._pty_session.start()
        self._session = self._pty_session.process

        self._pty_session.run("export PS1=''; stty -echo", timeout)
        if state.env_delta:
            exports = "\n".join(f"export {k}={shlex.quote(v)}" for k, v in state.env_delta.items())
            if exports:
                self._pty_session.run(exports, timeout)
        baseline_out, _, _ = self._pty_session.run("env", timeout)
        self._baseline_env = _parse_env_output(baseline_out)
        return self._pty_session

    def _execute_once_sync(
        self,
        command: str,
        timeout: float | None,
        on_stdout_chunk: Callable[[str], None] | None = None,
    ) -> ExecuteResult:
        if self.lease.observed_state == "paused":
            raise RuntimeError(f"Sandbox lease {self.lease.lease_id} is paused. Resume before executing commands.")

        state = self.terminal.get_state()
        pty_session = self._ensure_session_sync(timeout)
        stdout, stderr, exit_code = pty_session.run(command, timeout, on_stdout_chunk=on_stdout_chunk)

        # Capture state snapshot after each command so new ChatSession can hydrate from DB.
        pwd_stdout, _, _ = pty_session.run("pwd", timeout)
        env_stdout, _, _ = pty_session.run("env", timeout)
        pwd_lines = [line.strip() for line in pwd_stdout.splitlines() if line.strip()]
        new_cwd = pwd_lines[-1] if pwd_lines else state.cwd
        env_map = _parse_env_output(env_stdout)
        baseline_env = self._baseline_env or {}
        persisted_keys = set(state.env_delta.keys())
        env_delta = {k: v for k, v in env_map.items() if baseline_env.get(k) != v or k in persisted_keys}

        if new_cwd:
            from sandbox.terminal import TerminalState

            self.update_terminal_state(TerminalState(cwd=new_cwd, env_delta=env_delta))

        return ExecuteResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            timed_out=False,
        )

    async def _execute_background_command(
        self,
        command: str,
        timeout: float | None,
        on_stdout_chunk: Callable[[str], None] | None = None,
    ) -> ExecuteResult:
        async with self._session_lock:
            try:
                return await asyncio.to_thread(self._execute_once_sync, command, timeout, on_stdout_chunk)
            except TimeoutError:
                await self._recover_after_timeout()
                return ExecuteResult(
                    exit_code=-1,
                    stdout="",
                    stderr=f"Command timed out after {timeout}s",
                    timed_out=True,
                )
            except Exception as e:
                return ExecuteResult(
                    exit_code=1,
                    stdout="",
                    stderr=f"Error: {e}",
                )

    async def _recover_after_timeout(self) -> None:
        """Recover PTY session after a command timeout."""
        if self._pty_session is None:
            return
        recovered = await asyncio.to_thread(self._pty_session.interrupt_and_recover)
        if not recovered:
            await asyncio.to_thread(self._pty_session.close)
            self._pty_session = None

    async def execute(self, command: str, timeout: float | None = None) -> ExecuteResult:
        """Execute command in local shell."""
        return await self._execute_background_command(command, timeout=timeout)

    async def close(self) -> None:
        """Close the shell session."""
        if self._pty_session:
            await asyncio.to_thread(self._pty_session.close)
            self._session = self._pty_session.process
