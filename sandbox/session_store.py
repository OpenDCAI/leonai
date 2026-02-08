"""
SessionStore — persistence layer for sandbox session tracking.

Extracted from SandboxManager to separate lifecycle policy from I/O.
"""

from abc import ABC, abstractmethod

from sandbox.provider import SessionInfo


class SessionStore(ABC):
    """Abstract interface for session persistence.

    Implementations: SQLiteSessionStore (local), RemoteSessionStore (HTTP).
    """

    @abstractmethod
    def get(self, thread_id: str) -> dict | None:
        """Get session record by thread_id. Returns dict with all columns or None."""

    @abstractmethod
    def get_all(self) -> list[dict]:
        """Get all session records."""

    @abstractmethod
    def save(self, thread_id: str, info: SessionInfo, context_id: str | None) -> None:
        """Save or replace a session record."""

    @abstractmethod
    def update_status(self, thread_id: str, status: str) -> None:
        """Update session status and last_active timestamp."""

    @abstractmethod
    def touch(self, thread_id: str) -> None:
        """Update last_active timestamp only."""

    @abstractmethod
    def delete(self, thread_id: str) -> None:
        """Delete session record by thread_id."""

    @abstractmethod
    def close(self) -> None:
        """Release resources (DB connections, etc.)."""
