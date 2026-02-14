from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any


def _sandbox_db_path() -> Path:
    return Path(os.getenv("LEON_SANDBOX_DB_PATH") or (Path.home() / ".leon" / "sandbox.db"))


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.execute("PRAGMA busy_timeout=10000")
    conn.row_factory = sqlite3.Row
    return conn


def list_active_sessions(*, limit: int = 50) -> list[dict[str, Any]]:
    # @@@e2e-evidence - See `teams/log/leonai/data_platform/2026-02-15_e2e_operator_search_and_sandboxes.md`
    db_path = _sandbox_db_path()
    if not db_path.exists():
        return []

    with _connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        required = {"chat_sessions", "sandbox_leases", "abstract_terminals", "terminal_commands"}
        if not required.issubset(tables):
            raise RuntimeError(f"sandbox db missing tables: {sorted(required - tables)}")

        rows = conn.execute(
            """
            SELECT
              cs.thread_id,
              cs.chat_session_id,
              cs.terminal_id,
              cs.lease_id,
              cs.status AS chat_status,
              cs.started_at,
              cs.last_active_at,
              sl.provider_name,
              sl.observed_state,
              sl.last_error,
              at.cwd,
              (
                SELECT tc.command_id
                FROM terminal_commands tc
                WHERE tc.terminal_id = cs.terminal_id
                ORDER BY tc.created_at DESC
                LIMIT 1
              ) AS last_command_id,
              (
                SELECT tc.status
                FROM terminal_commands tc
                WHERE tc.terminal_id = cs.terminal_id
                ORDER BY tc.created_at DESC
                LIMIT 1
              ) AS last_command_status,
              (
                SELECT tc.exit_code
                FROM terminal_commands tc
                WHERE tc.terminal_id = cs.terminal_id
                ORDER BY tc.created_at DESC
                LIMIT 1
              ) AS last_command_exit_code
            FROM chat_sessions cs
            JOIN sandbox_leases sl ON sl.lease_id = cs.lease_id
            JOIN abstract_terminals at ON at.terminal_id = cs.terminal_id
            WHERE cs.status IN ('active', 'idle', 'paused')
            ORDER BY cs.last_active_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()

        return [
            {
                "thread_id": r["thread_id"],
                "chat_session_id": r["chat_session_id"],
                "terminal_id": r["terminal_id"],
                "lease_id": r["lease_id"],
                "chat_status": r["chat_status"],
                "started_at": r["started_at"],
                "last_active_at": r["last_active_at"],
                "provider_name": r["provider_name"],
                "observed_state": r["observed_state"],
                "last_error": r["last_error"],
                "cwd": r["cwd"],
                "last_command": {
                    "command_id": r["last_command_id"],
                    "status": r["last_command_status"],
                    "exit_code": r["last_command_exit_code"],
                }
                if r["last_command_id"]
                else None,
            }
            for r in rows
        ]


def list_thread_commands(*, thread_id: str, limit: int = 200) -> list[dict[str, Any]]:
    db_path = _sandbox_db_path()
    if not db_path.exists():
        return []

    with _connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        required = {"thread_terminal_pointers", "terminal_commands"}
        if not required.issubset(tables):
            raise RuntimeError(f"sandbox db missing tables: {sorted(required - tables)}")

        pointer = conn.execute(
            """
            SELECT active_terminal_id
            FROM thread_terminal_pointers
            WHERE thread_id = ?
            """,
            (thread_id,),
        ).fetchone()
        if not pointer:
            return []
        terminal_id = pointer["active_terminal_id"]

        rows = conn.execute(
            """
            SELECT command_id, terminal_id, chat_session_id, command_line, cwd, status, exit_code,
                   created_at, updated_at, finished_at
            FROM terminal_commands
            WHERE terminal_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (terminal_id, int(limit)),
        ).fetchall()

        return [
            {
                "command_id": r["command_id"],
                "terminal_id": r["terminal_id"],
                "chat_session_id": r["chat_session_id"],
                "command_line": r["command_line"],
                "cwd": r["cwd"],
                "status": r["status"],
                "exit_code": r["exit_code"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "finished_at": r["finished_at"],
            }
            for r in rows
        ]
