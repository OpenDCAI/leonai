#!/usr/bin/env python3
"""Interactive CLI for agent-style command tool debugging."""

from __future__ import annotations

import argparse
import asyncio
import shlex
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from middleware.command import CommandMiddleware
from sandbox.local import LocalSandbox


class AgentShoesCLI:
    def __init__(self, workspace: Path, thread_id: str, db_path: Path):
        self.workspace = workspace
        self.thread_id = thread_id
        self.db_path = db_path
        self.sandbox = LocalSandbox(workspace_root=str(workspace), db_path=db_path)
        self.sandbox.ensure_session(thread_id)
        self.middleware = CommandMiddleware(workspace_root=workspace, executor=self.sandbox.shell(), verbose=False)

    async def run_blocking(self, command: str) -> str:
        return await self.middleware._execute_command(
            command_line=command,
            cwd=None,
            blocking=True,
            timeout=None,
        )

    async def run_non_blocking(self, command: str) -> str:
        return await self.middleware._execute_command(
            command_line=command,
            cwd=None,
            blocking=False,
            timeout=None,
        )

    async def command_status(self, command_id: str, wait_seconds: int, max_chars: int) -> str:
        return await self.middleware._get_command_status(
            command_id=command_id,
            wait_seconds=wait_seconds,
            max_chars=max_chars,
        )

    def show_context(self) -> str:
        mgr = self.sandbox.manager
        active = mgr.terminal_store.get_active(self.thread_id)
        default = mgr.terminal_store.get_default(self.thread_id)
        session = mgr.session_manager.get(self.thread_id, active.terminal_id) if active else None
        lease = mgr.lease_store.get(active.lease_id) if active else None
        lines = [
            f"thread_id={self.thread_id}",
            f"active_terminal={active.terminal_id if active else None}",
            f"default_terminal={default.terminal_id if default else None}",
            f"session_id={session.session_id if session else None}",
            f"lease_id={lease.lease_id if lease else None}",
            f"lease_state={lease.observed_state if lease else None}",
            f"cwd={active.get_state().cwd if active else None}",
        ]
        return "\n".join(lines)

    def list_terminals(self) -> str:
        mgr = self.sandbox.manager
        terminals = mgr.terminal_store.list_by_thread(self.thread_id)
        if not terminals:
            return "(no terminals)"
        return "\n".join(
            f"{t.terminal_id} lease={t.lease_id} cwd={t.get_state().cwd} ver={t.get_state().state_version}" for t in terminals
        )

    def list_commands(self, limit: int) -> str:
        with sqlite3.connect(str(self.db_path), timeout=30) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT c.command_id, c.terminal_id, c.status, c.exit_code, c.created_at, c.updated_at
                FROM terminal_commands c
                JOIN abstract_terminals t ON t.terminal_id = c.terminal_id
                WHERE t.thread_id = ?
                ORDER BY c.created_at DESC
                LIMIT ?
                """,
                (self.thread_id, limit),
            ).fetchall()
        if not rows:
            return "(no commands)"
        return "\n".join(
            f"{r['command_id']} term={r['terminal_id']} status={r['status']} exit={r['exit_code']} updated={r['updated_at']}"
            for r in rows
        )

    def close(self) -> None:
        self.sandbox.close()


def _print_help() -> None:
    print("commands:")
    print("  run <shell-cmd>                  # non-blocking run_command")
    print("  runb <shell-cmd>                 # blocking run_command")
    print("  status <command_id> [wait] [max] # command_status")
    print("  watch <command_id> [interval]    # poll status until done")
    print("  ctx                              # thread/session/terminal context")
    print("  terms                            # list abstract terminals of this thread")
    print("  commands [limit]                 # list terminal_commands rows")
    print("  help")
    print("  exit")


async def _watch(cli: AgentShoesCLI, command_id: str, interval: float) -> None:
    while True:
        out = await cli.command_status(command_id, wait_seconds=0, max_chars=8000)
        print(out)
        if "Status: done" in out or out.startswith("Error:"):
            return
        await asyncio.sleep(interval)


async def repl(cli: AgentShoesCLI) -> None:
    _print_help()
    while True:
        try:
            # @@@nonblocking-repl-input - keep event loop alive so background commands continue while user thinks/types.
            line = (await asyncio.to_thread(input, "agent-shoes> ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not line:
            continue
        if line in {"exit", "quit"}:
            return
        if line in {"help", "h", "?"}:
            _print_help()
            continue
        if line == "ctx":
            print(cli.show_context())
            continue
        if line == "terms":
            print(cli.list_terminals())
            continue
        if line.startswith("commands"):
            parts = shlex.split(line)
            limit = int(parts[1]) if len(parts) > 1 else 20
            print(cli.list_commands(limit))
            continue
        if line.startswith("runb "):
            # @@@run-command-pass-through - keep raw command text after prefix unchanged for faithful tool debugging.
            command = line[5:]
            print(await cli.run_blocking(command))
            continue
        if line.startswith("run "):
            command = line[4:]
            print(await cli.run_non_blocking(command))
            continue
        if line.startswith("status "):
            parts = shlex.split(line)
            if len(parts) < 2:
                print("usage: status <command_id> [wait] [max]")
                continue
            command_id = parts[1]
            wait_seconds = int(parts[2]) if len(parts) > 2 else 0
            max_chars = int(parts[3]) if len(parts) > 3 else 10000
            print(await cli.command_status(command_id, wait_seconds=wait_seconds, max_chars=max_chars))
            continue
        if line.startswith("watch "):
            parts = shlex.split(line)
            if len(parts) < 2:
                print("usage: watch <command_id> [interval]")
                continue
            command_id = parts[1]
            interval = float(parts[2]) if len(parts) > 2 else 0.5
            await _watch(cli, command_id, interval)
            continue

        print("unknown command; use `help`")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agent-shoes command tool debugger")
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="workspace root")
    parser.add_argument("--thread-id", type=str, default="agent-shoes-thread", help="thread id to bind")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("/tmp/leon-agent-shoes.db"),
        help="sandbox db path",
    )
    return parser.parse_args()


async def _main() -> None:
    args = parse_args()
    cli = AgentShoesCLI(workspace=args.workspace.resolve(), thread_id=args.thread_id, db_path=args.db_path.resolve())
    try:
        await repl(cli)
    finally:
        cli.close()


if __name__ == "__main__":
    asyncio.run(_main())
