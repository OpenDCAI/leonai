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
import json
import os
import pty
import re
import select
import shlex
import sqlite3
import subprocess
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sandbox.lease import SandboxLease
    from sandbox.provider import SandboxProvider
    from sandbox.terminal import AbstractTerminal, TerminalState

from sandbox.interfaces.executor import AsyncCommand, ExecuteResult
from sandbox.shell_output import normalize_pty_result

ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
VALID_STATE_PERSIST_MODES = {"always", "boundary"}


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
        state_persist_mode: str = "always",
    ):
        if state_persist_mode not in VALID_STATE_PERSIST_MODES:
            raise RuntimeError(
                f"Invalid state_persist_mode '{state_persist_mode}'. "
                f"Expected one of {sorted(VALID_STATE_PERSIST_MODES)}"
            )
        self.terminal = terminal
        self.lease = lease
        self.state_persist_mode = state_persist_mode
        self.runtime_id = f"runtime-{uuid.uuid4().hex[:12]}"
        self.chat_session_id: str | None = None
        self._commands: dict[str, AsyncCommand] = {}
        self._tasks: dict[str, asyncio.Task[ExecuteResult]] = {}
        self._stream_flush_interval_sec = 0.2
        self._last_stream_flush_at: dict[str, float] = {}

    def bind_session(self, session_id: str) -> None:
        self.chat_session_id = session_id

    def _db_path(self) -> Path:
        db_path = getattr(self.terminal, "db_path", None)
        if not db_path:
            raise RuntimeError("Terminal db_path is required for command registry")
        return Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path()), timeout=30)
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _upsert_command_row(
        self,
        *,
        command_id: str,
        command_line: str,
        cwd: str,
        status: str,
        stdout: str = "",
        stderr: str = "",
        exit_code: int | None = None,
    ) -> None:
        now = datetime.now().isoformat()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT command_id, created_at FROM terminal_commands WHERE command_id = ?",
                (command_id,),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE terminal_commands
                    SET status = ?, stdout = ?, stderr = ?, exit_code = ?, updated_at = ?,
                        finished_at = CASE WHEN ? IN ('done', 'cancelled', 'failed') THEN ? ELSE finished_at END
                    WHERE command_id = ?
                    """,
                    (status, stdout, stderr, exit_code, now, status, now, command_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO terminal_commands (
                        command_id, terminal_id, chat_session_id, command_line, cwd, status,
                        stdout, stderr, exit_code, created_at, updated_at, finished_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        command_id,
                        self.terminal.terminal_id,
                        self.chat_session_id,
                        command_line,
                        cwd,
                        status,
                        stdout,
                        stderr,
                        exit_code,
                        now,
                        now,
                        now if status in {"done", "cancelled", "failed"} else None,
                    ),
                )
            conn.commit()

    def _flush_running_output_if_needed(self, command_id: str, *, force: bool = False) -> None:
        async_cmd = self._commands.get(command_id)
        if async_cmd is None:
            return
        now = time.monotonic()
        last = self._last_stream_flush_at.get(command_id, 0.0)
        if not force and now - last < self._stream_flush_interval_sec:
            return
        self._last_stream_flush_at[command_id] = now
        self._upsert_command_row(
            command_id=command_id,
            command_line=async_cmd.command_line,
            cwd=async_cmd.cwd,
            status="running",
            stdout="".join(async_cmd.stdout_buffer),
            stderr="".join(async_cmd.stderr_buffer),
        )

    def _load_command_from_db(self, command_id: str) -> AsyncCommand | None:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT command_id, command_line, cwd, status, stdout, stderr, exit_code
                FROM terminal_commands
                WHERE command_id = ? AND terminal_id = ?
                """,
                (command_id, self.terminal.terminal_id),
            ).fetchone()
        if not row:
            return None
        async_cmd = AsyncCommand(
            command_id=row["command_id"],
            command_line=row["command_line"],
            cwd=row["cwd"],
            stdout_buffer=[row["stdout"] or ""],
            stderr_buffer=[row["stderr"] or ""],
            exit_code=row["exit_code"],
            done=row["status"] in {"done", "cancelled", "failed"},
        )
        self._commands[command_id] = async_cmd
        return async_cmd

    async def start_command(self, command: str, cwd: str) -> AsyncCommand:
        command_id = f"cmd_{uuid.uuid4().hex[:12]}"
        async_cmd = AsyncCommand(
            command_id=command_id,
            command_line=command,
            cwd=cwd,
        )
        self._commands[command_id] = async_cmd
        self._upsert_command_row(
            command_id=command_id,
            command_line=command,
            cwd=cwd,
            status="running",
        )

        async def _run() -> ExecuteResult:
            def _append_stdout(chunk: str) -> None:
                if chunk:
                    async_cmd.stdout_buffer.append(chunk)
                    self._flush_running_output_if_needed(command_id)

            try:
                result = await self._execute_background_command(command, timeout=None, on_stdout_chunk=_append_stdout)
                status = "done"
            except Exception as exc:
                result = ExecuteResult(exit_code=1, stdout="", stderr=f"Error: {exc}")
                status = "failed"
            async_cmd.stdout_buffer = [result.stdout]
            async_cmd.stderr_buffer = [result.stderr]
            async_cmd.exit_code = result.exit_code
            async_cmd.done = True
            self._upsert_command_row(
                command_id=command_id,
                command_line=command,
                cwd=cwd,
                status=status,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.exit_code,
            )
            self._last_stream_flush_at.pop(command_id, None)
            return result

        self._tasks[command_id] = asyncio.create_task(_run())
        return async_cmd

    async def _execute_background_command(
        self,
        command: str,
        timeout: float | None,
        on_stdout_chunk: Callable[[str], None] | None = None,
    ) -> ExecuteResult:
        return await self.execute(command, timeout=timeout)

    async def get_command(self, command_id: str) -> AsyncCommand | None:
        cmd = self._commands.get(command_id)
        if cmd:
            if not cmd.done and command_id not in self._tasks:
                # @@@cross-runtime-status-source - If this runtime didn't start the task, trust DB row instead of stale memory.
                refreshed = self._load_command_from_db(command_id)
                return refreshed or cmd
            return cmd
        return self._load_command_from_db(command_id)

    async def wait_for_command(self, command_id: str, timeout: float | None = None) -> ExecuteResult | None:
        async_cmd = await self.get_command(command_id)
        if async_cmd is None:
            return None
        task = self._tasks.get(command_id)
        if task is None and not async_cmd.done:
            deadline = time.monotonic() + timeout if timeout is not None else None
            while not async_cmd.done:
                if deadline is not None and time.monotonic() > deadline:
                    return ExecuteResult(
                        exit_code=-1,
                        stdout="".join(async_cmd.stdout_buffer),
                        stderr="".join(async_cmd.stderr_buffer),
                        timed_out=True,
                        command_id=command_id,
                    )
                await asyncio.sleep(0.1)
                refreshed = self._load_command_from_db(command_id)
                if refreshed is None:
                    return None
                async_cmd = refreshed
        if task is not None and not task.done():
            try:
                if timeout is None:
                    await task
                else:
                    await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
            except TimeoutError:
                return ExecuteResult(
                    exit_code=-1,
                    stdout="".join(async_cmd.stdout_buffer),
                    stderr="".join(async_cmd.stderr_buffer),
                    timed_out=True,
                    command_id=command_id,
                )
            except asyncio.CancelledError:
                return ExecuteResult(
                    exit_code=130,
                    stdout="".join(async_cmd.stdout_buffer),
                    stderr="Command cancelled",
                    command_id=command_id,
                )
        return ExecuteResult(
            exit_code=async_cmd.exit_code or 0,
            stdout="".join(async_cmd.stdout_buffer),
            stderr="".join(async_cmd.stderr_buffer),
            command_id=command_id,
        )

    async def cancel_command(self, command_id: str) -> bool:
        task = self._tasks.get(command_id)
        cmd = await self.get_command(command_id)
        if not task or not cmd:
            return False
        if task.done():
            return False
        task.cancel()
        cmd.done = True
        cmd.exit_code = 130
        cmd.stderr_buffer = ["Command cancelled"]
        self._upsert_command_row(
            command_id=command_id,
            command_line=cmd.command_line,
            cwd=cmd.cwd,
            status="cancelled",
            stdout="".join(cmd.stdout_buffer),
            stderr="Command cancelled",
            exit_code=130,
        )
        return True

    def store_completed_result(self, command_id: str, command_line: str, cwd: str, result: ExecuteResult) -> None:
        cmd = AsyncCommand(
            command_id=command_id,
            command_line=command_line,
            cwd=cwd,
            stdout_buffer=[result.stdout],
            stderr_buffer=[result.stderr],
            exit_code=result.exit_code,
            done=True,
        )
        self._commands[command_id] = cmd
        self._upsert_command_row(
            command_id=command_id,
            command_line=command_line,
            cwd=cwd,
            status="done",
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
        )
        self._last_stream_flush_at.pop(command_id, None)

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

    def sync_terminal_state_snapshot(self, timeout: float | None = None) -> None:
        raise RuntimeError(f"{self.__class__.__name__} does not implement sync_terminal_state_snapshot()")


