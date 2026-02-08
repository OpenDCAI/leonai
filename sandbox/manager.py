"""
Sandbox session manager.

Tracks thread_id <-> session_id mapping via SessionStore.
Handles lazy creation, auto-pause, and resume lifecycle.
"""

from collections.abc import Callable
from pathlib import Path

from sandbox.provider import SandboxProvider, SessionInfo
from sandbox.session_store import SessionStore
from sandbox.sqlite_store import DEFAULT_DB_PATH, SQLiteSessionStore


def lookup_sandbox_for_thread(thread_id: str) -> str | None:
    """Check if a thread has a sandbox session in the DB.

    Returns provider name ('agentbay', 'e2b', 'docker', 'daytona') or None.
    Pure SQLite lookup — no provider initialization needed.
    """
    import sqlite3

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
    - Track thread_id <-> session_id mapping (via SessionStore)
    - Handle lazy creation and auto-pause lifecycle
    - Delegate persistence to the injected store

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
        store: SessionStore | None = None,
        db_path: Path | None = None,
        default_context_id: str | None = None,
        on_session_ready: Callable[[str, str], None] | None = None,
    ):
        self.provider = provider
        self.store = store or SQLiteSessionStore(db_path)
        self.default_context_id = default_context_id
        self._on_session_ready = on_session_ready

    def _build_context_id(self, thread_id: str) -> str | None:
        if self.provider.name in ("agentbay", "docker"):
            return f"leon-{thread_id}"
        return None

    def _fire_session_ready(self, session_id: str, reason: str) -> None:
        if self._on_session_ready:
            self._on_session_ready(session_id, reason)

    def close(self):
        self.store.close()

    def get_or_create_session(self, thread_id: str) -> SessionInfo:
        """Get existing session for thread, or create new one."""
        existing = self.store.get(thread_id)

        if existing:
            if existing["provider"] != self.provider.name:
                self.store.delete(thread_id)
            else:
                session_id = existing["session_id"]
                status = self.provider.get_session_status(session_id)

                if status == "running":
                    self.store.touch(thread_id)
                    return SessionInfo(
                        session_id=session_id,
                        provider=existing["provider"],
                        status="running",
                    )

                elif status == "paused":
                    if self.provider.resume_session(session_id):
                        self.store.update_status(thread_id, "running")
                        self._fire_session_ready(session_id, "resume")
                        return SessionInfo(
                            session_id=session_id,
                            provider=existing["provider"],
                            status="running",
                        )

                self.store.delete(thread_id)

        context_id = self._build_context_id(thread_id)
        info = self.provider.create_session(context_id=context_id)
        self.store.save(thread_id, info, context_id)
        # @@@ E2B legacy: restore workspace files into new VM
        if self.provider.name == "e2b" and hasattr(self.provider, "restore_workspace"):
            if hasattr(self.store, "load_e2b_snapshot"):
                snapshot = self.store.load_e2b_snapshot(thread_id)
                if snapshot:
                    try:
                        self.provider.restore_workspace(info.session_id, snapshot)
                    except Exception as e:
                        print(f"[SandboxManager] E2B restore failed: {e}")
        self._fire_session_ready(info.session_id, "create")

        return info

    def get_session(self, thread_id: str) -> SessionInfo | None:
        """Get session info without creating."""
        existing = self.store.get(thread_id)
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
        return self.store.get(thread_id) is not None

    def pause_session(self, thread_id: str) -> bool:
        """Pause session for thread."""
        existing = self.store.get(thread_id)
        if not existing:
            return False
        if existing["provider"] != self.provider.name:
            return False

        if self.provider.pause_session(existing["session_id"]):
            self.store.update_status(thread_id, "paused")
            return True
        return False

    def resume_session(self, thread_id: str) -> bool:
        """Resume paused session for thread."""
        existing = self.store.get(thread_id)
        if not existing:
            return False
        if existing["provider"] != self.provider.name:
            return False

        if self.provider.resume_session(existing["session_id"]):
            self.store.update_status(thread_id, "running")
            self._fire_session_ready(existing["session_id"], "resume")
            return True
        return False

    def destroy_session(self, thread_id: str = "", session_id: str = "", sync: bool = True) -> bool:
        """Destroy session by thread_id or session_id."""
        if thread_id:
            existing = self.store.get(thread_id)
            if not existing or existing["provider"] != self.provider.name:
                return False
            session_id = existing["session_id"]

            # @@@ E2B legacy: snapshot workspace files before destroying VM
            if self.provider.name == "e2b" and hasattr(self.provider, "snapshot_workspace"):
                if hasattr(self.store, "save_e2b_snapshot"):
                    try:
                        files = self.provider.snapshot_workspace(session_id)
                        self.store.save_e2b_snapshot(thread_id, files)
                    except Exception as e:
                        print(f"[SandboxManager] E2B snapshot failed: {e}")

            if self.provider.destroy_session(session_id, sync=sync):
                self.store.delete(thread_id)
                return True
            return False

        if session_id:
            return self.provider.destroy_session(session_id, sync=sync)

        return False

    def pause_all_sessions(self) -> int:
        """Pause all running sessions. Called on LEON exit."""
        count = 0
        for row in self.store.get_all():
            if row["provider"] != self.provider.name:
                continue
            status = self.provider.get_session_status(row["session_id"])
            if status in ("deleted", "unknown"):
                self.store.delete(row["thread_id"])
                continue
            if row["status"] == "running":
                try:
                    if self.provider.pause_session(row["session_id"]):
                        self.store.update_status(row["thread_id"], "paused")
                        count += 1
                except Exception as e:
                    message = str(e)
                    if "Session not found" in message:
                        self.store.delete(row["thread_id"])
                        continue
                    print(f"[SandboxManager] Failed to pause {row['session_id']}: {e}")
        return count

    def list_sessions(self) -> list[dict]:
        """List all tracked sessions with current status.

        If the provider supports list_provider_sessions(), also discovers
        orphaned sessions not in the local DB.
        """
        rows = [row for row in self.store.get_all() if row["provider"] == self.provider.name]

        # @@@ Providers with list_provider_sessions() can discover orphans
        if hasattr(self.provider, "list_provider_sessions"):
            api_sessions = self.provider.list_provider_sessions()
            api_map = {s.session_id: s.status for s in api_sessions}

            sessions = []
            for row in rows:
                status = api_map.pop(row["session_id"], "deleted")
                if status == "deleted":
                    self.store.delete(row["thread_id"])
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
            for sid, status in api_map.items():
                sessions.append(
                    {
                        "thread_id": "",
                        "session_id": sid,
                        "provider": self.provider.name,
                        "status": status,
                        "context_id": None,
                        "created_at": None,
                        "last_active": None,
                    }
                )
            return sessions

        # Batch status via get_all_session_statuses (1 API call vs N)
        if rows and hasattr(self.provider, "get_all_session_statuses"):
            status_map = self.provider.get_all_session_statuses()
            sessions = []
            for row in rows:
                status = status_map.get(row["session_id"], "deleted")
                if status == "deleted":
                    self.store.delete(row["thread_id"])
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

        if not rows:
            return []

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
                self.store.delete(row["thread_id"])
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
        for row in self.store.get_all():
            if row["provider"] != self.provider.name:
                continue
            status = self.provider.get_session_status(row["session_id"])
            if status in ("deleted", "unknown"):
                self.store.delete(row["thread_id"])
                count += 1
        return count
