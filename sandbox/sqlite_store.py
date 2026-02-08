"""
SQLiteSessionStore — local SQLite implementation of SessionStore.

Schema migration: sandbox_sessions → sandboxes + terminals
"""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from sandbox.provider import SessionInfo
from sandbox.session_store import SessionStore

DEFAULT_DB_PATH = Path.home() / ".leon" / "sandbox.db"


class SQLiteSessionStore(SessionStore):
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._lock = threading.Lock()
        self._conn = self._init_db()

    def _init_db(self) -> sqlite3.Connection:
        if isinstance(self.db_path, Path):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")

        # New schema: sandboxes + terminals
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sandboxes (
                sandbox_id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                status TEXT DEFAULT 'running',
                config TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS terminals (
                thread_id TEXT PRIMARY KEY,
                sandbox_id TEXT,
                status TEXT DEFAULT 'active',
                terminal_type TEXT DEFAULT 'remote_stateful',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sandbox_id) REFERENCES sandboxes(sandbox_id)
            )
        """)

        # Legacy table for migration
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sandbox_sessions (
                thread_id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                session_id TEXT NOT NULL,
                context_id TEXT,
                status TEXT DEFAULT 'running',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # E2B legacy
        conn.execute("""
            CREATE TABLE IF NOT EXISTS e2b_workspace_files (
                thread_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                content BLOB NOT NULL,
                PRIMARY KEY (thread_id, file_path)
            )
        """)

        # Durable workspace binding (final architecture)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workspace_storages (
                storage_id TEXT PRIMARY KEY,
                thread_id TEXT UNIQUE NOT NULL,
                storage_type TEXT NOT NULL,
                storage_config TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        return conn

    # ==================== SessionStore interface (legacy compat) ====================

    def get(self, thread_id: str) -> dict | None:
        """Get session by thread_id (legacy compat: joins terminals + sandboxes)."""
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            row = self._conn.execute("""
                SELECT t.thread_id, t.sandbox_id as session_id, s.provider, s.status,
                       NULL as context_id, s.created_at, s.last_active
                FROM terminals t
                LEFT JOIN sandboxes s ON t.sandbox_id = s.sandbox_id
                WHERE t.thread_id = ?
            """, (thread_id,)).fetchone()
            return dict(row) if row else None

    def get_all(self) -> list[dict]:
        """Get all sessions (legacy compat: joins terminals + sandboxes)."""
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            rows = self._conn.execute("""
                SELECT t.thread_id, t.sandbox_id as session_id, s.provider, s.status,
                       NULL as context_id, s.created_at, s.last_active
                FROM terminals t
                LEFT JOIN sandboxes s ON t.sandbox_id = s.sandbox_id
            """).fetchall()
            return [dict(row) for row in rows]

    def save(self, thread_id: str, info: SessionInfo, context_id: str | None) -> None:
        """Save session (creates sandbox + terminal)."""
        with self._lock:
            # Upsert sandbox
            self._conn.execute("""
                INSERT OR REPLACE INTO sandboxes (sandbox_id, provider, status, created_at, last_active)
                VALUES (?, ?, ?, ?, ?)
            """, (info.session_id, info.provider, info.status, datetime.now(), datetime.now()))

            # Upsert terminal
            self._conn.execute("""
                INSERT OR REPLACE INTO terminals (thread_id, sandbox_id, status, created_at, last_active)
                VALUES (?, ?, 'active', ?, ?)
            """, (thread_id, info.session_id, datetime.now(), datetime.now()))

            self._conn.commit()

    def update_status(self, thread_id: str, status: str) -> None:
        """Update sandbox status for thread's sandbox."""
        with self._lock:
            self._conn.execute("""
                UPDATE sandboxes SET status = ?, last_active = ?
                WHERE sandbox_id = (SELECT sandbox_id FROM terminals WHERE thread_id = ?)
            """, (status, datetime.now(), thread_id))
            self._conn.commit()

    def touch(self, thread_id: str) -> None:
        """Touch sandbox for thread."""
        with self._lock:
            self._conn.execute("""
                UPDATE sandboxes SET last_active = ?
                WHERE sandbox_id = (SELECT sandbox_id FROM terminals WHERE thread_id = ?)
            """, (datetime.now(), thread_id))
            self._conn.commit()

    def delete(self, thread_id: str) -> None:
        """Delete terminal (sandbox remains)."""
        with self._lock:
            self._conn.execute("DELETE FROM terminals WHERE thread_id = ?", (thread_id,))
            self._conn.commit()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    # ==================== New terminal/sandbox API ====================

    def get_terminal(self, thread_id: str) -> dict | None:
        """Get terminal by thread_id."""
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            row = self._conn.execute("SELECT * FROM terminals WHERE thread_id = ?", (thread_id,)).fetchone()
            return dict(row) if row else None

    def get_sandbox(self, sandbox_id: str) -> dict | None:
        """Get sandbox by sandbox_id."""
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            row = self._conn.execute("SELECT * FROM sandboxes WHERE sandbox_id = ?", (sandbox_id,)).fetchone()
            return dict(row) if row else None

    def get_terminals_by_sandbox(self, sandbox_id: str) -> list[dict]:
        """Get all terminals attached to a sandbox."""
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            rows = self._conn.execute("SELECT * FROM terminals WHERE sandbox_id = ?", (sandbox_id,)).fetchall()
            return [dict(row) for row in rows]

    def save_sandbox(self, sandbox_id: str, provider: str, status: str = 'running') -> None:
        """Save or update sandbox."""
        with self._lock:
            self._conn.execute("""
                INSERT OR REPLACE INTO sandboxes (sandbox_id, provider, status, created_at, last_active)
                VALUES (?, ?, ?, ?, ?)
            """, (sandbox_id, provider, status, datetime.now(), datetime.now()))
            self._conn.commit()

    def save_terminal(self, thread_id: str, sandbox_id: str | None, terminal_type: str = 'remote_stateful') -> None:
        """Save or update terminal."""
        with self._lock:
            self._conn.execute("""
                INSERT OR REPLACE INTO terminals (thread_id, sandbox_id, status, terminal_type, created_at, last_active)
                VALUES (?, ?, 'active', ?, ?, ?)
            """, (thread_id, sandbox_id, terminal_type, datetime.now(), datetime.now()))
            self._conn.commit()

    def attach_terminal(self, thread_id: str, sandbox_id: str) -> None:
        """Attach terminal to sandbox."""
        with self._lock:
            self._conn.execute("""
                UPDATE terminals SET sandbox_id = ?, last_active = ? WHERE thread_id = ?
            """, (sandbox_id, datetime.now(), thread_id))
            self._conn.commit()

    def detach_terminal(self, thread_id: str) -> None:
        """Detach terminal from sandbox."""
        with self._lock:
            self._conn.execute("""
                UPDATE terminals SET sandbox_id = NULL, last_active = ? WHERE thread_id = ?
            """, (datetime.now(), thread_id))
            self._conn.commit()

    def delete_sandbox(self, sandbox_id: str) -> None:
        """Delete sandbox and detach all terminals."""
        with self._lock:
            self._conn.execute("UPDATE terminals SET sandbox_id = NULL WHERE sandbox_id = ?", (sandbox_id,))
            self._conn.execute("DELETE FROM sandboxes WHERE sandbox_id = ?", (sandbox_id,))
            self._conn.commit()

    def update_sandbox_status(self, sandbox_id: str, status: str) -> None:
        """Update sandbox status."""
        with self._lock:
            self._conn.execute("""
                UPDATE sandboxes SET status = ?, last_active = ? WHERE sandbox_id = ?
            """, (status, datetime.now(), sandbox_id))
            self._conn.commit()

    # ==================== E2B snapshot (temporary) ====================

    def save_e2b_snapshot(self, thread_id: str, files: list[dict]) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM e2b_workspace_files WHERE thread_id = ?", (thread_id,))
            for f in files:
                self._conn.execute(
                    "INSERT INTO e2b_workspace_files (thread_id, file_path, content) VALUES (?, ?, ?)",
                    (thread_id, f["file_path"], f["content"]),
                )
            self._conn.commit()

    def load_e2b_snapshot(self, thread_id: str) -> list[dict]:
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            rows = self._conn.execute(
                "SELECT file_path, content FROM e2b_workspace_files WHERE thread_id = ?",
                (thread_id,),
            ).fetchall()
            return [{"file_path": row["file_path"], "content": row["content"]} for row in rows]