def _parse_env_output(raw: str) -> dict[str, str]:
    env_map: dict[str, str] = {}
    for line in raw.replace("\r", "").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not ENV_NAME_RE.match(key):
            continue
        env_map[key] = value
    return env_map


def _sanitize_shell_output(raw: str) -> str:
    cleaned = raw.replace("\r", "").replace("\x01\x01\x01", "").replace("\x02\x02\x02", "")
    cleaned = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", cleaned)
    cleaned = re.sub(r"\x1B\][^\x07]*\x07", "", cleaned)
    while True:
        next_cleaned = re.sub(r"[^\n]\x08", "", cleaned)
        if next_cleaned == cleaned:
            break
        cleaned = next_cleaned
    cleaned = cleaned.replace("\x08", "")
    cleaned = "".join(ch for ch in cleaned if ch in "\n\t" or 32 <= ord(ch))
    return cleaned


def _normalize_pty_result(output: str, command: str | None = None) -> str:
    return normalize_pty_result(output, command)


def _extract_state_from_output(
    raw_output: str,
    start_marker: str,
    end_marker: str,
    *,
    cwd_fallback: str,
    env_fallback: dict[str, str],
) -> tuple[str, dict[str, str], str]:
    pattern = re.compile(rf"{re.escape(start_marker)}(.*?){re.escape(end_marker)}", re.S)
    matches = list(pattern.finditer(raw_output))
    if not matches:
        raise RuntimeError("Failed to parse terminal state: state markers not found")

    match = matches[-1]
    pre_state = raw_output[: match.start()]
    state_blob = match.group(1)
    post_state = raw_output[match.end() :]
    state_lines = [_sanitize_shell_output(line).strip() for line in state_blob.splitlines()]
    state_lines = [line for line in state_lines if line]

    new_cwd = ""
    parsed_env: dict[str, str] = {}
    for line in state_lines:
        if "=" in line:
            key, value = line.split("=", 1)
            if ENV_NAME_RE.match(key):
                parsed_env[key] = value
            continue
        if os.path.isabs(line):
            new_cwd = line

    if not new_cwd:
        raise RuntimeError("Failed to parse terminal state: cwd not found in state snapshot")
    if not parsed_env:
        raise RuntimeError("Failed to parse terminal state: env snapshot is empty")

    cleaned_output = _sanitize_shell_output(pre_state + post_state).strip()
    return new_cwd, parsed_env, cleaned_output


