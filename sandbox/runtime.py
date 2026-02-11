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
import os
import re
import shlex
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
        self.runtime_id = f"runtime-{uuid.uuid4().hex[:12]}"

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
        self._master_fd: int | None = None
        self._session_lock = asyncio.Lock()
        self._baseline_env: dict[str, str] | None = None

    @staticmethod
    def _parse_env_output(raw: str) -> dict[str, str]:
        env_map: dict[str, str] = {}
        for line in raw.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            env_map[key] = value
        return env_map

    async def _pty_write(self, data: str) -> None:
        if self._master_fd is None:
            raise RuntimeError("PTY master fd is not available")
        payload = data.encode()
        offset = 0
        while offset < len(payload):
            try:
                written = os.write(self._master_fd, payload[offset:])
            except BlockingIOError:
                await asyncio.sleep(0.01)
                continue
            offset += written

    async def _ensure_session(self) -> asyncio.subprocess.Process:
        """Ensure persistent PTY shell session exists."""
        if self._session is not None and self._session.returncode is None and self._master_fd is not None:
            return self._session

        state = self.terminal.get_state()
        master_fd, slave_fd = os.openpty()
        try:
            self._session = await asyncio.create_subprocess_exec(
                *self.shell_command,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=state.cwd,
                start_new_session=True,
            )
        finally:
            os.close(slave_fd)

        self._master_fd = master_fd
        os.set_blocking(self._master_fd, False)

        # @@@pty-bootstrap - Disable prompt/echo so marker parsing stays deterministic.
        await self._pty_write("export PS1=''\nstty -echo\n")
        baseline_stdout, _, _ = await self._send_command("env")
        self._baseline_env = self._parse_env_output(baseline_stdout)
        if state.env_delta:
            exports = "".join(f"export {key}={shlex.quote(value)}\n" for key, value in state.env_delta.items())
            await self._pty_write(exports)

        return self._session

    async def _send_command(self, command: str) -> tuple[str, str, int]:
        """Send command to persistent PTY session and read output until marker."""
        if self._master_fd is None:
            raise RuntimeError("PTY session is not initialized")

        marker = f"__LEON_END_{uuid.uuid4().hex[:8]}__"
        marker_pattern = re.compile(rf"{re.escape(marker)}:(-?\d+)")
        full_cmd = f"{command}\nprintf '\\n{marker}:%s\\n' \"$?\"\n"
        await self._pty_write(full_cmd)

        buffer = ""
        exit_code = 0

        while True:
            try:
                chunk = os.read(self._master_fd, 4096)
            except BlockingIOError:
                if self._session and self._session.returncode is not None:
                    break
                await asyncio.sleep(0.01)
                continue
            if not chunk:
                if self._session and self._session.returncode is not None:
                    break
                await asyncio.sleep(0.01)
                continue
            buffer += chunk.decode("utf-8", errors="replace")
            match = marker_pattern.search(buffer)
            if not match:
                continue
            try:
                exit_code = int(match.group(1))
            except ValueError:
                exit_code = 1
            buffer = buffer[: match.start()]
            break

        clean_stdout = buffer.replace("\r", "")
        return clean_stdout, "", exit_code

    async def execute(self, command: str, timeout: float | None = None) -> ExecuteResult:
        """Execute command in local shell."""
        async with self._session_lock:
            try:
                if self.lease.observed_state == "paused":
                    raise RuntimeError(
                        f"Sandbox lease {self.lease.lease_id} is paused. Resume before executing commands."
                    )
                await self._ensure_session()

                stdout, stderr, exit_code = await asyncio.wait_for(
                    self._send_command(command),
                    timeout=timeout,
                )

                # Capture state snapshot after each command so new ChatSession can hydrate from DB.
                pwd_stdout, _, _ = await self._send_command("pwd")
                env_stdout, _, _ = await self._send_command("env")
                new_cwd = pwd_stdout.strip() or self.terminal.get_state().cwd
                env_map = self._parse_env_output(env_stdout)
                baseline_env = self._baseline_env or {}
                persisted_keys = set(self.terminal.get_state().env_delta.keys())
                env_delta = {k: v for k, v in env_map.items() if baseline_env.get(k) != v or k in persisted_keys}

                if new_cwd:
                    from sandbox.terminal import TerminalState

                    new_state = TerminalState(
                        cwd=new_cwd,
                        env_delta=env_delta,
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
                await self._session.wait()
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None


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

    @staticmethod
    def _looks_like_infra_error(text: str) -> bool:
        message = text.lower()
        markers = (
            "not found",
            "no such session",
            "session does not exist",
            "is paused",
            "stopped",
            "connection",
            "transport",
            "unreachable",
            "timed out",
            "timeout",
            "detached",
        )
        return any(marker in message for marker in markers)

    def _recover_infra(self) -> None:
        # @@@infra-recovery - Refresh provider truth once, then resume/recreate and retry command exactly once.
        status = self.lease.refresh_instance_status(self.provider, force=True, max_age_sec=0)
        if status == "paused":
            if not self.lease.resume_instance(self.provider):
                raise RuntimeError(f"Failed to resume paused lease {self.lease.lease_id}")
            return
        if status in {"detached", "unknown"}:
            self.lease.ensure_active_instance(self.provider)

    def _execute_once(self, command: str, timeout: float | None = None) -> ExecuteResult:
        instance = self.lease.ensure_active_instance(self.provider)
        state = self.terminal.get_state()
        timeout_ms = int(timeout * 1000) if timeout else 30000
        start_marker = f"__LEON_STATE_START_{uuid.uuid4().hex[:8]}__"
        end_marker = f"__LEON_STATE_END_{uuid.uuid4().hex[:8]}__"
        exports = "\n".join(f"export {key}={shlex.quote(value)}" for key, value in state.env_delta.items())
        wrapped = "\n".join(
            part
            for part in [
                f"cd {shlex.quote(state.cwd)} || exit 1",
                exports,
                command,
                "__leon_exit_code=$?",
                f"echo {shlex.quote(start_marker)}",
                "pwd",
                "env",
                f"echo {shlex.quote(end_marker)}",
                "exit $__leon_exit_code",
            ]
            if part
        )
        result = self.provider.execute(
            instance.instance_id,
            wrapped,
            timeout_ms=timeout_ms,
            cwd=state.cwd,
        )
        raw_output = result.output or ""

        try:
            pre_state, tail = raw_output.split(start_marker, 1)
            state_blob, post_state = tail.split(end_marker, 1)
            state_lines = [line for line in state_blob.strip().splitlines() if line.strip()]
            new_cwd = state.cwd
            env_map = state.env_delta
            if state_lines:
                parsed_cwd = state_lines[0].strip()
                if parsed_cwd:
                    new_cwd = parsed_cwd
                parsed_env: dict[str, str] = {}
                for line in state_lines[1:]:
                    if "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    parsed_env[key] = value
                if parsed_env:
                    env_map = parsed_env
            from sandbox.terminal import TerminalState

            self.update_terminal_state(TerminalState(cwd=new_cwd, env_delta=env_map))
            raw_output = (pre_state + post_state).strip()
        except ValueError:
            pass

        exit_code = result.exit_code
        if result.error and exit_code == 0:
            exit_code = 1

        return ExecuteResult(
            exit_code=exit_code,
            stdout=raw_output,
            stderr=result.error or "",
        )

    async def execute(self, command: str, timeout: float | None = None) -> ExecuteResult:
        """Execute command via provider."""
        try:
            first = await asyncio.to_thread(self._execute_once, command, timeout)
        except Exception as e:
            if not self._looks_like_infra_error(str(e)):
                raise
            await asyncio.to_thread(self._recover_infra)
            return await asyncio.to_thread(self._execute_once, command, timeout)

        if first.exit_code != 0 and self._looks_like_infra_error(first.stderr or first.stdout):
            await asyncio.to_thread(self._recover_infra)
            return await asyncio.to_thread(self._execute_once, command, timeout)

        return first

    async def close(self) -> None:
        """No-op for remote runtime - instance lifecycle managed by lease."""
        pass
