"""ChatSession - Policy/lifecycle window for PhysicalTerminalRuntime.

This module implements the session abstraction that owns the ephemeral
runtime process and enforces lifecycle policies (idle timeout, max duration).

Architecture:
    Thread (durable) → ChatSession (policy window) → PhysicalTerminalRuntime (ephemeral)
                     → AbstractTerminal (reference)
                     → SandboxLease (reference)
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sandbox.lease import SandboxLease
    from sandbox.provider import SandboxProvider
    from sandbox.runtime import PhysicalTerminalRuntime
    from sandbox.terminal import AbstractTerminal

DEFAULT_DB_PATH = Path.home() / ".leon" / "leon.db"


@dataclass
class ChatSessionPolicy:
    """Policy configuration for ChatSession lifecycle."""

    idle_timeout_seconds: int = 3600  # 1 hour
    max_duration_seconds: int = 86400  # 24 hours


class ChatSession:
    """Policy/lifecycle window for PhysicalTerminalRuntime.

    Owns the ephemeral runtime process and enforces lifecycle policies.
    When the session expires, the runtime is closed but terminal state persists.

    Responsibilities:
    - Own PhysicalTerminalRuntime lifecycle
    - Enforce idle timeout and max duration policies
    - Track session activity (last_activity_at)
    - Provide runtime to callers

    Does NOT:
    - Own terminal state (that's AbstractTerminal)
    - Own compute resources (that's SandboxLease)
    - Persist beyond policy window
    """

    def __init__(
        self,
        session_id: str,
        thread_id: str,
        terminal: AbstractTerminal,
        lease: SandboxLease,
        runtime: PhysicalTerminalRuntime,
        policy: ChatSessionPolicy,
        created_at: datetime,
        last_activity_at: datetime,
    ):
        self.session_id = session_id
        self.thread_id = thread_id
        self.terminal = terminal
        self.lease = lease
        self.runtime = runtime
        self.policy = policy
        self.created_at = created_at
        self.last_activity_at = last_activity_at

    def is_expired(self) -> bool:
        """Check if session has expired based on policy."""
        now = datetime.now()

        # Check idle timeout
        idle_duration = now - self.last_activity_at
        if idle_duration.total_seconds() > self.policy.idle_timeout_seconds:
            return True

        # Check max duration
        total_duration = now - self.created_at
        if total_duration.total_seconds() > self.policy.max_duration_seconds:
            return True

        return False

    def touch(self) -> None:
        """Update last_activity_at to current time."""
        self.last_activity_at = datetime.now()

    async def close(self) -> None:
        """Close the runtime process."""
        await self.runtime.close()


class ChatSessionManager:
    """Manager for ChatSession lifecycle.

    Handles creation, retrieval, and cleanup of chat sessions.
    """

    def __init__(
        self,
        provider: SandboxProvider,
        db_path: Path = DEFAULT_DB_PATH,
        default_policy: ChatSessionPolicy | None = None,
    ):
        self.provider = provider
        self.db_path = db_path
        self.default_policy = default_policy or ChatSessionPolicy()
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Ensure chat_sessions table exists."""
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    thread_id TEXT UNIQUE NOT NULL,
                    terminal_id TEXT NOT NULL,
                    lease_id TEXT NOT NULL,
                    idle_timeout_seconds INTEGER NOT NULL,
                    max_duration_seconds INTEGER NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    last_activity_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (terminal_id) REFERENCES abstract_terminals(terminal_id),
                    FOREIGN KEY (lease_id) REFERENCES sandbox_leases(lease_id)
                )
                """
            )
            conn.commit()

    def get(self, thread_id: str) -> ChatSession | None:
        """Get active session for thread, or None if expired/missing."""
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT session_id, thread_id, terminal_id, lease_id,
                       idle_timeout_seconds, max_duration_seconds,
                       created_at, last_activity_at
                FROM chat_sessions
                WHERE thread_id = ?
                """,
                (thread_id,),
            ).fetchone()

            if not row:
                return None

            # Load terminal and lease
            from sandbox.lease import LeaseStore
            from sandbox.terminal import TerminalStore

            terminal_store = TerminalStore(db_path=self.db_path)
            lease_store = LeaseStore(db_path=self.db_path)

            terminal = terminal_store.get_by_id(row["terminal_id"])
            lease = lease_store.get(row["lease_id"])

            if not terminal or not lease:
                return None

            # Create runtime
            from sandbox.runtime import LocalPersistentShellRuntime, RemoteWrappedRuntime

            if self.provider.name == "local":
                runtime = LocalPersistentShellRuntime(terminal, lease)
            else:
                runtime = RemoteWrappedRuntime(terminal, lease, self.provider)

            policy = ChatSessionPolicy(
                idle_timeout_seconds=row["idle_timeout_seconds"],
                max_duration_seconds=row["max_duration_seconds"],
            )

            session = ChatSession(
                session_id=row["session_id"],
                thread_id=row["thread_id"],
                terminal=terminal,
                lease=lease,
                runtime=runtime,
                policy=policy,
                created_at=datetime.fromisoformat(row["created_at"]),
                last_activity_at=datetime.fromisoformat(row["last_activity_at"]),
            )

            # Check if expired
            if session.is_expired():
                # Clean up expired session
                self.delete(session.session_id)
                return None

            return session

    def create(
        self,
        session_id: str,
        thread_id: str,
        terminal: AbstractTerminal,
        lease: SandboxLease,
        policy: ChatSessionPolicy | None = None,
    ) -> ChatSession:
        """Create new chat session."""
        policy = policy or self.default_policy
        now = datetime.now()

        # Create runtime
        from sandbox.runtime import LocalPersistentShellRuntime, RemoteWrappedRuntime

        if self.provider.name == "local":
            runtime = LocalPersistentShellRuntime(terminal, lease)
        else:
            runtime = RemoteWrappedRuntime(terminal, lease, self.provider)

        # Persist to DB
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.execute(
                """
                INSERT INTO chat_sessions (
                    session_id, thread_id, terminal_id, lease_id,
                    idle_timeout_seconds, max_duration_seconds,
                    created_at, last_activity_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    thread_id,
                    terminal.terminal_id,
                    lease.lease_id,
                    policy.idle_timeout_seconds,
                    policy.max_duration_seconds,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            conn.commit()

        return ChatSession(
            session_id=session_id,
            thread_id=thread_id,
            terminal=terminal,
            lease=lease,
            runtime=runtime,
            policy=policy,
            created_at=now,
            last_activity_at=now,
        )

    def touch(self, session_id: str) -> None:
        """Update last_activity_at for session."""
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.execute(
                """
                UPDATE chat_sessions
                SET last_activity_at = ?
                WHERE session_id = ?
                """,
                (datetime.now().isoformat(), session_id),
            )
            conn.commit()

    def delete(self, session_id: str) -> None:
        """Delete session from DB."""
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.execute(
                "DELETE FROM chat_sessions WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()

    def list_all(self) -> list[dict]:
        """List all sessions."""
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT session_id, thread_id, terminal_id, lease_id,
                       created_at, last_activity_at
                FROM chat_sessions
                ORDER BY created_at DESC
                """
            ).fetchall()

            return [dict(row) for row in rows]

    def cleanup_expired(self) -> int:
        """Clean up expired sessions. Returns count of cleaned sessions."""
        sessions = self.list_all()
        count = 0

        for session_data in sessions:
            # Check expiry directly from DB data
            created_at = datetime.fromisoformat(session_data["created_at"])
            last_activity_at = datetime.fromisoformat(session_data["last_activity_at"])

            # Get policy from DB
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT idle_timeout_seconds, max_duration_seconds FROM chat_sessions WHERE session_id = ?",
                    (session_data["session_id"],),
                ).fetchone()

                if not row:
                    continue

                policy = ChatSessionPolicy(
                    idle_timeout_seconds=row["idle_timeout_seconds"],
                    max_duration_seconds=row["max_duration_seconds"],
                )

            now = datetime.now()
            idle_duration = now - last_activity_at
            total_duration = now - created_at

            is_expired = (
                idle_duration.total_seconds() > policy.idle_timeout_seconds
                or total_duration.total_seconds() > policy.max_duration_seconds
            )

            if is_expired:
                self.delete(session_data["session_id"])
                count += 1

        return count