class _SubprocessPtySession:
    def __init__(self, command: list[str], cwd: str | None = None):
        self.command = command
        self.cwd = cwd
        self._master_fd: int | None = None
        self._proc: subprocess.Popen[bytes] | None = None

    @property
    def process(self) -> subprocess.Popen[bytes] | None:
        return self._proc

    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    @staticmethod
    def _extract_marker_exit(raw: str, marker: str, command: str | None = None) -> tuple[str, int]:
        exit_code = 0
        cleaned_lines: list[str] = []
        marker_re = re.compile(rf"{re.escape(marker)}\s+(-?\d+)")
        for line in raw.replace("\r", "").splitlines():
            m = marker_re.search(line)
            if m:
                exit_code = int(m.group(1))
                continue
            cleaned_lines.append(line)
        cleaned = _sanitize_shell_output("\n".join(cleaned_lines).strip())
        return _normalize_pty_result(cleaned, command), exit_code

    def start(self) -> None:
        if self.is_alive():
            return
        master_fd, slave_fd = pty.openpty()
        try:
            self._proc = subprocess.Popen(
                self.command,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=self.cwd,
                close_fds=True,
            )
        finally:
            os.close(slave_fd)
        self._master_fd = master_fd

    def run(
        self,
        command: str,
        timeout: float | None,
        on_stdout_chunk: Callable[[str], None] | None = None,
    ) -> tuple[str, str, int]:
        if not self.is_alive() or self._master_fd is None:
            raise RuntimeError("PTY session is not running")

        marker = f"__LEON_PTY_END_{uuid.uuid4().hex[:8]}__"
        marker_done_re = re.compile(rf"{re.escape(marker)}\s+-?\d+")
        payload = f"{command}\nprintf '\\n{marker} %s\\n' $?\n"
        os.write(self._master_fd, payload.encode("utf-8"))

        raw = bytearray()
        emitted_raw_len = 0
        deadline = time.monotonic() + timeout if timeout else None
        while True:
            if deadline is not None and time.monotonic() > deadline:
                raise TimeoutError(f"Command timed out after {timeout}s")
            wait_sec = 0.1 if deadline is None else max(0.0, min(0.1, deadline - time.monotonic()))
            readable, _, _ = select.select([self._master_fd], [], [], wait_sec)
            if not readable:
                continue
            chunk = os.read(self._master_fd, 4096)
            if not chunk:
                raise RuntimeError("PTY stream closed unexpectedly")
            raw.extend(chunk)
            decoded = raw.decode("utf-8", errors="replace")
            if marker_done_re.search(decoded):
                cleaned, exit_code = self._extract_marker_exit(decoded, marker, command)
                return cleaned, "", exit_code
            if on_stdout_chunk is not None:
                if len(decoded) > emitted_raw_len:
                    delta_raw = decoded[emitted_raw_len:]
                    emitted_raw_len = len(decoded)
                    delta = _sanitize_shell_output(delta_raw)
                    if delta:
                        on_stdout_chunk(delta)

    def close(self) -> None:
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None

        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5.0)
            except Exception:
                self._proc.kill()
                self._proc.wait(timeout=5.0)


