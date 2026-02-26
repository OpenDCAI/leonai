"""General helper utilities."""

import re
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.web.core.config import DB_PATH
from core.memory.thread_config_repo import SQLiteThreadConfigRepo
from sandbox.db import DEFAULT_DB_PATH as SANDBOX_DB_PATH


def is_virtual_thread_id(thread_id: str | None) -> bool:
    """Check if thread_id is a virtual thread (wrapped in parentheses)."""
    return bool(thread_id) and thread_id.startswith("(") and thread_id.endswith(")")


def get_terminal_timestamps(terminal_id: str) -> tuple[str | None, str | None]:
    """Get created_at and updated_at timestamps for a terminal."""
    if not SANDBOX_DB_PATH.exists():
        return None, None
    with sqlite3.connect(str(SANDBOX_DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT created_at, updated_at FROM abstract_terminals WHERE terminal_id = ?",
            (terminal_id,),
        ).fetchone()
        if not row:
            return None, None
        return row["created_at"], row["updated_at"]


def get_lease_timestamps(lease_id: str) -> tuple[str | None, str | None]:
    """Get created_at and updated_at timestamps for a lease."""
    if not SANDBOX_DB_PATH.exists():
        return None, None
    with sqlite3.connect(str(SANDBOX_DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT created_at, updated_at FROM sandbox_leases WHERE lease_id = ?",
            (lease_id,),
        ).fetchone()
        if not row:
            return None, None
        return row["created_at"], row["updated_at"]


def extract_webhook_instance_id(payload: dict[str, Any]) -> str | None:
    """Extract provider instance/session id from webhook payload."""
    direct_keys = ("session_id", "sandbox_id", "instance_id", "id")
    for key in direct_keys:
        value = payload.get(key)
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                return normalized

    nested = payload.get("data")
    if isinstance(nested, dict):
        for key in direct_keys:
            value = nested.get(key)
            if isinstance(value, str):
                normalized = value.strip()
                if normalized:
                    return normalized

    return None


def save_thread_metadata(thread_id: str, sandbox_type: str, cwd: str | None) -> None:
    """Persist thread sandbox_type and cwd to SQLite."""
    repo = SQLiteThreadConfigRepo(DB_PATH)
    try:
        repo.save_metadata(thread_id, sandbox_type, cwd)
    finally:
        repo.close()


def save_thread_model(thread_id: str, model: str) -> None:
    """Persist the selected model for a thread."""
    repo = SQLiteThreadConfigRepo(DB_PATH)
    try:
        repo.save_model(thread_id, model)
    finally:
        repo.close()


def lookup_thread_model(thread_id: str) -> str | None:
    """Look up persisted model for a thread."""
    if not DB_PATH.exists():
        return None
    try:
        repo = SQLiteThreadConfigRepo(DB_PATH)
        try:
            return repo.lookup_model(thread_id)
        finally:
            repo.close()
    except sqlite3.OperationalError:
        return None


def lookup_thread_metadata(thread_id: str) -> tuple[str, str | None] | None:
    """Look up persisted (sandbox_type, cwd) for a thread. Returns None if not found."""
    if not DB_PATH.exists():
        return None
    try:
        repo = SQLiteThreadConfigRepo(DB_PATH)
        try:
            return repo.lookup_metadata(thread_id)
        finally:
            repo.close()
    except sqlite3.OperationalError:
        return None


def resolve_local_workspace_path(
    raw_path: str | None,
    thread_id: str | None = None,
    thread_cwd_map: dict[str, str] | None = None,
    local_workspace_root: Path | None = None,
) -> Path:
    """Resolve a workspace path relative to thread-specific or global workspace root."""
    from backend.web.core.config import LOCAL_WORKSPACE_ROOT

    if local_workspace_root is None:
        local_workspace_root = LOCAL_WORKSPACE_ROOT

    # Use thread-specific workspace root if available (memory → SQLite fallback)
    thread_cwd = None
    if thread_id:
        if thread_cwd_map:
            thread_cwd = thread_cwd_map.get(thread_id)
        if not thread_cwd:
            meta = lookup_thread_metadata(thread_id)
            if meta:
                thread_cwd = meta[1]
    # @@@workspace-root-normalization - boundary check needs absolute base path to avoid false escape on relative roots.
    base = Path(thread_cwd).resolve() if thread_cwd else Path(local_workspace_root).resolve()

    if not raw_path:
        return base
    requested = Path(raw_path).expanduser()
    if requested.is_absolute():
        target = requested.resolve()
    else:
        target = (base / requested).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise HTTPException(400, f"Path outside workspace: {target}") from exc
    return target


def delete_thread_in_db(thread_id: str) -> None:
    """Delete all records for a thread from both databases."""
    ident_re = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    def _sqlite_ident(name: str) -> str:
        if not ident_re.match(name):
            raise RuntimeError(f"Invalid sqlite identifier: {name}")
        return f'"{name}"'

    for db_path in (DB_PATH, SANDBOX_DB_PATH):
        if not db_path.exists():
            continue
        with sqlite3.connect(str(db_path)) as conn:
            existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            for table in existing:
                try:
                    table_ident = _sqlite_ident(table)
                except RuntimeError:
                    continue
                cols = {r[1] for r in conn.execute("PRAGMA table_info(" + table_ident + ")").fetchall()}
                if "thread_id" in cols:
                    conn.execute("DELETE FROM " + table_ident + " WHERE thread_id = ?", (thread_id,))
            conn.commit()
