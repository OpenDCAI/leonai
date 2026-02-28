"""SQLite repository for thread-level config persistence."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteThreadConfigRepo:
    """Thread config repository with minimal read/write API."""

    def __init__(self, db_path: str | Path, conn: sqlite3.Connection | None = None) -> None:
        self._own_conn = conn is None
        if conn is not None:
            self._conn = conn
        else:
            self._conn = sqlite3.connect(str(db_path))
        self._ensure_table()

    def close(self) -> None:
        if self._own_conn:
            self._conn.close()

    def save_metadata(self, thread_id: str, sandbox_type: str, cwd: str | None) -> None:
        self._conn.execute(
            """
            INSERT INTO thread_config (thread_id, sandbox_type, cwd)
            VALUES (?, ?, ?)
            ON CONFLICT(thread_id) DO UPDATE SET
                sandbox_type = excluded.sandbox_type,
                cwd = excluded.cwd
            """,
            (thread_id, sandbox_type, cwd),
        )
        self._conn.commit()

    def save_model(self, thread_id: str, model: str) -> None:
        self._conn.execute(
            """
            INSERT INTO thread_config (thread_id, sandbox_type, model)
            VALUES (?, 'local', ?)
            ON CONFLICT(thread_id) DO UPDATE SET
                model = excluded.model
            """,
            (thread_id, model),
        )
        self._conn.commit()

    def update_fields(self, thread_id: str, **fields: str | None) -> None:
        allowed = {"sandbox_type", "cwd", "model", "queue_mode", "observation_provider", "agent"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        self._conn.execute(
            f"UPDATE thread_config SET {set_clause} WHERE thread_id = ?",
            (*updates.values(), thread_id),
        )
        self._conn.commit()

    def lookup_model(self, thread_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT model FROM thread_config WHERE thread_id = ?",
            (thread_id,),
        ).fetchone()
        if not row:
            return None
        return row[0] if row[0] else None

    def lookup_config(self, thread_id: str) -> dict[str, str | None] | None:
        row = self._conn.execute(
            """
            SELECT sandbox_type, cwd, model, queue_mode, observation_provider, agent
            FROM thread_config
            WHERE thread_id = ?
            """,
            (thread_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "sandbox_type": row[0],
            "cwd": row[1],
            "model": row[2],
            "queue_mode": row[3],
            "observation_provider": row[4],
            "agent": row[5],
        }

    def lookup_metadata(self, thread_id: str) -> tuple[str, str | None] | None:
        row = self._conn.execute(
            "SELECT sandbox_type, cwd FROM thread_config WHERE thread_id = ?",
            (thread_id,),
        ).fetchone()
        if not row:
            return None
        return row[0], row[1]

    def _ensure_table(self) -> None:
        tables = {r[0] for r in self._conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        # @@@table_migration - keep backward compatibility by renaming old thread_metadata table once.
        if "thread_metadata" in tables and "thread_config" not in tables:
            self._conn.execute("ALTER TABLE thread_metadata RENAME TO thread_config")

        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS thread_config (
                thread_id TEXT PRIMARY KEY,
                sandbox_type TEXT NOT NULL DEFAULT 'local',
                cwd TEXT,
                model TEXT,
                queue_mode TEXT DEFAULT 'steer',
                observation_provider TEXT,
                agent TEXT
            )
            """
        )

        existing_cols = {r[1] for r in self._conn.execute("PRAGMA table_info(thread_config)")}
        if "model" not in existing_cols:
            self._conn.execute("ALTER TABLE thread_config ADD COLUMN model TEXT")
        if "cwd" not in existing_cols:
            self._conn.execute("ALTER TABLE thread_config ADD COLUMN cwd TEXT")
        if "sandbox_type" not in existing_cols:
            self._conn.execute("ALTER TABLE thread_config ADD COLUMN sandbox_type TEXT")
        if "queue_mode" not in existing_cols:
            self._conn.execute("ALTER TABLE thread_config ADD COLUMN queue_mode TEXT DEFAULT 'steer'")
        if "observation_provider" not in existing_cols:
            self._conn.execute("ALTER TABLE thread_config ADD COLUMN observation_provider TEXT")
        if "agent" not in existing_cols:
            self._conn.execute("ALTER TABLE thread_config ADD COLUMN agent TEXT")

        self._conn.commit()
