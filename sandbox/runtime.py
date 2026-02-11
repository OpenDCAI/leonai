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
import sqlite3
import shlex
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sandbox.lease import SandboxLease
    from sandbox.provider import SandboxProvider
    from sandbox.terminal import AbstractTerminal, TerminalState

from sandbox.interfaces.executor import ExecuteResult
from sandbox.interfaces.executor import AsyncCommand


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
        self.chat_session_id: str | None = None
        self._commands: dict[str, AsyncCommand] = {}
        self._tasks: dict[str, asyncio.Task[ExecuteResult]] = {}

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
        if row["status"] == "running":
            # @@@stale-running-command - Runtime restart loses in-memory task, mark DB row failed instead of hanging forever.
            msg = "Runtime restarted before command completion"
            async_cmd.stderr_buffer = [msg]
            async_cmd.exit_code = 1
            async_cmd.done = True
            self._upsert_command_row(
                command_id=command_id,
                command_line=async_cmd.command_line,
                cwd=async_cmd.cwd,
                status="failed",
                stdout=async_cmd.stdout_buffer[0],
                stderr=msg,
                exit_code=1,
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
            try:
                result = await self.execute(command, timeout=None)
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
            return result

        self._tasks[command_id] = asyncio.create_task(_run())
        return async_cmd

    async def get_command(self, command_id: str) -> AsyncCommand | None:
        cmd = self._commands.get(command_id)
        if cmd:
            return cmd
        return self._load_command_from_db(command_id)

    async def wait_for_command(self, command_id: str, timeout: float | None = None) -> ExecuteResult | None:
        async_cmd = await self.get_command(command_id)
        if async_cmd is None:
            return None
        task = self._tasks.get(command_id)
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
            self._baseline_env = self._parse_env_output(baseline_stdout)
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
