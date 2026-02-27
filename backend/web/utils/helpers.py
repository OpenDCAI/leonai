"""General helper utilities."""

import os
import re
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.web.core.config import DB_PATH
from sandbox.db import DEFAULT_DB_PATH as SANDBOX_DB_PATH


def _memory_write_backend() -> str:
    # @@@dualwrite-gate - PG dual-write must be explicitly enabled to avoid changing default runtime behavior.
    backend = os.getenv("LEON_MEMORY_WRITE_BACKEND", "sqlite").strip().lower()
    if backend not in {"sqlite", "dual"}:
        raise RuntimeError(f"invalid LEON_MEMORY_WRITE_BACKEND={backend}; expected sqlite or dual")
    return backend


def _pg_write_enabled() -> bool:
    return _memory_write_backend() == "dual"


def _require_pg_runtime() -> tuple[Any, str]:
    dsn = os.getenv("LEON_PG_DSN", "").strip()
    if not dsn:
        raise RuntimeError("LEON_PG_DSN is required when LEON_MEMORY_WRITE_BACKEND=dual")
    try:
        import psycopg  # type: ignore[import-not-found]
    except Exception as error:  # pragma: no cover - runtime env check
        raise RuntimeError("psycopg is required when LEON_MEMORY_WRITE_BACKEND=dual") from error
    return psycopg, dsn


def _derive_thread_kind(thread_id: str) -> str:
    return "subagent" if thread_id.startswith("subagent_") else "main"


def _pg_upsert_thread_registry(
    thread_id: str,
    sandbox_type: str,
    cwd: str | None,
    model: str | None = None,
    queue_mode: str = "steer",
    observation_provider: str | None = None,
    agent_id: str = "legacy-default",
) -> None:
    psycopg, dsn = _require_pg_runtime()
    thread_kind = _derive_thread_kind(thread_id)
    try:
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute(
                """
                INSERT INTO thread_registry
                    (thread_id, agent_id, thread_kind, sandbox_type, cwd, model, queue_mode, observation_provider)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (thread_id) DO UPDATE SET
                    agent_id = EXCLUDED.agent_id,
                    thread_kind = EXCLUDED.thread_kind,
                    sandbox_type = EXCLUDED.sandbox_type,
                    cwd = EXCLUDED.cwd,
                    model = EXCLUDED.model,
                    queue_mode = EXCLUDED.queue_mode,
                    observation_provider = EXCLUDED.observation_provider,
                    updated_at = now()
                """,
                (thread_id, agent_id, thread_kind, sandbox_type, cwd, model, queue_mode, observation_provider),
            )
        print(f"dualwrite_thread_registry_ok action=upsert thread_id={thread_id}", flush=True)
    except Exception as error:
        print(f"dualwrite_thread_registry_fail action=upsert thread_id={thread_id} error={error}", flush=True)
        raise RuntimeError(f"dualwrite thread_registry upsert failed for {thread_id}: {error}") from error


def _pg_update_thread_registry(thread_id: str, updates: dict[str, Any]) -> None:
    if not updates:
        return
    psycopg, dsn = _require_pg_runtime()
    allowed = {"sandbox_type", "cwd", "model", "queue_mode", "observation_provider"}
    safe_updates = {k: v for k, v in updates.items() if k in allowed}
    if not safe_updates:
        return
    set_clause = ", ".join(f"{key} = %s" for key in safe_updates)
    values = [*safe_updates.values(), thread_id]
    try:
        with psycopg.connect(dsn, autocommit=True) as conn:
            cursor = conn.execute(
                f"UPDATE thread_registry SET {set_clause}, updated_at = now() WHERE thread_id = %s",
                values,
            )
            if cursor.rowcount == 0:
                raise RuntimeError("target thread_registry row not found")
        print(f"dualwrite_thread_registry_ok action=update thread_id={thread_id}", flush=True)
    except Exception as error:
        print(f"dualwrite_thread_registry_fail action=update thread_id={thread_id} error={error}", flush=True)
        raise RuntimeError(f"dualwrite thread_registry update failed for {thread_id}: {error}") from error


def _pg_delete_thread_related(thread_id: str) -> None:
    psycopg, dsn = _require_pg_runtime()
    try:
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute("DELETE FROM history_events WHERE thread_id = %s", (thread_id,))
            conn.execute("DELETE FROM task_registry WHERE thread_id = %s", (thread_id,))
            conn.execute("DELETE FROM thread_registry WHERE thread_id = %s", (thread_id,))
        print(f"dualwrite_thread_registry_ok action=delete thread_id={thread_id}", flush=True)
    except Exception as error:
        print(f"dualwrite_thread_registry_fail action=delete thread_id={thread_id} error={error}", flush=True)
        raise RuntimeError(f"dualwrite thread delete failed for {thread_id}: {error}") from error


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
    for col, default in [("model", None), ("queue_mode", "'steer'"), ("observation_provider", None)]:
        try:
            default_clause = f" DEFAULT {default}" if default else ""
            conn.execute(f"ALTER TABLE thread_config ADD COLUMN {col} TEXT{default_clause}")
        except sqlite3.OperationalError:
            pass


def save_thread_config(thread_id: str, **fields: Any) -> None:
    """Update specific fields of thread config in SQLite.

    Usage: save_thread_config(thread_id, model="gpt-4", queue_mode="followup")
    """
    allowed = {"sandbox_type", "cwd", "model", "queue_mode", "observation_provider"}
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
    if _pg_write_enabled():
        # @@@dualwrite-order - SQLite commit first, then PG mirror write for staged rollout.
        _pg_update_thread_registry(thread_id, updates)


def load_thread_config(thread_id: str):
    """Load full thread config from SQLite. Returns ThreadConfig or None."""
    if not DB_PATH.exists():
        return None
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            _ensure_thread_config_table(conn)
            row = conn.execute(
                "SELECT sandbox_type, cwd, model, queue_mode, observation_provider FROM thread_config WHERE thread_id = ?",
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
                observation_provider=row["observation_provider"],
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
    if _pg_write_enabled():
        _pg_upsert_thread_registry(thread_id=thread_id, sandbox_type=sandbox_type, cwd=cwd)


def get_active_observation_provider() -> str | None:
    """Read global observation config and return the active provider name."""
    from config.observation_loader import ObservationLoader

    config = ObservationLoader().load()
    return config.active if config.active else None


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
    if _pg_write_enabled():
        _pg_delete_thread_related(thread_id)
