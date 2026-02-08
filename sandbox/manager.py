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

from sandbox.capability import SandboxCapability
from sandbox.chat_session import ChatSessionManager, ChatSessionPolicy
from sandbox.lease import LeaseStore
from sandbox.provider import SandboxProvider
from sandbox.session_store import SessionStore
from sandbox.sqlite_store import DEFAULT_DB_PATH, SQLiteSessionStore
from sandbox.terminal import TerminalStore


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
            # Check new architecture first
            row = conn.execute(
                """
                SELECT sl.provider_name
                FROM chat_sessions cs
                JOIN abstract_terminals at ON cs.terminal_id = at.terminal_id
                JOIN sandbox_leases sl ON at.lease_id = sl.lease_id
                WHERE cs.thread_id = ?
                """,
                (thread_id,),
            ).fetchone()
            if row:
                return row[0]

            # Fallback to legacy
            row = conn.execute(
                "SELECT provider FROM sandbox_sessions WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
            return row[0] if row else None
    except Exception:
        return None


class SandboxManager:
    """
    Manages sandbox sessions across threads - NEW ARCHITECTURE.

    Responsibilities:
    - Orchestrate thread_id → ChatSession → Runtime → Terminal → Lease
    - Provide SandboxCapability to agents
    - Handle session lifecycle (create, resume, cleanup)
    - Maintain backward compatibility with legacy API

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
        store: SessionStore | None = None,
        db_path: Path | None = None,
        default_context_id: str | None = None,
        on_session_ready: Callable[[str, str], None] | None = None,
    ):
        self.provider = provider
        self.store = store or SQLiteSessionStore(db_path)
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

    def _fire_session_ready(self, session_id: str, reason: str) -> None:
        if self._on_session_ready:
            self._on_session_ready(session_id, reason)

    def close(self):
        self.store.close()

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
            # Use a safe default cwd that exists
            import os
            initial_cwd = os.path.expanduser("~")

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

    # Legacy API compatibility methods below

    def get_or_create_session(self, thread_id: str):
        """Legacy API - returns SessionInfo for backward compatibility."""
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
        if not session:
            return False

        from sandbox.runtime import RemoteWrappedRuntime
        if isinstance(session.runtime, RemoteWrappedRuntime):
            return session.lease.pause_instance(session.runtime.provider)
        return False

    def resume_session(self, thread_id: str) -> bool:
        """Resume session for thread."""
        session = self.session_manager.get(thread_id)
        if not session:
            return False

        from sandbox.runtime import RemoteWrappedRuntime
        if isinstance(session.runtime, RemoteWrappedRuntime):
            return session.lease.resume_instance(session.runtime.provider)
        return False

    def pause_all_sessions(self) -> int:
        """Pause all active sessions."""
        sessions = self.session_manager.list_all()
        count = 0

        for session_data in sessions:
            if self.pause_session(session_data["thread_id"]):
                count += 1

        return count

    def destroy_session(self, thread_id: str, session_id: str | None = None) -> None:
        """Destroy session and clean up resources."""
        session = self.session_manager.get(thread_id)
        if session:
            from sandbox.runtime import RemoteWrappedRuntime
            if isinstance(session.runtime, RemoteWrappedRuntime):
                session.lease.destroy_instance(session.runtime.provider)
            self.session_manager.delete(session.session_id)

    def list_sessions(self) -> list[dict]:
        """List all sessions."""
        return self.session_manager.list_all()
