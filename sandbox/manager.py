"""
Sandbox session manager.

Tracks thread_id <-> session_id mapping with SQLite persistence.
Handles lazy creation, auto-pause, and resume lifecycle.
"""

import sqlite3
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from sandbox.provider import SandboxProvider, SessionInfo

DEFAULT_DB_PATH = Path.home() / ".leon" / "leon.db"


def lookup_sandbox_for_thread(thread_id: str) -> str | None:
    """Check if a thread has a sandbox session in the DB.

    Returns provider name ('e2b', 'docker', 'agentbay') or None.
    Pure SQLite lookup — no provider initialization needed.
    """
    if not DEFAULT_DB_PATH.exists():
        return None
    try:
        with sqlite3.connect(str(DEFAULT_DB_PATH), timeout=5) as conn:
            row = conn.execute(
                "SELECT provider FROM sandbox_sessions WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
            return row[0] if row else None
    except Exception:
        return None


class SandboxManager:
    """
    Manages sandbox sessions across threads.

    Responsibilities:
    - Track thread_id <-> session_id mapping
    - Persist to SQLite for resume across LEON restarts
    - Handle lazy creation and auto-pause lifecycle

    Lifecycle:
    1. First tool call -> lazy create session
    2. Thread switch -> pause current session
    3. Resume thread -> resume paused session
    4. Exit LEON -> pause all sessions
    5. TTL expiry -> auto-delete (handled by provider)
    """

    def __init__(
        self,
        provider: SandboxProvider,
        db_path: Path | None = None,
        default_context_id: str | None = None,
        on_session_ready: Callable[[str, str], None] | None = None,
    ):
        self.provider = provider
        self.db_path = db_path or DEFAULT_DB_PATH
        self.default_context_id = default_context_id
        self._on_session_ready = on_session_ready
        self._lock = threading.Lock()
        self._conn = self._init_db()

    def _build_context_id(self, thread_id: str) -> str | None:
        if self.provider.name in ("agentbay", "docker"):
            return f"leon-{thread_id}"
        return None

    def _fire_session_ready(self, session_id: str, reason: str) -> None:
        if self._on_session_ready:
            self._on_session_ready(session_id, reason)

    def _init_db(self) -> sqlite3.Connection:
        """Create sandbox_sessions table if not exists. Returns persistent connection."""
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

    def close(self):
        """Close the persistent DB connection."""
        try:
            self._conn.close()
        except Exception:
            pass

    def get_or_create_session(self, thread_id: str) -> SessionInfo:
        """Get existing session for thread, or create new one."""
        existing = self._get_from_db(thread_id)

        if existing:
            if existing["provider"] != self.provider.name:
                self._delete_from_db(thread_id)
            else:
                session_id = existing["session_id"]
                status = self.provider.get_session_status(session_id)

                if status == "running":
                    self._update_last_active(thread_id)
                    return SessionInfo(
                        session_id=session_id,
                        provider=existing["provider"],
                        status="running",
                    )

                elif status == "paused":
                    if self.provider.resume_session(session_id):
                        self._update_status(thread_id, "running")
                        self._fire_session_ready(session_id, "resume")
                        return SessionInfo(
                            session_id=session_id,
                            provider=existing["provider"],
                            status="running",
                        )

                self._delete_from_db(thread_id)

        context_id = self._build_context_id(thread_id)
        info = self.provider.create_session(context_id=context_id)
        self._save_to_db(thread_id, info, context_id)
<<<<<<< HEAD
        # @@@ E2B: restore workspace files into new VM
        if self.provider.name == "e2b" and hasattr(self.provider, "restore_workspace"):
            snapshot = self._load_e2b_snapshot(thread_id)
            if snapshot:
                try:
                    self.provider.restore_workspace(info.session_id, snapshot)
                except Exception as e:
                    print(f"[SandboxManager] E2B restore failed: {e}")
=======
        self._fire_session_ready(info.session_id, "create")
>>>>>>> sandbox/workspace-init

        return info

    def get_session(self, thread_id: str) -> SessionInfo | None:
        """Get session info without creating."""
        existing = self._get_from_db(thread_id)
        if not existing:
            return None
        if existing["provider"] != self.provider.name:
            return None

        status = self.provider.get_session_status(existing["session_id"])
        return SessionInfo(
            session_id=existing["session_id"],
            provider=existing["provider"],
            status=status,
        )

    def has_session(self, thread_id: str) -> bool:
        """Check if thread has an active session."""
        return self._get_from_db(thread_id) is not None

    def pause_session(self, thread_id: str) -> bool:
        """Pause session for thread."""
        existing = self._get_from_db(thread_id)
        if not existing:
            return False
        if existing["provider"] != self.provider.name:
            return False

        if self.provider.pause_session(existing["session_id"]):
            self._update_status(thread_id, "paused")
            return True
        return False

    def resume_session(self, thread_id: str) -> bool:
        """Resume paused session for thread."""
        existing = self._get_from_db(thread_id)
        if not existing:
            return False
        if existing["provider"] != self.provider.name:
            return False

        if self.provider.resume_session(existing["session_id"]):
            self._update_status(thread_id, "running")
            self._fire_session_ready(existing["session_id"], "resume")
            return True
        return False

    def destroy_session(self, thread_id: str, sync: bool = True) -> bool:
        """Destroy session for thread."""
        existing = self._get_from_db(thread_id)
        if not existing:
            return False
        if existing["provider"] != self.provider.name:
            return False

        # @@@ E2B: snapshot workspace files before destroying VM
        if self.provider.name == "e2b" and hasattr(self.provider, "snapshot_workspace"):
            try:
                files = self.provider.snapshot_workspace(existing["session_id"])
                self._save_e2b_snapshot(thread_id, files)
            except Exception as e:
                print(f"[SandboxManager] E2B snapshot failed: {e}")

        if self.provider.destroy_session(existing["session_id"], sync=sync):
            self._delete_from_db(thread_id)
            return True
        return False

    def pause_all_sessions(self) -> int:
        """Pause all running sessions. Called on LEON exit."""
        count = 0
        for row in self._get_all_from_db():
            if row["provider"] != self.provider.name:
                continue
            status = self.provider.get_session_status(row["session_id"])
            if status in ("deleted", "unknown"):
                self._delete_from_db(row["thread_id"])
                continue
            if row["status"] == "running":
                try:
                    if self.provider.pause_session(row["session_id"]):
                        self._update_status(row["thread_id"], "paused")
                        count += 1
                except Exception as e:
                    message = str(e)
                    if "Session not found" in message:
                        self._delete_from_db(row["thread_id"])
                        continue
                    print(f"[SandboxManager] Failed to pause {row['session_id']}: {e}")
        return count

    def list_sessions(self) -> list[dict]:
        """List all tracked sessions with current status."""
        rows = [row for row in self._get_all_from_db() if row["provider"] == self.provider.name]
        if not rows:
            return []

        # @@@ Use batch status if provider supports it (1 API call vs N)
        if hasattr(self.provider, "get_all_session_statuses"):
            status_map = self.provider.get_all_session_statuses()
            sessions = []
            for row in rows:
                status = status_map.get(row["session_id"], "deleted")
                if status == "deleted":
                    self._delete_from_db(row["thread_id"])
                    continue
                sessions.append(
                    {
                        "thread_id": row["thread_id"],
                        "session_id": row["session_id"],
                        "provider": row["provider"],
                        "status": status,
                        "context_id": row["context_id"],
                        "created_at": row["created_at"],
                        "last_active": row["last_active"],
                    }
                )
            return sessions

        # Fallback: parallel per-session status checks
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=min(len(rows), 8)) as pool:
            statuses = list(
                pool.map(
                    lambda r: self.provider.get_session_status(r["session_id"]),
                    rows,
                )
            )

        sessions = []
        for row, status in zip(rows, statuses):
            if status == "deleted":
                self._delete_from_db(row["thread_id"])
                continue
            sessions.append(
                {
                    "thread_id": row["thread_id"],
                    "session_id": row["session_id"],
                    "provider": row["provider"],
                    "status": status,
                    "context_id": row["context_id"],
                    "created_at": row["created_at"],
                    "last_active": row["last_active"],
                }
            )
        return sessions

    def cleanup_stale_sessions(self) -> int:
        """Remove DB entries for sessions that no longer exist."""
        count = 0
        for row in self._get_all_from_db():
            if row["provider"] != self.provider.name:
                continue
            status = self.provider.get_session_status(row["session_id"])
            if status in ("deleted", "unknown"):
                self._delete_from_db(row["thread_id"])
                count += 1
        return count

    # ==================== DB Operations ====================

    def _get_from_db(self, thread_id: str) -> dict | None:
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            row = self._conn.execute(
                "SELECT * FROM sandbox_sessions WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
            return dict(row) if row else None

    def _get_all_from_db(self) -> list[dict]:
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            rows = self._conn.execute("SELECT * FROM sandbox_sessions").fetchall()
            return [dict(row) for row in rows]

    def _save_to_db(self, thread_id: str, info: SessionInfo, context_id: str | None):
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

    def _update_status(self, thread_id: str, status: str):
        with self._lock:
            self._conn.execute(
                "UPDATE sandbox_sessions SET status = ?, last_active = ? WHERE thread_id = ?",
                (status, datetime.now(), thread_id),
            )
            self._conn.commit()

    def _update_last_active(self, thread_id: str):
        with self._lock:
            self._conn.execute(
                "UPDATE sandbox_sessions SET last_active = ? WHERE thread_id = ?",
                (datetime.now(), thread_id),
            )
            self._conn.commit()

    def _delete_from_db(self, thread_id: str):
        with self._lock:
            self._conn.execute(
                "DELETE FROM sandbox_sessions WHERE thread_id = ?",
                (thread_id,),
            )
            self._conn.commit()

    def _save_e2b_snapshot(self, thread_id: str, files: list[dict]):
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

    def _load_e2b_snapshot(self, thread_id: str) -> list[dict]:
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            rows = self._conn.execute(
                "SELECT file_path, content FROM e2b_workspace_files WHERE thread_id = ?",
                (thread_id,),
            ).fetchall()
            return [{"file_path": row["file_path"], "content": row["content"]} for row in rows]
