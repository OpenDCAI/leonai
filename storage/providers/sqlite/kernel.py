"""Unified SQLite kernel for role-based connections and consistent PRAGMA setup."""

from __future__ import annotations

import os
import sqlite3
from enum import StrEnum
from pathlib import Path
from typing import Any

WAL_MODE = "WAL"
BUSY_TIMEOUT_MS = 30_000
SYNCHRONOUS = "NORMAL"


class SQLiteDBRole(StrEnum):
    """Logical database roles used by SQLite callers."""

    MAIN = "main"
    RUN_EVENT = "run_event"
    EVAL = "eval"
    SANDBOX = "sandbox"
    QUEUE = "queue"
    SUBAGENT = "subagent"


def resolve_role_db_path(role: SQLiteDBRole, db_path: Path | str | None = None) -> Path:
    """Resolve role-specific DB path, honoring env overrides."""
    if db_path is not None:
        return Path(db_path)

    home_root = Path.home() / ".leon"
    main_raw = os.getenv("LEON_DB_PATH")
    main_path = Path(main_raw) if main_raw else home_root / "leon.db"

    if role == SQLiteDBRole.MAIN:
        return main_path
    if role == SQLiteDBRole.RUN_EVENT:
        run_event_raw = os.getenv("LEON_RUN_EVENT_DB_PATH")
        return Path(run_event_raw) if run_event_raw else main_path.with_name("events.db")
    if role == SQLiteDBRole.EVAL:
        eval_raw = os.getenv("LEON_EVAL_DB_PATH")
        return Path(eval_raw) if eval_raw else home_root / "eval.db"
    if role == SQLiteDBRole.SANDBOX:
        sandbox_raw = os.getenv("LEON_SANDBOX_DB_PATH")
        return Path(sandbox_raw) if sandbox_raw else home_root / "sandbox.db"
    if role == SQLiteDBRole.QUEUE:
        queue_raw = os.getenv("LEON_QUEUE_DB_PATH")
        return Path(queue_raw) if queue_raw else main_path.with_name("queue.db")
    if role == SQLiteDBRole.SUBAGENT:
        subagent_raw = os.getenv("LEON_SUBAGENT_DB_PATH")
        return Path(subagent_raw) if subagent_raw else main_path.with_name("subagent.db")
    return main_path


def apply_pragmas(conn: sqlite3.Connection) -> None:
    """Apply canonical PRAGMA settings for Leon SQLite connections."""
    conn.execute(f"PRAGMA journal_mode={WAL_MODE}")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    conn.execute(f"PRAGMA synchronous={SYNCHRONOUS}")


def connect_sqlite(
    db_path: Path | str,
    *,
    row_factory: type | None = None,
    check_same_thread: bool = True,
    timeout_ms: int = BUSY_TIMEOUT_MS,
) -> sqlite3.Connection:
    """Create a SQLite connection with unified settings."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(path),
        timeout=timeout_ms / 1000,
        check_same_thread=check_same_thread,
    )
    apply_pragmas(conn)
    if row_factory is not None:
        conn.row_factory = row_factory
    return conn


def connect_sqlite_role(
    role: SQLiteDBRole,
    *,
    db_path: Path | str | None = None,
    row_factory: type | None = None,
    check_same_thread: bool = True,
    timeout_ms: int = BUSY_TIMEOUT_MS,
) -> sqlite3.Connection:
    """Create connection for a logical role using role-specific path resolution."""
    resolved = resolve_role_db_path(role, db_path=db_path)
    return connect_sqlite(
        resolved,
        row_factory=row_factory,
        check_same_thread=check_same_thread,
        timeout_ms=timeout_ms,
    )


async def connect_sqlite_async(
    db_path: Path | str,
    *,
    row_factory: Any | None = None,
    timeout_ms: int = BUSY_TIMEOUT_MS,
):
    """Create async SQLite connection with unified settings."""
    import aiosqlite

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(
        str(path),
        timeout=timeout_ms / 1000,
    )
    await conn.execute(f"PRAGMA journal_mode={WAL_MODE}")
    await conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    await conn.execute(f"PRAGMA synchronous={SYNCHRONOUS}")
    if row_factory is not None:
        conn.row_factory = row_factory
    return conn
