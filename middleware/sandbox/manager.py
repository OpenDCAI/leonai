"""
Sandbox session manager.

Tracks thread_id ↔ session_id mapping with SQLite persistence.
Handles lazy creation, auto-pause, and resume lifecycle.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

from middleware.sandbox.provider import SandboxProvider, SessionInfo


class SandboxManager:
    """
    Manages sandbox sessions across threads.

    Responsibilities:
    - Track thread_id ↔ session_id mapping
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
    ):
        """
        Initialize sandbox manager.

        Args:
            provider: Sandbox provider implementation
            db_path: Path to SQLite database (default: ~/.leon/leon.db)
            default_context_id: Default context for data persistence
        """
        self.provider = provider
        self.db_path = db_path or (Path.home() / ".leon" / "leon.db")
        self.default_context_id = default_context_id
        self._init_db()

    def _init_db(self):
        """Create sandbox_sessions table if not exists."""
        # Handle both Path and string (e.g., ':memory:')
        if isinstance(self.db_path, Path):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
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
            conn.commit()

    def get_or_create_session(self, thread_id: str) -> SessionInfo:
        """
        Get existing session for thread, or create new one.

        Automatically resumes paused sessions.

        Args:
            thread_id: LEON thread identifier

        Returns:
            SessionInfo with active session
        """
        # Check DB for existing session
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
                    # Resume paused session
                    if self.provider.resume_session(session_id):
                        self._update_status(thread_id, "running")
                        return SessionInfo(
                            session_id=session_id,
                            provider=existing["provider"],
                            status="running",
                        )

                # Session is gone or in bad state, clean up DB entry
                self._delete_from_db(thread_id)

        # Create new session
        context_id = self.default_context_id
        info = self.provider.create_session(context_id=context_id)
        self._save_to_db(thread_id, info, context_id)

        return info

    def get_session(self, thread_id: str) -> SessionInfo | None:
        """
        Get session info without creating.

        Args:
            thread_id: LEON thread identifier

        Returns:
            SessionInfo or None if no session exists
        """
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
        """
        Pause session for thread.

        Args:
            thread_id: LEON thread identifier

        Returns:
            True if successful
        """
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
        """
        Resume paused session for thread.

        Args:
            thread_id: LEON thread identifier

        Returns:
            True if successful
        """
        existing = self._get_from_db(thread_id)
        if not existing:
            return False
        if existing["provider"] != self.provider.name:
            return False

        if self.provider.resume_session(existing["session_id"]):
            self._update_status(thread_id, "running")
            return True
        return False

    def destroy_session(self, thread_id: str, sync: bool = True) -> bool:
        """
        Destroy session for thread.

        Args:
            thread_id: LEON thread identifier
            sync: If True, persist data before destruction

        Returns:
            True if successful
        """
        existing = self._get_from_db(thread_id)
        if not existing:
            return False
        if existing["provider"] != self.provider.name:
            return False

        if self.provider.destroy_session(existing["session_id"], sync=sync):
            self._delete_from_db(thread_id)
            return True
        return False

    def pause_all_sessions(self) -> int:
        """
        Pause all running sessions.

        Called on LEON exit.

        Returns:
            Number of sessions paused
        """
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
        """
        List all tracked sessions with current status.

        Returns:
            List of session info dicts
        """
        sessions = []
        for row in self._get_all_from_db():
            if row["provider"] != self.provider.name:
                continue
            status = self.provider.get_session_status(row["session_id"])
            sessions.append({
                "thread_id": row["thread_id"],
                "session_id": row["session_id"],
                "provider": row["provider"],
                "status": status,
                "context_id": row["context_id"],
                "created_at": row["created_at"],
                "last_active": row["last_active"],
            })
        return sessions

    def cleanup_stale_sessions(self) -> int:
        """
        Remove DB entries for sessions that no longer exist.

        Returns:
            Number of entries cleaned up
        """
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
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM sandbox_sessions WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
            return dict(row) if row else None

    def _get_all_from_db(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM sandbox_sessions").fetchall()
            return [dict(row) for row in rows]

    def _save_to_db(self, thread_id: str, info: SessionInfo, context_id: str | None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
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
            conn.commit()

    def _update_status(self, thread_id: str, status: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE sandbox_sessions SET status = ?, last_active = ? WHERE thread_id = ?",
                (status, datetime.now(), thread_id),
            )
            conn.commit()

    def _update_last_active(self, thread_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE sandbox_sessions SET last_active = ? WHERE thread_id = ?",
                (datetime.now(), thread_id),
            )
            conn.commit()

    def _delete_from_db(self, thread_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM sandbox_sessions WHERE thread_id = ?",
                (thread_id,),
            )
            conn.commit()
