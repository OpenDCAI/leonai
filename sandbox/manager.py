"""
Sandbox session manager.

Orchestrates: Thread → ChatSession → Runtime → Terminal → Lease → Instance

Architecture:
- Thread (durable) → ChatSession (policy window) → Runtime (ephemeral)
- Runtime references Terminal (state) + Lease (compute)
- Lease manages Instance (ephemeral VM/container)
"""

from collections.abc import Callable
from pathlib import Path
import uuid
import os

from sandbox.capability import SandboxCapability
from sandbox.chat_session import ChatSessionManager, ChatSessionPolicy
from sandbox.db import DEFAULT_DB_PATH
from sandbox.lease import LeaseStore
from sandbox.provider import SandboxProvider
from sandbox.terminal import TerminalStore


def lookup_sandbox_for_thread(thread_id: str, db_path: Path | None = None) -> str | None:
    """Check if a thread has a sandbox session in the DB.

    Returns provider name ('agentbay', 'e2b', 'docker', 'daytona') or None.
    Pure SQLite lookup — no provider initialization needed.
    """
    import sqlite3

    target_db = db_path or DEFAULT_DB_PATH
    if not target_db.exists():
        return None
    with sqlite3.connect(str(target_db), timeout=5) as conn:
        existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "abstract_terminals" not in existing or "sandbox_leases" not in existing:
            return None
        row = conn.execute(
            """
            SELECT sl.provider_name
            FROM abstract_terminals at
            JOIN sandbox_leases sl ON at.lease_id = sl.lease_id
            WHERE at.thread_id = ?
            LIMIT 1
            """,
            (thread_id,),
        ).fetchone()
        if row:
            return row[0]
        return None


