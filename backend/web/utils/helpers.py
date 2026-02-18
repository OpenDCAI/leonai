"""General helper utilities."""

import re
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.web.core.config import DB_PATH
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
        if isinstance(value, str) and value:
            return value

    nested = payload.get("data")
    if isinstance(nested, dict):
        for key in direct_keys:
            value = nested.get(key)
            if isinstance(value, str) and value:
                return value

    return None


def _ensure_thread_config_table(conn: sqlite3.Connection) -> None:
    """Create thread_config table and run migrations from old thread_metadata."""
    # Migrate old table name if exists
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "thread_metadata" in tables and "thread_config" not in tables:
        conn.execute("ALTER TABLE thread_metadata RENAME TO thread_config")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS thread_config"
        "(thread_id TEXT PRIMARY KEY, sandbox_type TEXT NOT NULL, cwd TEXT, model TEXT, queue_mode TEXT DEFAULT 'steer')"
    )
    for col, default in [("model", None), ("queue_mode", "'steer'")]:
        try:
            default_clause = f" DEFAULT {default}" if default else ""
            conn.execute(f"ALTER TABLE thread_config ADD COLUMN {col} TEXT{default_clause}")
        except sqlite3.OperationalError:
            pass


def save_thread_config(thread_id: str, **fields: Any) -> None:
    """Update specific fields of thread config in SQLite.

    Usage: save_thread_config(thread_id, model="gpt-4", queue_mode="followup")
    """
    allowed = {"sandbox_type", "cwd", "model", "queue_mode"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    with sqlite3.connect(str(DB_PATH)) as conn:
        _ensure_thread_config_table(conn)
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(
            f"UPDATE thread_config SET {set_clause} WHERE thread_id = ?",
            (*updates.values(), thread_id),
        )
        conn.commit()


def load_thread_config(thread_id: str):
    """Load full thread config from SQLite. Returns ThreadConfig or None."""
    if not DB_PATH.exists():
        return None
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            _ensure_thread_config_table(conn)
            row = conn.execute(
                "SELECT sandbox_type, cwd, model, queue_mode FROM thread_config WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
            if not row:
                return None
            from backend.web.models.thread_config import ThreadConfig

            return ThreadConfig(
                sandbox_type=row["sandbox_type"],
                cwd=row["cwd"],
                model=row["model"],
                queue_mode=row["queue_mode"] or "steer",
            )
    except sqlite3.OperationalError:
        return None


def init_thread_config(thread_id: str, sandbox_type: str, cwd: str | None) -> None:
    """Create initial thread config row in SQLite."""
    with sqlite3.connect(str(DB_PATH)) as conn:
        _ensure_thread_config_table(conn)
        conn.execute(
            "INSERT OR REPLACE INTO thread_config (thread_id, sandbox_type, cwd) VALUES (?, ?, ?)",
            (thread_id, sandbox_type, cwd),
        )
        conn.commit()


def save_thread_model(thread_id: str, model: str) -> None:
    """Persist the selected model for a thread."""
    save_thread_config(thread_id, model=model)


def lookup_thread_model(thread_id: str) -> str | None:
    """Look up persisted model for a thread."""
    config = load_thread_config(thread_id)
    return config.model if config else None


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
            tc = load_thread_config(thread_id)
            if tc:
                thread_cwd = tc.cwd
    base = Path(thread_cwd).resolve() if thread_cwd else local_workspace_root

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