class LocalPersistentShellRuntime(PhysicalTerminalRuntime):
    """Local persistent shell runtime (for local provider).

    Uses a persistent PTY-backed shell session.
    """

    def __init__(
        self,
        terminal: AbstractTerminal,
        lease: SandboxLease,
        shell_command: tuple[str, ...] = ("/bin/bash",),
        state_persist_mode: str = "always",
    ):
        super().__init__(terminal, lease, state_persist_mode=state_persist_mode)
        self.shell_command = shell_command
        self._pty_session: _SubprocessPtySession | None = None
        self._session: subprocess.Popen[bytes] | None = None
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
        if self.state_persist_mode == "always":
            self._sync_terminal_state_snapshot_sync(timeout, state)

        return ExecuteResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            timed_out=False,
        )

    def _sync_terminal_state_snapshot_sync(self, timeout: float | None, state=None) -> None:
        if self._pty_session is None:
            return
        if not self._pty_session.is_alive():
            raise RuntimeError("Local PTY session is not running; cannot snapshot terminal state")
        current_state = state or self.terminal.get_state()
        pwd_stdout, _, _ = self._pty_session.run("pwd", timeout)
        env_stdout, _, _ = self._pty_session.run("env", timeout)
        pwd_lines = [line.strip() for line in pwd_stdout.splitlines() if line.strip()]
        new_cwd = pwd_lines[-1] if pwd_lines else current_state.cwd
        env_map = _parse_env_output(env_stdout)
        baseline_env = self._baseline_env or {}
        persisted_keys = set(current_state.env_delta.keys())
        env_delta = {k: v for k, v in env_map.items() if baseline_env.get(k) != v or k in persisted_keys}
        if new_cwd:
            from sandbox.terminal import TerminalState

            self.update_terminal_state(TerminalState(cwd=new_cwd, env_delta=env_delta))

    def sync_terminal_state_snapshot(self, timeout: float | None = None) -> None:
        self._sync_terminal_state_snapshot_sync(timeout)

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

    async def execute(self, command: str, timeout: float | None = None) -> ExecuteResult:
        """Execute command in local shell."""
        return await self._execute_background_command(command, timeout=timeout)

    async def close(self) -> None:
        """Close the shell session."""
        if self._pty_session:
            await asyncio.to_thread(self._pty_session.close)
            self._session = self._pty_session.process