class SandboxManager:
    """
    Manages sandbox sessions across threads - NEW ARCHITECTURE.

    Responsibilities:
    - Orchestrate thread_id → ChatSession → Runtime → Terminal → Lease
    - Provide SandboxCapability to agents
    - Handle session lifecycle (create, resume, cleanup)

    New Flow:
    1. get_sandbox(thread_id) → SandboxCapability
    2. Capability wraps ChatSession
    3. ChatSession owns Runtime
    4. Runtime references Terminal + Lease
    5. Lease manages Instance
    """

    def __init__(
        self,
        provider: SandboxProvider,
        db_path: Path | None = None,
        default_context_id: str | None = None,
        on_session_ready: Callable[[str, str], None] | None = None,
    ):
        self.provider = provider
        self.default_context_id = default_context_id
        self._on_session_ready = on_session_ready

        # New architecture stores
        self.db_path = db_path or DEFAULT_DB_PATH
        self.terminal_store = TerminalStore(db_path=self.db_path)
        self.lease_store = LeaseStore(db_path=self.db_path)
        self.session_manager = ChatSessionManager(
            provider=provider,
            db_path=self.db_path,
            default_policy=ChatSessionPolicy(),
        )

    def _build_context_id(self, thread_id: str) -> str | None:
        if self.provider.name in ("agentbay", "docker"):
            return f"leon-{thread_id}"
        return None

    def _default_terminal_cwd(self) -> str:
        """Resolve provider-appropriate initial cwd for terminal state."""
        if self.provider.name == "local":
            return os.path.expanduser("~")
        if hasattr(self.provider, "default_cwd"):
            value = getattr(self.provider, "default_cwd")
            if isinstance(value, str) and value:
                return value
        if hasattr(self.provider, "default_context_path"):
            value = getattr(self.provider, "default_context_path")
            if isinstance(value, str) and value:
                return value
        if hasattr(self.provider, "mount_path"):
            value = getattr(self.provider, "mount_path")
            if isinstance(value, str) and value:
                return value
        return "/home/user"

    def _fire_session_ready(self, session_id: str, reason: str) -> None:
        if self._on_session_ready:
            self._on_session_ready(session_id, reason)

    def close(self):
        return None

    def get_sandbox(self, thread_id: str) -> SandboxCapability:
        """Get sandbox capability for thread (NEW ARCHITECTURE).

        This is the main entry point for agents. Returns a capability object
        that wraps the new architecture while maintaining the same interface.

        Flow:
        1. Check if ChatSession exists for thread
        2. If not, create: Terminal → Lease → Runtime → ChatSession
        3. Wrap in SandboxCapability
        4. Return to agent
        """
        # Try to get existing session
        session = self.session_manager.get(thread_id)

        if session:
            # Session exists and not expired
            return SandboxCapability(session)

        # Create new session
        # 1. Create or get terminal
        terminal = self.terminal_store.get(thread_id)
        if not terminal:
            # Create new terminal + lease
            terminal_id = f"term-{uuid.uuid4().hex[:12]}"
            lease_id = f"lease-{uuid.uuid4().hex[:12]}"

            lease = self.lease_store.create(lease_id, self.provider.name)
            initial_cwd = self._default_terminal_cwd()

            terminal = self.terminal_store.create(
                terminal_id=terminal_id,
                thread_id=thread_id,
                lease_id=lease_id,
                initial_cwd=initial_cwd,
            )
        else:
            # Terminal exists, get its lease
            lease = self.lease_store.get(terminal.lease_id)
            if not lease:
                # Lease missing, create new one
                lease = self.lease_store.create(terminal.lease_id, self.provider.name)

        # 2. Create ChatSession (which creates Runtime)
        session_id = f"sess-{uuid.uuid4().hex[:12]}"
        session = self.session_manager.create(
            session_id=session_id,
            thread_id=thread_id,
            terminal=terminal,
            lease=lease,
        )

        # 3. Fire session ready callback if configured
        instance = lease.get_instance()
        if instance:
            self._fire_session_ready(instance.instance_id, "create")

        return SandboxCapability(session)

    def get_or_create_session(self, thread_id: str):
        """Return provider SessionInfo for current thread lease instance."""
        from sandbox.provider import SessionInfo

        capability = self.get_sandbox(thread_id)
        instance = capability._session.lease.get_instance()

        if not instance:
            # Ensure instance exists
            from sandbox.runtime import RemoteWrappedRuntime
            if isinstance(capability._session.runtime, RemoteWrappedRuntime):
                instance = capability._session.lease.ensure_active_instance(
                    capability._session.runtime.provider
                )

        return SessionInfo(
            session_id=instance.instance_id if instance else "local",
            provider=self.provider.name,
            status="running",
        )

    def pause_session(self, thread_id: str) -> bool:
        """Pause session for thread."""
        session = self.session_manager.get(thread_id)
        if session and session.status != "paused":
            self.session_manager.pause(session.session_id)

        terminal = self.terminal_store.get(thread_id)
        if not terminal:
            return False
        lease = self.lease_store.get(terminal.lease_id)
        if not lease:
            return False

        if self.provider.name == "local":
            return True
        return lease.pause_instance(self.provider)

    def _get_thread_lease(self, thread_id: str):
        terminal = self.terminal_store.get(thread_id)
        if not terminal:
            return None
        return self.lease_store.get(terminal.lease_id)

    def _ensure_chat_session(self, thread_id: str) -> None:
        if self.session_manager.get(thread_id):
            return
        self.get_sandbox(thread_id)

    def resume_session(self, thread_id: str) -> bool:
        """Resume session for thread."""
        lease = self._get_thread_lease(thread_id)
        if not lease:
            return False
        if self.provider.name != "local":
            resumed = lease.resume_instance(self.provider)
            if not resumed:
                return False
        session = self.session_manager.get(thread_id)
        if session:
            self.session_manager.resume(session.session_id)
        else:
            self._ensure_chat_session(thread_id)
        return True

    def pause_all_sessions(self) -> int:
        """Pause all active sessions."""
        sessions = self.session_manager.list_all()
        count = 0

        for session_data in sessions:
            if self.pause_session(session_data["thread_id"]):
                count += 1

        return count

    def destroy_session(self, thread_id: str, session_id: str | None = None) -> bool:
        """Destroy session and clean up resources."""
        session = self.session_manager.get(thread_id)
        if session:
            self.session_manager.delete(session.session_id)

        terminal = self.terminal_store.get(thread_id)
        if not terminal:
            return False
        lease = self.lease_store.get(terminal.lease_id)
        if not lease:
            return False
        if self.provider.name != "local":
            lease.destroy_instance(self.provider)
        return True

    def list_sessions(self) -> list[dict]:
        """List sessions with ground-truth focus (lease/provider first, chat-session second)."""
        sessions: list[dict] = []

        # Build helper maps for thread/session metadata.
        terminals = self.terminal_store.list_all()
        threads_by_lease: dict[str, list[str]] = {}
        for term in terminals:
            lease_id = term.get("lease_id")
            thread_id = term.get("thread_id")
            if not lease_id or not thread_id:
                continue
            threads_by_lease.setdefault(lease_id, []).append(thread_id)

        rows = self.session_manager.list_all()
        active_rows = [r for r in rows if r.get("status") in {"active", "idle", "paused"}]
        chat_by_thread: dict[str, dict] = {row["thread_id"]: row for row in active_rows if row.get("thread_id")}

        if self.provider.name == "local":
            for row in active_rows:
                sessions.append(
                    {
                        "session_id": row["session_id"],
                        "thread_id": row["thread_id"],
                        "provider": self.provider.name,
                        "status": row["status"],
                        "created_at": row.get("started_at"),
                        "last_active": row.get("last_active_at"),
                        "lease_id": row.get("lease_id"),
                        "instance_id": None,
                        "chat_session_id": row.get("session_id"),
                        "source": "chat_session",
                    }
                )
            return sessions

        seen_instance_ids: set[str] = set()

        # @@@ground-truth-lease-view - Inspect must show real machine occupancy even if chat session is absent/expired.
        for lease_row in self.lease_store.list_by_provider(self.provider.name):
            lease_id = lease_row["lease_id"]
            lease = self.lease_store.get(lease_id)
            if not lease:
                continue
            instance = lease.get_instance()
            if not instance:
                continue

            status = lease.refresh_instance_status(self.provider)
            refreshed_instance = lease.get_instance()
            if not refreshed_instance:
                continue
            if status in {"detached", "deleted", "stopped", "dead"}:
                continue

            seen_instance_ids.add(refreshed_instance.instance_id)
            threads = sorted(set(threads_by_lease.get(lease_id) or []))
            if not threads:
                sessions.append(
                    {
                        "session_id": refreshed_instance.instance_id,
                        "thread_id": "(untracked)",
                        "provider": self.provider.name,
                        "status": status,
                        "created_at": lease_row.get("created_at"),
                        "last_active": lease_row.get("updated_at"),
                        "lease_id": lease_id,
                        "instance_id": refreshed_instance.instance_id,
                        "chat_session_id": None,
                        "source": "lease",
                    }
                )
                continue

            for thread_id in threads:
                chat = chat_by_thread.get(thread_id)
                sessions.append(
                    {
                        "session_id": refreshed_instance.instance_id,
                        "thread_id": thread_id,
                        "provider": self.provider.name,
                        "status": status,
                        "created_at": lease_row.get("created_at"),
                        "last_active": (chat or {}).get("last_active_at") or lease_row.get("updated_at"),
                        "lease_id": lease_id,
                        "instance_id": refreshed_instance.instance_id,
                        "chat_session_id": (chat or {}).get("session_id"),
                        "source": "lease",
                    }
                )

        # Provider orphan resources (machine exists but no DB lease).
        if hasattr(self.provider, "list_provider_sessions"):
            try:
                provider_sessions = self.provider.list_provider_sessions() or []
            except Exception:
                provider_sessions = []
            for ps in provider_sessions:
                instance_id = getattr(ps, "session_id", None)
                status = getattr(ps, "status", None) or "unknown"
                if not instance_id or status in {"deleted", "dead", "stopped"}:
                    continue
                if instance_id in seen_instance_ids:
                    continue
                sessions.append(
                    {
                        "session_id": instance_id,
                        "thread_id": "(orphan)",
                        "provider": self.provider.name,
                        "status": status,
                        "created_at": None,
                        "last_active": None,
                        "lease_id": None,
                        "instance_id": instance_id,
                        "chat_session_id": None,
                        "source": "provider_orphan",
                    }
                )

        return sessions
