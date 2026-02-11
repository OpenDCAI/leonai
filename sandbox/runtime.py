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
import re
import shlex
import time
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


def _parse_env_output(raw: str) -> dict[str, str]:
    env_map: dict[str, str] = {}
    for line in raw.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_map[key] = value
    return env_map


def _sanitize_shell_output(raw: str) -> str:
    cleaned = raw.replace("\x01\x01\x01", "").replace("\x02\x02\x02", "")
    cleaned = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", cleaned)
    cleaned = re.sub(r"\x1B\][^\x07]*\x07", "", cleaned)
    return cleaned


def _extract_state_from_output(
    raw_output: str,
    start_marker: str,
    end_marker: str,
    *,
    cwd_fallback: str,
    env_fallback: dict[str, str],
) -> tuple[str, dict[str, str], str]:
    try:
        pre_state, tail = raw_output.split(start_marker, 1)
        state_blob, post_state = tail.split(end_marker, 1)
        state_lines = [line for line in state_blob.strip().splitlines() if line.strip()]
        new_cwd = cwd_fallback
        env_map = env_fallback
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
        cleaned_output = (pre_state + post_state).strip()
        return new_cwd, env_map, cleaned_output
    except ValueError:
        return cwd_fallback, env_fallback, raw_output


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
        self._baseline_env: dict[str, str] | None = None

    async def _ensure_session(self) -> asyncio.subprocess.Process:
        """Ensure persistent shell session exists."""
        if self._session is None or self._session.returncode is not None:
            state = self.terminal.get_state()
            self._session = await asyncio.create_subprocess_exec(
                *self.shell_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=state.cwd,
            )
            self._session.stdin.write(b"export PS1=''\n")
            await self._session.stdin.drain()
            baseline_stdout, _, _ = await self._send_command(self._session, "env")
            self._baseline_env = _parse_env_output(baseline_stdout)
            if state.env_delta:
                for key, value in state.env_delta.items():
                    self._session.stdin.write(f"export {key}={shlex.quote(value)}\n".encode())
                await self._session.stdin.drain()

        return self._session

    async def _send_command(self, proc: asyncio.subprocess.Process, command: str) -> tuple[str, str, int]:
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
                prefix, suffix = line_str.split(marker, 1)
                if prefix:
                    stdout_lines.append(prefix)
                parts = suffix.strip().split()
                if len(parts) >= 2:
                    try:
                        exit_code = int(parts[0])
                    except ValueError:
                        pass
                break
            stdout_lines.append(line_str)

        return "".join(stdout_lines), "", exit_code

    async def execute(self, command: str, timeout: float | None = None) -> ExecuteResult:
        """Execute command in local shell."""
        async with self._session_lock:
            try:
                if self.lease.observed_state == "paused":
                    raise RuntimeError(
                        f"Sandbox lease {self.lease.lease_id} is paused. Resume before executing commands."
                    )
                proc = await self._ensure_session()

                stdout, stderr, exit_code = await asyncio.wait_for(
                    self._send_command(proc, command),
                    timeout=timeout,
                )

                # Capture state snapshot after each command so new ChatSession can hydrate from DB.
                pwd_stdout, _, _ = await self._send_command(proc, "pwd")
                env_stdout, _, _ = await self._send_command(proc, "env")
                new_cwd = pwd_stdout.strip() or self.terminal.get_state().cwd
                env_map = _parse_env_output(env_stdout)
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


class _RemoteRuntimeBase(PhysicalTerminalRuntime):
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
            "not running",
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

    def _provider_sandbox(self, instance_id: str):
        getter = getattr(self.provider, "get_runtime_sandbox", None)
        if callable(getter):
            return getter(instance_id)
        private_getter = getattr(self.provider, "_get_sandbox", None)
        if callable(private_getter):
            return private_getter(instance_id)
        raise RuntimeError(f"Provider {getattr(self.provider, 'name', '?')} does not expose runtime sandbox handle")