class _RemoteRuntimeBase(PhysicalTerminalRuntime):
    def __init__(
        self,
        terminal: AbstractTerminal,
        lease: SandboxLease,
        provider: SandboxProvider,
        state_persist_mode: str = "always",
    ):
        super().__init__(terminal, lease, state_persist_mode=state_persist_mode)
        self.provider = provider

    @staticmethod
    def _looks_like_infra_error(text: str) -> bool:
        message = text.lower()
        markers = (
            "not found",
            "no such session",
            "session does not exist",
            "failed to create pty session",
            "no ip address found",
            "is the sandbox started",
            "is paused",
            "stopped",
            "connection",
            # Websocket/PTY transport failures (sandbox may still be started; handle is stale).
            "websocket",
            "close frame",
            "no close frame",
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
        state_persist_mode: str = "always",
    ):
        super().__init__(terminal, lease, provider, state_persist_mode=state_persist_mode)

    def _sync_terminal_state_snapshot_sync(self, timeout: float | None = None) -> None:
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
                f"echo {shlex.quote(start_marker)}",
                "pwd",
                "env",
                f"echo {shlex.quote(end_marker)}",
            ]
            if part
        )
        result = self.provider.execute(
            instance.instance_id,
            wrapped,
            timeout_ms=timeout_ms,
            cwd=state.cwd,
        )
        if result.error:
            raise RuntimeError(result.error)
        if result.exit_code != 0:
            raise RuntimeError(f"Remote snapshot failed with exit code {result.exit_code}")
        new_cwd, env_map, _ = _extract_state_from_output(
            result.output or "",
            start_marker,
            end_marker,
            cwd_fallback=state.cwd,
            env_fallback=state.env_delta,
        )
        from sandbox.terminal import TerminalState

        self.update_terminal_state(TerminalState(cwd=new_cwd, env_delta=env_map))

    def sync_terminal_state_snapshot(self, timeout: float | None = None) -> None:
        self._sync_terminal_state_snapshot_sync(timeout)

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
        if self.state_persist_mode == "always":
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
    """Daytona runtime using native PTY session API (persistent terminal semantics)."""

    def __init__(
        self,
        terminal: AbstractTerminal,
        lease: SandboxLease,
        provider: SandboxProvider,
        state_persist_mode: str = "always",
    ):
        super().__init__(terminal, lease, provider, state_persist_mode=state_persist_mode)
        self._session_lock = asyncio.Lock()
        self._pty_session_id = f"leon-pty-{terminal.terminal_id[-12:]}"
        self._bound_instance_id: str | None = None
        self._pty_handle = None
        self._hydrated = False
        self._baseline_env: dict[str, str] | None = None
        self._snapshot_task: asyncio.Task[None] | None = None
        self._snapshot_generation = 0
        self._snapshot_error: str | None = None

    def _sanitize_terminal_snapshot(self) -> tuple[str, dict[str, str]]:
        state = self.terminal.get_state()
        cleaned_env = {k: v for k, v in state.env_delta.items() if ENV_NAME_RE.match(k)}
        cleaned_cwd = state.cwd
        if not os.path.isabs(cleaned_cwd):
            pwd_hint = cleaned_env.get("PWD")
            if isinstance(pwd_hint, str) and os.path.isabs(pwd_hint):
                cleaned_cwd = pwd_hint
            else:
                raise RuntimeError(
                    f"Invalid terminal cwd snapshot for terminal {self.terminal.terminal_id}: {state.cwd!r}"
                )
        if cleaned_cwd != state.cwd or cleaned_env != state.env_delta:
            from sandbox.terminal import TerminalState

            # @@@daytona-state-sanitize - Legacy prompt noise can corrupt persisted cwd/env_delta and break PTY creation.
            # Normalize once here so new abstract terminals inherit only valid state.
            self.update_terminal_state(TerminalState(cwd=cleaned_cwd, env_delta=cleaned_env))
        return cleaned_cwd, cleaned_env

    def _close_shell_sync(self) -> None:
        if self._pty_handle is not None:
            try:
                self._pty_handle.disconnect()
            except Exception:
                pass
        self._pty_handle = None
        self._hydrated = False
        if not self._bound_instance_id:
            return
        try:
            sandbox = self._provider_sandbox(self._bound_instance_id)
            sandbox.process.kill_pty_session(self._pty_session_id)
        except Exception:
            pass

    @staticmethod
    def _read_pty_chunk_sync(handle, wait_sec: float) -> bytes | None:
        ws = getattr(handle, "_ws", None)
        if ws is None:
            raise RuntimeError("Daytona PTY websocket unavailable")
        try:
            message = ws.recv(timeout=wait_sec)
        except TimeoutError:
            return None
        except Exception as exc:
            raise RuntimeError(f"Daytona PTY read failed: {exc}") from exc

        if isinstance(message, bytes):
            return message

        text = str(message)
        try:
            control = json.loads(text)
        except Exception:
            return text.encode("utf-8", errors="replace")

        if isinstance(control, dict) and control.get("type") == "control":
            status = str(control.get("status") or "")
            if status == "error":
                error = str(control.get("error") or "unknown")
                raise RuntimeError(f"Daytona PTY control error: {error}")
            return b""

        return text.encode("utf-8", errors="replace")

    def _run_pty_command_sync(
        self,
        handle,
        command: str,
        timeout: float | None,
        on_stdout_chunk: Callable[[str], None] | None = None,
    ) -> tuple[str, str, int]:
        marker = f"__LEON_PTY_END_{uuid.uuid4().hex[:8]}__"
        marker_done_re = re.compile(rf"{re.escape(marker)}\s+-?\d+")
        payload = f"{command}\nprintf '\\n{marker} %s\\n' $?\n"
        handle.send_input(payload)

        raw = bytearray()
        emitted_raw_len = 0
        deadline = time.monotonic() + timeout if timeout else None
        while True:
            if deadline is not None and time.monotonic() > deadline:
                raise TimeoutError(f"Command timed out after {timeout}s")
            wait_sec = 0.1 if deadline is None else max(0.0, min(0.1, deadline - time.monotonic()))
            chunk = self._read_pty_chunk_sync(handle, wait_sec)
            if chunk is None:
                continue
            if not chunk:
                continue
            raw.extend(chunk)
            decoded = raw.decode("utf-8", errors="replace")
            if marker_done_re.search(decoded):
                cleaned, exit_code = _SubprocessPtySession._extract_marker_exit(decoded, marker, command)
                return cleaned, "", exit_code
            if on_stdout_chunk is not None:
                if len(decoded) > emitted_raw_len:
                    delta_raw = decoded[emitted_raw_len:]
                    emitted_raw_len = len(decoded)
                    delta = _sanitize_shell_output(delta_raw)
                    if delta:
                        on_stdout_chunk(delta)

    def _ensure_session_sync(self, timeout: float | None):
        instance = self.lease.ensure_active_instance(self.provider)
        if self._bound_instance_id != instance.instance_id:
            self._close_shell_sync()
            self._bound_instance_id = instance.instance_id
            self._baseline_env = None
            self._hydrated = False

        sandbox = self._provider_sandbox(instance.instance_id)
        effective_cwd, effective_env = self._sanitize_terminal_snapshot()
        if self._pty_handle is None:
            try:
                handle = sandbox.process.connect_pty_session(self._pty_session_id)
                handle.wait_for_connection(timeout=10.0)
            except Exception:
                try:
                    from daytona_sdk.common.pty import PtySize
                except Exception:
                    class PtySize:  # type: ignore[no-redef]
                        def __init__(self, *, rows: int, cols: int):
                            self.rows = rows
                            self.cols = cols

                try:
                    handle = sandbox.process.create_pty_session(
                        id=self._pty_session_id,
                        cwd=effective_cwd,
                        envs=None,
                        pty_size=PtySize(rows=32, cols=120),
                    )
                except Exception as create_exc:
                    message = str(create_exc)
                    if "/usr/bin/zsh" in message:
                        # @@@daytona-shell-fail-loud - Do not silently override provider shell selection.
                        # Surface explicit infra error so snapshot/image shell mismatch is fixed at source.
                        raise RuntimeError(
                            "Daytona PTY bootstrap failed: provider requested /usr/bin/zsh but it is missing "
                            "in the sandbox image. Fix provider snapshot/image shell config."
                        ) from create_exc
                    raise
            self._pty_handle = handle

        if not self._hydrated:
            _, _, shell_exit = self._run_pty_command_sync(self._pty_handle, "export PS1=''; stty -echo", timeout)
            if shell_exit != 0:
                raise RuntimeError(f"Daytona PTY shell normalization failed (exit={shell_exit})")
            init_parts = [f"cd {shlex.quote(effective_cwd)} || exit 1"]
            init_parts.extend(f"export {k}={shlex.quote(v)}" for k, v in effective_env.items())
            init_command = "\n".join(part for part in init_parts if part)
            if init_command:
                _, _, init_exit = self._run_pty_command_sync(self._pty_handle, init_command, timeout)
                if init_exit != 0:
                    raise RuntimeError(f"Daytona PTY hydrate failed (exit={init_exit})")

            baseline_out, _, _ = self._run_pty_command_sync(self._pty_handle, "env", timeout)
            self._baseline_env = _parse_env_output(baseline_out)
            self._hydrated = True
        return self._pty_handle

    def _execute_once_sync(
        self,
        command: str,
        timeout: float | None = None,
        on_stdout_chunk: Callable[[str], None] | None = None,
    ) -> ExecuteResult:
        handle = self._ensure_session_sync(timeout)
        stdout, _, exit_code = self._run_pty_command_sync(handle, command, timeout, on_stdout_chunk=on_stdout_chunk)
        return ExecuteResult(exit_code=exit_code, stdout=stdout, stderr="")

    def _sync_terminal_state_snapshot_sync(self, timeout: float | None = None) -> None:
        # Snapshot must be able to run after infra recovery (PTY re-created), so always ensure a handle.
        handle = self._ensure_session_sync(timeout)
        state = self.terminal.get_state()
        start_marker = f"__LEON_STATE_START_{uuid.uuid4().hex[:8]}__"
        end_marker = f"__LEON_STATE_END_{uuid.uuid4().hex[:8]}__"
        snapshot_out, _, _ = self._run_pty_command_sync(
            handle,
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

    async def _snapshot_state_async(self, generation: int, timeout: float | None) -> None:
        async with self._session_lock:
            if generation != self._snapshot_generation:
                return
            try:
                await asyncio.to_thread(self._sync_terminal_state_snapshot_sync, timeout)
            except Exception as exc:
                message = str(exc)
                if self._looks_like_infra_error(message):
                    # @@@daytona-snapshot-retry - Snapshot can fail due to stale PTY websocket even if sandbox is running.
                    # Refresh infra truth once, re-create PTY, and retry exactly once.
                    try:
                        self._recover_infra()
                        self._close_shell_sync()
                        await asyncio.to_thread(self._sync_terminal_state_snapshot_sync, timeout)
                        self._snapshot_error = None
                        return
                    except Exception as retry_exc:
                        self._snapshot_error = str(retry_exc)
                        return
                self._snapshot_error = message

    def _schedule_snapshot(self, generation: int, timeout: float | None) -> None:
        if self._snapshot_task and not self._snapshot_task.done():
            self._snapshot_task.cancel()
        self._snapshot_task = asyncio.create_task(self._snapshot_state_async(generation, timeout))

    def sync_terminal_state_snapshot(self, timeout: float | None = None) -> None:
        if self._pty_handle is None:
            return
        self._sync_terminal_state_snapshot_sync(timeout)

    async def _execute_background_command(
        self,
        command: str,
        timeout: float | None,
        on_stdout_chunk: Callable[[str], None] | None = None,
    ) -> ExecuteResult:
        async with self._session_lock:
            if self._snapshot_error:
                if self._looks_like_infra_error(self._snapshot_error):
                    # @@@daytona-snapshot-recover - Do not wedge the terminal forever on a transient snapshot failure.
                    # Attempt infra recovery once, then proceed (a fresh snapshot will be scheduled after this command).
                    try:
                        self._recover_infra()
                        self._close_shell_sync()
                        self._snapshot_error = None
                    except Exception as exc:
                        return ExecuteResult(
                            exit_code=1,
                            stdout="",
                            stderr=f"Error: snapshot failed: {exc}",
                        )
                else:
                    return ExecuteResult(
                        exit_code=1, stdout="", stderr=f"Error: snapshot failed: {self._snapshot_error}"
                    )
            try:
                first = await asyncio.to_thread(self._execute_once_sync, command, timeout, on_stdout_chunk)
            except TimeoutError:
                return ExecuteResult(
                    exit_code=-1, stdout="", stderr=f"Command timed out after {timeout}s", timed_out=True
                )
            except Exception as exc:
                if not self._looks_like_infra_error(str(exc)):
                    return ExecuteResult(exit_code=1, stdout="", stderr=f"Error: {exc}")
                self._recover_infra()
                self._close_shell_sync()
                try:
                    return await asyncio.to_thread(self._execute_once_sync, command, timeout, on_stdout_chunk)
                except Exception as retry_exc:
                    return ExecuteResult(exit_code=1, stdout="", stderr=f"Error: {retry_exc}")

            if first.exit_code != 0 and self._looks_like_infra_error(first.stderr or first.stdout):
                self._recover_infra()
                self._close_shell_sync()
                try:
                    return await asyncio.to_thread(self._execute_once_sync, command, timeout, on_stdout_chunk)
                except Exception as retry_exc:
                    return ExecuteResult(exit_code=1, stdout="", stderr=f"Error: {retry_exc}")

            if self.state_persist_mode == "always":
                self._snapshot_generation += 1
                generation = self._snapshot_generation
            else:
                generation = -1

        if self.state_persist_mode == "always":
            # @@@daytona-async-snapshot - state sync runs in background so command result streaming is not blocked.
            # @@@daytona-snapshot-timeout - Snapshot reads full env; don't inherit overly aggressive user timeouts.
            snapshot_timeout = None if timeout is None else max(float(timeout), 10.0)
            self._schedule_snapshot(generation, snapshot_timeout)
        return first

    async def execute(self, command: str, timeout: float | None = None) -> ExecuteResult:
        return await self._execute_background_command(command, timeout=timeout)

    async def close(self) -> None:
        if self._snapshot_task and not self._snapshot_task.done():
            self._snapshot_task.cancel()
            # @@@cross-loop-snapshot-close - Runtime.close may run on a different loop during manager cleanup.
            # Only await task cancellation when task belongs to the current running loop.
            try:
                current_loop = asyncio.get_running_loop()
            except RuntimeError:
                current_loop = None
            task_loop = self._snapshot_task.get_loop()
            if current_loop is task_loop:
                try:
                    await self._snapshot_task
                except asyncio.CancelledError:
                    pass
        self._snapshot_task = None
        await asyncio.to_thread(self._close_shell_sync)


class DockerPtyRuntime(_RemoteRuntimeBase):
    """Docker runtime using a persistent PTY shell inside container."""

    def __init__(
        self,
        terminal: AbstractTerminal,
        lease: SandboxLease,
        provider: SandboxProvider,
        state_persist_mode: str = "always",
    ):
        super().__init__(terminal, lease, provider, state_persist_mode=state_persist_mode)
        self._session_lock = asyncio.Lock()
        self._bound_instance_id: str | None = None
        self._pty_session: _SubprocessPtySession | None = None
        self._baseline_env: dict[str, str] | None = None

    def _close_shell_sync(self) -> None:
        if self._pty_session:
            self._pty_session.close()
        self._pty_session = None

    def _ensure_shell_sync(self, timeout: float | None) -> _SubprocessPtySession:
        instance = self.lease.ensure_active_instance(self.provider)
        if self._bound_instance_id != instance.instance_id:
            self._close_shell_sync()
            self._bound_instance_id = instance.instance_id
            self._baseline_env = None

        if self._pty_session and self._pty_session.is_alive():
            return self._pty_session

        state = self.terminal.get_state()
        self._pty_session = _SubprocessPtySession(["docker", "exec", "-it", instance.instance_id, "/bin/sh"])
        self._pty_session.start()
        self._pty_session.run("export PS1=''; stty -echo", timeout)
        self._pty_session.run(f"cd {shlex.quote(state.cwd)} || exit 1", timeout)
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
        session = self._ensure_shell_sync(timeout)
        stdout, stderr, exit_code = session.run(command, timeout, on_stdout_chunk=on_stdout_chunk)
        if self.state_persist_mode == "always":
            self._sync_terminal_state_snapshot_sync(timeout)
        return ExecuteResult(exit_code=exit_code, stdout=stdout, stderr=stderr)

    def _sync_terminal_state_snapshot_sync(self, timeout: float | None = None) -> None:
        if self._pty_session is None:
            return
        if not self._pty_session.is_alive():
            raise RuntimeError("Docker PTY session is not running; cannot snapshot terminal state")
        state = self.terminal.get_state()
        start_marker = f"__LEON_STATE_START_{uuid.uuid4().hex[:8]}__"
        end_marker = f"__LEON_STATE_END_{uuid.uuid4().hex[:8]}__"
        snapshot_cmd = "\n".join([f"echo {shlex.quote(start_marker)}", "pwd", "env", f"echo {shlex.quote(end_marker)}"])
        snapshot_out, _, _ = self._pty_session.run(snapshot_cmd, timeout)
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

    def sync_terminal_state_snapshot(self, timeout: float | None = None) -> None:
        self._sync_terminal_state_snapshot_sync(timeout)

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
                return ExecuteResult(
                    exit_code=-1, stdout="", stderr=f"Command timed out after {timeout}s", timed_out=True
                )
            except Exception as exc:
                if self._looks_like_infra_error(str(exc)):
                    self._recover_infra()
                    self._close_shell_sync()
                    try:
                        return await asyncio.to_thread(self._execute_once_sync, command, timeout, on_stdout_chunk)
                    except Exception as retry_exc:
                        return ExecuteResult(exit_code=1, stdout="", stderr=f"Error: {retry_exc}")
                return ExecuteResult(exit_code=1, stdout="", stderr=f"Error: {exc}")

    async def execute(self, command: str, timeout: float | None = None) -> ExecuteResult:
        return await self._execute_background_command(command, timeout=timeout)

    async def close(self) -> None:
        await asyncio.to_thread(self._close_shell_sync)


class E2BPtyRuntime(_RemoteRuntimeBase):
    """E2B runtime using native SDK PTY handle for persistent shell."""

    def __init__(
        self,
        terminal: AbstractTerminal,
        lease: SandboxLease,
        provider: SandboxProvider,
        state_persist_mode: str = "always",
    ):
        super().__init__(terminal, lease, provider, state_persist_mode=state_persist_mode)
        self._session_lock = asyncio.Lock()
        self._bound_instance_id: str | None = None
        self._pty_pid: int | None = None
        self._baseline_env: dict[str, str] | None = None

    @staticmethod
    def _extract_marker_exit(raw: str, marker: str, command: str | None = None) -> tuple[str, int]:
        exit_code = 0
        cleaned_lines: list[str] = []
        marker_re = re.compile(rf"{re.escape(marker)}\s+(-?\d+)")
        for line in raw.splitlines():
            m = marker_re.search(line)
            if m:
                exit_code = int(m.group(1))
                continue
            cleaned_lines.append(line)
        cleaned = _sanitize_shell_output("\n".join(cleaned_lines).strip())
        return _normalize_pty_result(cleaned, command), exit_code

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
                        cleaned, exit_code = self._extract_marker_exit(decoded, marker, command)
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
        stdout, stderr, exit_code = self._run_pty_command_sync(sandbox, pid, command, timeout)
        if self.state_persist_mode == "always":
            self._sync_terminal_state_snapshot_sync(timeout)
        return ExecuteResult(exit_code=exit_code, stdout=stdout, stderr=stderr)

    def _sync_terminal_state_snapshot_sync(self, timeout: float | None = None) -> None:
        if self._pty_pid is None:
            return
        if self._bound_instance_id is None:
            raise RuntimeError("E2B runtime lost bound instance id; cannot snapshot terminal state")
        state = self.terminal.get_state()
        sandbox = self._provider_sandbox(self._bound_instance_id)
        start_marker = f"__LEON_STATE_START_{uuid.uuid4().hex[:8]}__"
        end_marker = f"__LEON_STATE_END_{uuid.uuid4().hex[:8]}__"
        snapshot_out, _, _ = self._run_pty_command_sync(
            sandbox,
            self._pty_pid,
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

    def sync_terminal_state_snapshot(self, timeout: float | None = None) -> None:
        self._sync_terminal_state_snapshot_sync(timeout)

    async def execute(self, command: str, timeout: float | None = None) -> ExecuteResult:
        async with self._session_lock:
            try:
                return await asyncio.to_thread(self._execute_once_sync, command, timeout)
            except TimeoutError:
                return ExecuteResult(
                    exit_code=-1, stdout="", stderr=f"Command timed out after {timeout}s", timed_out=True
                )
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
    state_persist_mode: str = "always",
) -> PhysicalTerminalRuntime:
    capability = provider.get_capability()
    runtime_kind = str(getattr(capability, "runtime_kind", "remote"))
    if runtime_kind == "local":
        return LocalPersistentShellRuntime(terminal, lease, state_persist_mode=state_persist_mode)
    if runtime_kind == "docker_pty":
        return DockerPtyRuntime(terminal, lease, provider, state_persist_mode=state_persist_mode)
    if runtime_kind == "daytona_pty":
        return DaytonaSessionRuntime(terminal, lease, provider, state_persist_mode=state_persist_mode)
    if runtime_kind == "e2b_pty":
        return E2BPtyRuntime(terminal, lease, provider, state_persist_mode=state_persist_mode)
    return RemoteWrappedRuntime(terminal, lease, provider, state_persist_mode=state_persist_mode)
