"""PhysicalTerminalRuntime - Ephemeral shell/pty process.

This module implements the runtime layer that owns the actual physical
shell process. The runtime is ephemeral and owned by ChatSession.

Architecture:
    ChatSession → PhysicalTerminalRuntime (ephemeral process)
                → AbstractTerminal (reference for state)
                → SandboxLease (reference for compute)
"""

from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sandbox.lease import SandboxLease
    from sandbox.provider import SandboxProvider
    from sandbox.terminal import AbstractTerminal, TerminalState

from sandbox.interfaces.executor import ExecuteResult


class PhysicalTerminalRuntime(ABC):
    """Ephemeral shell/pty process owned by ChatSession.

    This is the actual running process that executes commands.
    It's ephemeral - when the ChatSession ends, this dies.

    Responsibilities:
    - Own physical shell/pty process
    - Execute commands
    - Hydrate state from AbstractTerminal on startup
    - Persist state to AbstractTerminal after commands
    - Provide access to lease for I/O operations

    Does NOT:
    - Own terminal identity (that's AbstractTerminal)
    - Own compute lifecycle (that's SandboxLease)
    - Outlive ChatSession
    """

    def __init__(
        self,
        terminal: AbstractTerminal,
        lease: SandboxLease,
    ):
        self.terminal = terminal
        self.lease = lease
        self._hydrated = False

    @abstractmethod
    async def execute(self, command: str, timeout: float | None = None) -> ExecuteResult:
        """Execute command in this runtime.

        Should hydrate state on first execution, then persist state after.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the physical runtime process."""
        ...

    def get_terminal_state(self) -> TerminalState:
        """Get current terminal state."""
        return self.terminal.get_state()

    def update_terminal_state(self, state: TerminalState) -> None:
        """Update terminal state after command execution."""
        self.terminal.update_state(state)


class LocalPersistentShellRuntime(PhysicalTerminalRuntime):
    """Local persistent shell runtime (for local provider).

    Uses asyncio subprocess with persistent shell session.
    Similar to BashExecutor but integrated with terminal state.
    """

    def __init__(
        self,
        terminal: AbstractTerminal,
        lease: SandboxLease,
        shell_command: tuple[str, ...] = ("/bin/bash",),
    ):
        super().__init__(terminal, lease)
        self.shell_command = shell_command
        self._session: asyncio.subprocess.Process | None = None
        self._session_lock = asyncio.Lock()

    async def _ensure_session(self) -> asyncio.subprocess.Process:
        """Ensure persistent shell session exists."""
        if self._session is None or self._session.returncode is not None:
            state = self.terminal.get_state()
            self._session = await asyncio.create_subprocess_exec(
                *self.shell_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=state.cwd,
            )
            # Disable PS1 prompt
            self._session.stdin.write(b"export PS1=''\n")
            await self._session.stdin.drain()

            # Hydrate env_delta
            if state.env_delta:
                for key, value in state.env_delta.items():
                    self._session.stdin.write(f"export {key}='{value}'\n".encode())
                await self._session.stdin.drain()

            self._hydrated = True

        return self._session

    async def _send_command(
        self, proc: asyncio.subprocess.Process, command: str
    ) -> tuple[str, str, int]:
        """Send command to persistent session and read output."""
        marker = f"__END_{uuid.uuid4().hex[:8]}__"
        full_cmd = f"{command}\necho {marker} $?\n"

        proc.stdin.write(full_cmd.encode())
        await proc.stdin.drain()

        stdout_lines = []
        exit_code = 0

        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            line_str = line.decode("utf-8", errors="replace")
            if marker in line_str:
                parts = line_str.split()
                if len(parts) >= 2:
                    try:
                        exit_code = int(parts[1])
                    except ValueError:
                        pass
                break
            stdout_lines.append(line_str)

        return "".join(stdout_lines), "", exit_code

    async def execute(self, command: str, timeout: float | None = None) -> ExecuteResult:
        """Execute command in local shell."""
        async with self._session_lock:
            try:
                proc = await self._ensure_session()

                stdout, stderr, exit_code = await asyncio.wait_for(
                    self._send_command(proc, command),
                    timeout=timeout,
                )

                # Update cwd after command (read from shell)
                pwd_stdout, _, _ = await self._send_command(proc, "pwd")
                new_cwd = pwd_stdout.strip()

                if new_cwd:
                    from sandbox.terminal import TerminalState

                    state = self.terminal.get_state()
                    new_state = TerminalState(
                        cwd=new_cwd,
                        env_delta=state.env_delta,
                    )
                    self.update_terminal_state(new_state)

                return ExecuteResult(
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr,
                    timed_out=False,
                )
            except TimeoutError:
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

    async def close(self) -> None:
        """Close the shell session."""
        if self._session and self._session.returncode is None:
            try:
                self._session.terminate()
                await asyncio.wait_for(self._session.wait(), timeout=5.0)
            except Exception:
                self._session.kill()


class RemoteWrappedRuntime(PhysicalTerminalRuntime):
    """Remote runtime that wraps provider execute calls.

    For remote providers (E2B, AgentBay, etc), there's no local process.
    Instead, we wrap the provider's execute() and track state via markers.
    """

    def __init__(
        self,
        terminal: AbstractTerminal,
        lease: SandboxLease,
        provider: SandboxProvider,
    ):
        super().__init__(terminal, lease)
        self.provider = provider

    async def execute(self, command: str, timeout: float | None = None) -> ExecuteResult:
        """Execute command via provider."""
        # Ensure instance is active
        instance = self.lease.ensure_active_instance(self.provider)

        # Hydrate state on first execution
        if not self._hydrated:
            state = self.terminal.get_state()
            # Send cd command to set cwd
            if state.cwd != "/root":
                self.provider.execute(
                    instance.instance_id,
                    f"cd '{state.cwd}'",
                    timeout_ms=5000,
                )
            # Send export commands for env_delta
            for key, value in state.env_delta.items():
                self.provider.execute(
                    instance.instance_id,
                    f"export {key}='{value}'",
                    timeout_ms=5000,
                )
            self._hydrated = True

        # Execute command with cwd
        state = self.terminal.get_state()
        timeout_ms = int(timeout * 1000) if timeout else 30000

        result = self.provider.execute(
            instance.instance_id,
            command,
            timeout_ms=timeout_ms,
            cwd=state.cwd,
        )

        # Update cwd after command (only if command might have changed it)
        if "cd " in command or command.startswith("cd"):
            pwd_result = self.provider.execute(
                instance.instance_id,
                "pwd",
                timeout_ms=5000,
                cwd=state.cwd,
            )

            output = getattr(pwd_result, 'output', None) or getattr(pwd_result, 'stdout', '')
            if output:
                new_cwd = output.strip()
                if new_cwd and new_cwd != state.cwd:
                    from sandbox.terminal import TerminalState

                    new_state = TerminalState(
                        cwd=new_cwd,
                        env_delta=state.env_delta,
                    )
                    self.update_terminal_state(new_state)

        return ExecuteResult(
            exit_code=result.exit_code,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )

    async def close(self) -> None:
        """No-op for remote runtime - instance lifecycle managed by lease."""
        pass
