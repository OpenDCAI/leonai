"""SandboxLease - Durable shared compute handle.

This module implements the lease abstraction that provides a stable handle
to sandbox compute resources that can be shared across multiple terminals.

Architecture:
    SandboxLease (durable handle) → SandboxInstance (ephemeral compute)

A lease can have 0 or 1 active instances. When an instance dies, the lease
can create a new one. Multiple terminals can share the same lease.
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sandbox.provider import SandboxProvider

DEFAULT_DB_PATH = Path.home() / ".leon" / "leon.db"


@dataclass
class SandboxInstance:
    """Ephemeral sandbox compute instance.

    Represents an active VM/container. Can be stopped/started/destroyed.
    When destroyed, the lease can create a new instance.
    """

    instance_id: str  # Provider's session_id
    provider_name: str
    status: str  # "running", "paused", "stopped"
    created_at: datetime


class SandboxLease(ABC):
    """Durable shared compute handle.

    Provides stable identity for sandbox compute that can outlive
    individual instances. Multiple terminals can share one lease.

    Responsibilities:
    - Maintain lease identity (lease_id, provider_name)
    - Track current instance (if any)
    - Create/recover instances on demand
    - Health check and recovery

    Does NOT:
    - Own terminal state (that's AbstractTerminal)
    - Own physical runtime process (that's PhysicalTerminalRuntime)
    """

    def __init__(
        self,
        lease_id: str,
        provider_name: str,
        current_instance: SandboxInstance | None = None,
    ):
        self.lease_id = lease_id
        self.provider_name = provider_name
        self._current_instance = current_instance

    def get_instance(self) -> SandboxInstance | None:
        """Get current active instance, if any."""
        return self._current_instance

    @abstractmethod
    def ensure_active_instance(self, provider: SandboxProvider) -> SandboxInstance:
        """Ensure there's an active instance, creating if needed.

        This is the convergence point:
        - If instance exists and healthy → return it
        - If instance dead/missing → create new one
        - Update lease state in DB

        Args:
            provider: SandboxProvider to use for instance operations

        Returns:
            Active SandboxInstance
        """
        ...

    @abstractmethod
    def destroy_instance(self, provider: SandboxProvider) -> None:
        """Destroy current instance and clear lease state."""
        ...

    @abstractmethod
    def pause_instance(self, provider: SandboxProvider) -> bool:
        """Pause current instance if supported."""
        ...

    @abstractmethod
    def resume_instance(self, provider: SandboxProvider) -> bool:
        """Resume paused instance if supported."""
        ...


class SQLiteLease(SandboxLease):
    """SQLite-backed lease implementation."""

    def __init__(
        self,
        lease_id: str,
        provider_name: str,
        current_instance: SandboxInstance | None = None,
        db_path: Path = DEFAULT_DB_PATH,
    ):
        super().__init__(lease_id, provider_name, current_instance)
        self.db_path = db_path

    def ensure_active_instance(self, provider: SandboxProvider) -> SandboxInstance:
        """Ensure active instance exists."""
        # Check if current instance is healthy
        if self._current_instance:
            try:
                status = provider.get_session_status(self._current_instance.instance_id)
                if status == "running":
                    return self._current_instance
                elif status == "paused":
                    # Try to resume
                    if provider.resume_session(self._current_instance.instance_id):
                        self._current_instance.status = "running"
                        self._persist_instance()
                        return self._current_instance
            except Exception:
                # Instance is dead, need to create new one
                pass

        # Create new instance
        session_info = provider.create_session(context_id=f"leon-{self.lease_id}")
        instance = SandboxInstance(
            instance_id=session_info.session_id,
            provider_name=self.provider_name,
            status="running",
            created_at=datetime.now(),
        )
        self._current_instance = instance
        self._persist_instance()
        return instance

    def destroy_instance(self, provider: SandboxProvider) -> None:
        """Destroy current instance."""
        if self._current_instance:
            try:
                provider.destroy_session(self._current_instance.instance_id)
            except Exception:
                pass  # Already destroyed
            self._current_instance = None
            self._clear_instance()

    def pause_instance(self, provider: SandboxProvider) -> bool:
        """Pause current instance."""
        if not self._current_instance:
            return False

        try:
            if provider.pause_session(self._current_instance.instance_id):
                self._current_instance.status = "paused"
                self._persist_instance()
                return True
        except Exception:
            pass
        return False

    def resume_instance(self, provider: SandboxProvider) -> bool:
        """Resume paused instance."""
        if not self._current_instance:
            return False

        try:
            if provider.resume_session(self._current_instance.instance_id):
                self._current_instance.status = "running"
                self._persist_instance()
                return True
        except Exception:
            pass
        return False

    def _persist_instance(self) -> None:
        """Persist current instance to DB."""
        if not self._current_instance:
            return

        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.execute(
                """
                UPDATE sandbox_leases
                SET current_instance_id = ?, instance_status = ?, instance_created_at = ?, updated_at = ?
                WHERE lease_id = ?
                """,
                (
                    self._current_instance.instance_id,
                    self._current_instance.status,
                    self._current_instance.created_at.isoformat(),
                    datetime.now().isoformat(),
                    self.lease_id,
                ),
            )
            conn.commit()

    def _clear_instance(self) -> None:
        """Clear instance from DB."""
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.execute(
                """
                UPDATE sandbox_leases
                SET current_instance_id = NULL, instance_status = NULL, instance_created_at = NULL, updated_at = ?
                WHERE lease_id = ?
                """,
                (datetime.now().isoformat(), self.lease_id),
            )
            conn.commit()


class LeaseStore:
    """Store for managing SandboxLease persistence."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Ensure sandbox_leases table exists."""
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sandbox_leases (
                    lease_id TEXT PRIMARY KEY,
                    provider_name TEXT NOT NULL,
                    current_instance_id TEXT,
                    instance_status TEXT,
                    instance_created_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
                """
            )
            conn.commit()

    def get(self, lease_id: str) -> SandboxLease | None:
        """Get lease by lease_id."""
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT lease_id, provider_name, current_instance_id, instance_status, instance_created_at
                FROM sandbox_leases
                WHERE lease_id = ?
                """,
                (lease_id,),
            ).fetchone()

            if not row:
                return None

            instance = None
            if row["current_instance_id"]:
                instance = SandboxInstance(
                    instance_id=row["current_instance_id"],
                    provider_name=row["provider_name"],
                    status=row["instance_status"],
                    created_at=datetime.fromisoformat(row["instance_created_at"]),
                )

            return SQLiteLease(
                lease_id=row["lease_id"],
                provider_name=row["provider_name"],
                current_instance=instance,
                db_path=self.db_path,
            )

    def create(
        self,
        lease_id: str,
        provider_name: str,
    ) -> SandboxLease:
        """Create new lease."""
        now = datetime.now().isoformat()

        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.execute(
                """
                INSERT INTO sandbox_leases (lease_id, provider_name, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (lease_id, provider_name, now, now),
            )
            conn.commit()

        return SQLiteLease(
            lease_id=lease_id,
            provider_name=provider_name,
            current_instance=None,
            db_path=self.db_path,
        )

    def delete(self, lease_id: str) -> None:
        """Delete lease."""
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.execute(
                "DELETE FROM sandbox_leases WHERE lease_id = ?",
                (lease_id,),
            )
            conn.commit()

    def list_all(self) -> list[dict]:
        """List all leases."""
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT lease_id, provider_name, current_instance_id, instance_status, created_at, updated_at
                FROM sandbox_leases
                ORDER BY created_at DESC
                """
            ).fetchall()

            return [dict(row) for row in rows]

    def list_by_provider(self, provider_name: str) -> list[dict]:
        """List all leases for a provider."""
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT lease_id, provider_name, current_instance_id, instance_status, created_at, updated_at
                FROM sandbox_leases
                WHERE provider_name = ?
                ORDER BY created_at DESC
                """,
                (provider_name,),
            ).fetchall()

            return [dict(row) for row in rows]
