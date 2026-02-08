"""Persistent shell executor that maintains session state across commands."""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass, field

from .base import AsyncCommand, BaseExecutor, ExecuteResult


@dataclass
class ShellSession:
    """Persistent shell session."""

    session_id: str
    process: asyncio.subprocess.Process
    cwd: str
    env: dict[str, str]
    stdin_writer: asyncio.StreamWriter
    stdout_reader: asyncio.StreamReader
    stderr_reader: asyncio.StreamReader
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class PersistentExecutor(BaseExecutor):
    """Executor that maintains persistent shell sessions."""

    def __init__(
        self,
        shell_command: tuple[str, ...],
        shell_name: str,
        default_cwd: str | None = None,
        startup_commands: list[str] | None = None,
    ):
        super().__init__(default_cwd)
        self.shell_command = shell_command
        self.shell_name = shell_name
        self.startup_commands = startup_commands or []
        self._sessions: dict[str, ShellSession] = {}
        self._running_commands: dict[str, AsyncCommand] = {}

    async def _create_session(self, cwd: str, env: dict[str, str]) -> ShellSession:
        """Create a new persistent shell session."""
        proc = await asyncio.create_subprocess_exec(
            *self.shell_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
        )

        session = ShellSession(
            session_id=f"session_{uuid.uuid4().hex[:8]}",
            process=proc,
            cwd=cwd,
            env=env,
            stdin_writer=proc.stdin,
            stdout_reader=proc.stdout,
            stderr_reader=proc.stderr,
        )

        # Run startup commands
        for cmd in self.startup_commands:
            await self._send_command(session, cmd)

        self._sessions[session.session_id] = session
        return session

    async def _send_command(self, session: ShellSession, command: str) -> tuple[str, str, int]:
        """Send command to session and read output."""
        marker = f"__CMD_END_{uuid.uuid4().hex[:8]}__"
        full_cmd = f"{command}\necho {marker} $?\n"

        session.stdin_writer.write(full_cmd.encode())
        await session.stdin_writer.drain()

        stdout_lines = []
        stderr_lines = []
        exit_code = 0

        # Read stdout until marker
        while True:
            line = await session.stdout_reader.readline()
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

        return "".join(stdout_lines), "".join(stderr_lines), exit_code

    async def execute(
        self,
        command: str,
        cwd: str | None = None,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> ExecuteResult:
        """Execute command in persistent session."""
        work_dir = cwd or self.default_cwd or os.getcwd()

        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        # Get or create session for this cwd/env combo
        session_key = f"{work_dir}:{hash(frozenset(merged_env.items()))}"
        session = None
        for s in self._sessions.values():
            if s.cwd == work_dir:
                session = s
                break

        if session is None:
            session = await self._create_session(work_dir, merged_env)

        async with session.lock:
            try:
                stdout, stderr, exit_code = await asyncio.wait_for(
                    self._send_command(session, command),
                    timeout=timeout,
                )
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

    async def execute_async(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> AsyncCommand:
        """Execute command asynchronously."""
        work_dir = cwd or self.default_cwd or os.getcwd()
        command_id = f"cmd_{uuid.uuid4().hex[:12]}"

        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=work_dir,
            env=merged_env,
            shell=True,
            executable=self.shell_command[0],
        )

        async_cmd = AsyncCommand(
            command_id=command_id,
            command_line=command,
            cwd=work_dir,
            process=proc,
        )
        self._running_commands[command_id] = async_cmd

        asyncio.create_task(self._monitor_process(async_cmd))

        return async_cmd

    async def _monitor_process(self, async_cmd: AsyncCommand) -> None:
        """Monitor async process."""
        proc = async_cmd.process
        if proc is None:
            return

        stdout_bytes, stderr_bytes = await proc.communicate()

        async_cmd.stdout_buffer.append(stdout_bytes.decode("utf-8", errors="replace"))
        async_cmd.stderr_buffer.append(stderr_bytes.decode("utf-8", errors="replace"))
        async_cmd.exit_code = proc.returncode
        async_cmd.done = True

    async def get_status(self, command_id: str) -> AsyncCommand | None:
        return self._running_commands.get(command_id)

    async def wait_for(
        self,
        command_id: str,
        timeout: float | None = None,
    ) -> ExecuteResult | None:
        async_cmd = self._running_commands.get(command_id)
        if async_cmd is None:
            return None

        if not async_cmd.done:
            try:
                await asyncio.wait_for(
                    self._wait_until_done(async_cmd),
                    timeout=timeout,
                )
            except TimeoutError:
                return ExecuteResult(
                    exit_code=-1,
                    stdout="".join(async_cmd.stdout_buffer),
                    stderr="".join(async_cmd.stderr_buffer),
                    timed_out=True,
                    command_id=command_id,
                )

        return ExecuteResult(
            exit_code=async_cmd.exit_code or 0,
            stdout="".join(async_cmd.stdout_buffer),
            stderr="".join(async_cmd.stderr_buffer),
            timed_out=False,
            command_id=command_id,
        )

    async def _wait_until_done(self, async_cmd: AsyncCommand) -> None:
        while not async_cmd.done:
            await asyncio.sleep(0.1)

    def store_completed_result(
        self,
        command_id: str,
        command_line: str,
        cwd: str,
        result: ExecuteResult,
    ) -> None:
        async_cmd = AsyncCommand(
            command_id=command_id,
            command_line=command_line,
            cwd=cwd,
            process=None,
            stdout_buffer=[result.stdout],
            stderr_buffer=[result.stderr],
            exit_code=result.exit_code,
            done=True,
        )
        self._running_commands[command_id] = async_cmd

    async def cleanup(self) -> None:
        """Cleanup all sessions."""
        for session in self._sessions.values():
            try:
                session.process.terminate()
                await session.process.wait()
            except Exception:
                pass
        self._sessions.clear()