class RemoteWrappedRuntime(_RemoteRuntimeBase):
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
        super().__init__(terminal, lease, provider)

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

        new_cwd, env_map, raw_output = _extract_state_from_output(
            raw_output,
            start_marker,
            end_marker,
            cwd_fallback=state.cwd,
            env_fallback=state.env_delta,
        )
        from sandbox.terminal import TerminalState

        self.update_terminal_state(TerminalState(cwd=new_cwd, env_delta=env_map))

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
            first = self._execute_once(command, timeout)
        except Exception as e:
            if not self._looks_like_infra_error(str(e)):
                raise
            self._recover_infra()
            return self._execute_once(command, timeout)

        if first.exit_code != 0 and self._looks_like_infra_error(first.stderr or first.stdout):
            self._recover_infra()
            return self._execute_once(command, timeout)

        return first

    async def close(self) -> None:
        """No-op for remote runtime - instance lifecycle managed by lease."""
        pass


class DaytonaSessionRuntime(_RemoteRuntimeBase):
    """Daytona runtime using native process session API (persistent shell semantics)."""

    def __init__(self, terminal: AbstractTerminal, lease: SandboxLease, provider: SandboxProvider):
        super().__init__(terminal, lease, provider)
        self._session_lock = asyncio.Lock()
        self._session_id = f"leon-term-{terminal.terminal_id[-12:]}"
        self._bound_instance_id: str | None = None
        self._hydrated = False
        self._baseline_env: dict[str, str] | None = None

    @staticmethod
    def _normalize_output(resp) -> str:
        stdout = getattr(resp, "stdout", None) or ""
        stderr = getattr(resp, "stderr", None) or ""
        output = getattr(resp, "output", None)
        if output:
            return _sanitize_shell_output(output)
        if stderr:
            merged = f"{stdout}\n{stderr}".strip() if stdout else stderr
            return _sanitize_shell_output(merged)
        return _sanitize_shell_output(stdout)

    def _session_execute_sync(self, sandbox, command: str, timeout_ms: int):
        from daytona_sdk.common.process import SessionExecuteRequest

        timeout_sec = max(1, timeout_ms // 1000)
        return sandbox.process.execute_session_command(
            self._session_id,
            SessionExecuteRequest(command=command),
            timeout=timeout_sec,
        )

    def _ensure_session_sync(self, timeout_ms: int):
        instance = self.lease.ensure_active_instance(self.provider)
        if self._bound_instance_id != instance.instance_id:
            self._bound_instance_id = instance.instance_id
            self._hydrated = False
            self._baseline_env = None

        sandbox = self._provider_sandbox(instance.instance_id)
        if self._hydrated:
            return sandbox

        try:
            sandbox.process.create_session(self._session_id)
        except Exception as exc:
            if "already exists" not in str(exc).lower():
                raise

        state = self.terminal.get_state()
        init_parts = [f"cd {shlex.quote(state.cwd)} || exit 1"]
        init_parts.extend(f"export {k}={shlex.quote(v)}" for k, v in state.env_delta.items())
        init_command = "\n".join(part for part in init_parts if part)
        if init_command:
            init_resp = self._session_execute_sync(sandbox, init_command, timeout_ms)
            init_exit = getattr(init_resp, "exit_code", 0) or 0
            if init_exit != 0:
                raise RuntimeError(f"Daytona session hydrate failed (exit={init_exit}): {self._normalize_output(init_resp)}")

        baseline_resp = self._session_execute_sync(sandbox, "env", timeout_ms)
        self._baseline_env = _parse_env_output(self._normalize_output(baseline_resp))
        self._hydrated = True
        return sandbox

    def _execute_once_sync(self, command: str, timeout: float | None = None) -> ExecuteResult:
        timeout_ms = int(timeout * 1000) if timeout else 30000
        sandbox = self._ensure_session_sync(timeout_ms)
        state = self.terminal.get_state()

        resp = self._session_execute_sync(sandbox, command, timeout_ms)
        stdout = self._normalize_output(resp)
        exit_code = getattr(resp, "exit_code", 0) or 0

        start_marker = f"__LEON_STATE_START_{uuid.uuid4().hex[:8]}__"
        end_marker = f"__LEON_STATE_END_{uuid.uuid4().hex[:8]}__"
        snapshot_resp = self._session_execute_sync(
            sandbox,
            "\n".join([f"echo {shlex.quote(start_marker)}", "pwd", "env", f"echo {shlex.quote(end_marker)}"]),
            timeout_ms,
        )
        snapshot_raw = self._normalize_output(snapshot_resp)
        new_cwd, env_map, _ = _extract_state_from_output(
            snapshot_raw,
            start_marker,
            end_marker,
            cwd_fallback=state.cwd,
            env_fallback=state.env_delta,
        )
        baseline_env = self._baseline_env or {}
        persisted_keys = set(state.env_delta.keys())
        env_delta = {k: v for k, v in env_map.items() if baseline_env.get(k) != v or k in persisted_keys}
        from sandbox.terminal import TerminalState

        self.update_terminal_state(TerminalState(cwd=new_cwd, env_delta=env_delta))
        return ExecuteResult(exit_code=exit_code, stdout=stdout, stderr="")

    async def execute(self, command: str, timeout: float | None = None) -> ExecuteResult:
        async with self._session_lock:
            try:
                first = await asyncio.to_thread(self._execute_once_sync, command, timeout)
            except Exception as exc:
                if not self._looks_like_infra_error(str(exc)):
                    return ExecuteResult(exit_code=1, stdout="", stderr=f"Error: {exc}")
                self._recover_infra()
                self._hydrated = False
                try:
                    return await asyncio.to_thread(self._execute_once_sync, command, timeout)
                except Exception as retry_exc:
                    return ExecuteResult(exit_code=1, stdout="", stderr=f"Error: {retry_exc}")

            if first.exit_code != 0 and self._looks_like_infra_error(first.stderr or first.stdout):
                self._recover_infra()
                self._hydrated = False
                try:
                    return await asyncio.to_thread(self._execute_once_sync, command, timeout)
                except Exception as retry_exc:
                    return ExecuteResult(exit_code=1, stdout="", stderr=f"Error: {retry_exc}")
            return first

    async def close(self) -> None:
        # Session belongs to sandbox instance lifecycle; explicit close optional.
        self._hydrated = False


class E2BPtyRuntime(_RemoteRuntimeBase):
    """E2B runtime using native SDK PTY handle for persistent shell."""

    def __init__(self, terminal: AbstractTerminal, lease: SandboxLease, provider: SandboxProvider):
        super().__init__(terminal, lease, provider)
        self._session_lock = asyncio.Lock()
        self._bound_instance_id: str | None = None
        self._pty_pid: int | None = None
        self._baseline_env: dict[str, str] | None = None

    @staticmethod
    def _extract_marker_exit(raw: str, marker: str) -> tuple[str, int]:
        exit_code = 0
        cleaned_lines: list[str] = []
        marker_re = re.compile(rf"{re.escape(marker)}\s+(-?\d+)")
        for line in raw.splitlines():
            m = marker_re.search(line)
            if m:
                exit_code = int(m.group(1))
                continue
            cleaned_lines.append(line)
        return _sanitize_shell_output("\n".join(cleaned_lines).strip()), exit_code

    def _run_pty_command_sync(
        self,
        sandbox,
        pid: int,
        command: str,
        timeout: float | None,
    ) -> tuple[str, str, int]:
        marker = f"__LEON_PTY_END_{uuid.uuid4().hex[:8]}__"
        payload = f"{command}\nprintf '\\n{marker} %s\\n' $?\n"
        handle = sandbox.pty.connect(pid, timeout=timeout or 60)
        started = time.monotonic()
        raw = bytearray()
        try:
            sandbox.pty.send_stdin(pid, payload.encode("utf-8"))
            for _, _, pty_data in handle:
                if pty_data:
                    raw.extend(pty_data)
                    decoded = raw.decode("utf-8", errors="replace")
                    if marker in decoded:
                        cleaned, exit_code = self._extract_marker_exit(decoded, marker)
                        return cleaned, "", exit_code
                if timeout and time.monotonic() - started > timeout:
                    raise TimeoutError(f"Command timed out after {timeout}s")
            raise RuntimeError("PTY stream closed before marker")
        finally:
            handle.disconnect()

    def _ensure_shell_sync(self, timeout: float | None) -> tuple[object, int]:
        instance = self.lease.ensure_active_instance(self.provider)
        if self._bound_instance_id != instance.instance_id:
            self._bound_instance_id = instance.instance_id
            self._pty_pid = None
            self._baseline_env = None

        sandbox = self._provider_sandbox(instance.instance_id)

        if self._pty_pid is not None:
            try:
                processes = sandbox.commands.list()
                if any(getattr(proc, "pid", None) == self._pty_pid for proc in processes):
                    return sandbox, self._pty_pid
            except Exception:
                self._pty_pid = None

        from e2b.sandbox.commands.command_handle import PtySize

        state = self.terminal.get_state()
        handle = sandbox.pty.create(
            size=PtySize(rows=32, cols=120),
            cwd=state.cwd,
            timeout=0,
        )
        self._pty_pid = handle.pid
        handle.disconnect()
        self._run_pty_command_sync(sandbox, self._pty_pid, "export PS1=''; stty -echo", timeout)

        if state.env_delta:
            exports = "\n".join(f"export {k}={shlex.quote(v)}" for k, v in state.env_delta.items())
            if exports:
                self._run_pty_command_sync(sandbox, self._pty_pid, exports, timeout)

        baseline_out, _, _ = self._run_pty_command_sync(sandbox, self._pty_pid, "env", timeout)
        self._baseline_env = _parse_env_output(baseline_out)
        return sandbox, self._pty_pid

    def _execute_once_sync(self, command: str, timeout: float | None = None) -> ExecuteResult:
        sandbox, pid = self._ensure_shell_sync(timeout)
        state = self.terminal.get_state()
        stdout, stderr, exit_code = self._run_pty_command_sync(sandbox, pid, command, timeout)

        start_marker = f"__LEON_STATE_START_{uuid.uuid4().hex[:8]}__"
        end_marker = f"__LEON_STATE_END_{uuid.uuid4().hex[:8]}__"
        snapshot_out, _, _ = self._run_pty_command_sync(
            sandbox,
            pid,
            "\n".join([f"echo {shlex.quote(start_marker)}", "pwd", "env", f"echo {shlex.quote(end_marker)}"]),
            timeout,
        )
        new_cwd, env_map, _ = _extract_state_from_output(
            snapshot_out,
            start_marker,
            end_marker,
            cwd_fallback=state.cwd,
            env_fallback=state.env_delta,
        )
        baseline_env = self._baseline_env or {}
        persisted_keys = set(state.env_delta.keys())
        env_delta = {k: v for k, v in env_map.items() if baseline_env.get(k) != v or k in persisted_keys}
        from sandbox.terminal import TerminalState

        self.update_terminal_state(TerminalState(cwd=new_cwd, env_delta=env_delta))
        return ExecuteResult(exit_code=exit_code, stdout=stdout, stderr=stderr)

    async def execute(self, command: str, timeout: float | None = None) -> ExecuteResult:
        async with self._session_lock:
            try:
                return await asyncio.to_thread(self._execute_once_sync, command, timeout)
            except TimeoutError:
                return ExecuteResult(exit_code=-1, stdout="", stderr=f"Command timed out after {timeout}s", timed_out=True)
            except Exception as exc:
                if self._looks_like_infra_error(str(exc)):
                    self._recover_infra()
                    self._pty_pid = None
                    try:
                        return await asyncio.to_thread(self._execute_once_sync, command, timeout)
                    except Exception as retry_exc:
                        return ExecuteResult(exit_code=1, stdout="", stderr=f"Error: {retry_exc}")
                return ExecuteResult(exit_code=1, stdout="", stderr=f"Error: {exc}")

    async def close(self) -> None:
        if self._pty_pid is None or self._bound_instance_id is None:
            return
        pid = self._pty_pid
        instance_id = self._bound_instance_id
        self._pty_pid = None
        try:
            sandbox = await asyncio.to_thread(self._provider_sandbox, instance_id)
            await asyncio.to_thread(sandbox.pty.kill, pid)
        except Exception:
            pass


def create_runtime(
    provider: SandboxProvider,
    terminal: AbstractTerminal,
    lease: SandboxLease,
) -> PhysicalTerminalRuntime:
    capability = provider.get_capability()
    runtime_kind = str(getattr(capability, "runtime_kind", "remote"))
    if runtime_kind == "local":
        return LocalPersistentShellRuntime(terminal, lease)
    if runtime_kind == "daytona_session":
        return DaytonaSessionRuntime(terminal, lease, provider)
    if runtime_kind == "e2b_pty":
        return E2BPtyRuntime(terminal, lease, provider)
    return RemoteWrappedRuntime(terminal, lease, provider)
