"""
SQLiteSessionStore — local SQLite implementation of SessionStore.

Mechanical extraction of the 6 DB methods from SandboxManager.
Also carries E2B snapshot methods as temporary extras (will be
replaced by WorkspaceStorage).
"""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from sandbox.provider import SessionInfo
from sandbox.session_store import SessionStore

DEFAULT_DB_PATH = Path.home() / ".leon" / "leon.db"


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
        # @@@ E2B legacy — will be removed when WorkspaceStorage lands
        conn.execute("""
            CREATE TABLE IF NOT EXISTS e2b_workspace_files (
                thread_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                content BLOB NOT NULL,
                PRIMARY KEY (thread_id, file_path)
            )
        """)
        conn.commit()
        return conn

    # ==================== SessionStore interface ====================

    def get(self, thread_id: str) -> dict | None:
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            row = self._conn.execute(
                "SELECT * FROM sandbox_sessions WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_all(self) -> list[dict]:
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            rows = self._conn.execute("SELECT * FROM sandbox_sessions").fetchall()
            return [dict(row) for row in rows]

    def save(self, thread_id: str, info: SessionInfo, context_id: str | None) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO sandbox_sessions
                (thread_id, provider, session_id, context_id, status, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    thread_id,
                    info.provider,
                    info.session_id,
                    context_id,
                    info.status,
                    datetime.now(),
                    datetime.now(),
                ),
            )
            self._conn.commit()

    def update_status(self, thread_id: str, status: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE sandbox_sessions SET status = ?, last_active = ? WHERE thread_id = ?",
                (status, datetime.now(), thread_id),
            )
            self._conn.commit()

    def touch(self, thread_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE sandbox_sessions SET last_active = ? WHERE thread_id = ?",
                (datetime.now(), thread_id),
            )
            self._conn.commit()

    def delete(self, thread_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM sandbox_sessions WHERE thread_id = ?",
                (thread_id,),
            )
            self._conn.commit()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    # ==================== E2B snapshot (temporary) ====================

    def save_e2b_snapshot(self, thread_id: str, files: list[dict]) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM e2b_workspace_files WHERE thread_id = ?",
                (thread_id,),
            )
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
