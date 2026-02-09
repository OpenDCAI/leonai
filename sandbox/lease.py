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
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sandbox.db import DEFAULT_DB_PATH

if TYPE_CHECKING:
    from sandbox.provider import SandboxProvider

LEASE_FRESHNESS_TTL_SEC = 3.0

REQUIRED_LEASE_COLUMNS = {
    "lease_id",
    "provider_name",
    "workspace_key",
    "current_instance_id",
    "instance_status",
    "instance_created_at",
    "observed_at",
    "refresh_error",
    "needs_refresh",
    "refresh_hint_at",
    "status",
    "created_at",
    "updated_at",
}
REQUIRED_INSTANCE_COLUMNS = {
    "instance_id",
    "lease_id",
    "provider_session_id",
    "status",
    "created_at",
    "last_seen_at",
}


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


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
        status: str = "active",
        workspace_key: str | None = None,
        observed_at: datetime | None = None,
        refresh_error: str | None = None,
        needs_refresh: bool = False,
        refresh_hint_at: datetime | None = None,
    ):
        self.lease_id = lease_id
        self.provider_name = provider_name
        self._current_instance = current_instance
        self.status = status
        self.workspace_key = workspace_key
        self.observed_at = observed_at
        self.refresh_error = refresh_error
        self.needs_refresh = needs_refresh
        self.refresh_hint_at = refresh_hint_at

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

    @abstractmethod
    def refresh_instance_status(
        self,
        provider: SandboxProvider,
        *,
        force: bool = False,
        max_age_sec: float = LEASE_FRESHNESS_TTL_SEC,
    ) -> str:
        """Refresh status from provider and converge persisted lease state.

        Returns one of: running, paused, detached, unknown.
        """
        ...

    @abstractmethod
    def mark_needs_refresh(self, hint_at: datetime | None = None) -> None:
        """Mark lease snapshot invalidated; next read/run must force provider refresh."""
        ...


class SQLiteLease(SandboxLease):
    """SQLite-backed lease implementation."""

    _lock_guard = threading.Lock()
    _lease_locks: dict[str, threading.Lock] = {}

    def __init__(
        self,
        lease_id: str,
        provider_name: str,
        current_instance: SandboxInstance | None = None,
        db_path: Path = DEFAULT_DB_PATH,
        status: str = "active",
        workspace_key: str | None = None,
        observed_at: datetime | None = None,
        refresh_error: str | None = None,
        needs_refresh: bool = False,
        refresh_hint_at: datetime | None = None,
    ):
        super().__init__(
            lease_id=lease_id,
            provider_name=provider_name,
            current_instance=current_instance,
            status=status,
            workspace_key=workspace_key,
            observed_at=observed_at,
            refresh_error=refresh_error,
            needs_refresh=needs_refresh,
            refresh_hint_at=refresh_hint_at,
        )
        self.db_path = db_path

    def _is_fresh(self, max_age_sec: float = LEASE_FRESHNESS_TTL_SEC) -> bool:
        if not self.observed_at:
            return False
        return (datetime.now() - self.observed_at).total_seconds() <= max_age_sec

    def _record_refresh_error(self, error: str) -> None:
        self.refresh_error = error[:500]
        self._persist_lease_metadata()

    def ensure_active_instance(self, provider: SandboxProvider) -> SandboxInstance:
        """Ensure active instance exists."""
        # Check if current instance is healthy
        if self._current_instance:
            if self._current_instance.status == "running" and self._is_fresh() and not self.needs_refresh:
                return self._current_instance
            try:
                status = provider.get_session_status(self._current_instance.instance_id)
                self.observed_at = datetime.now()
                had_refresh_error = self.refresh_error is not None
                self.refresh_error = None
                self.needs_refresh = False
                self.refresh_hint_at = None
                if status == "running":
                    # @@@status-convergence - Provider is source of truth; converge persisted lease state immediately.
                    if self._current_instance.status != "running" or had_refresh_error:
                        self._current_instance.status = "running"
                        self._persist_instance()
                    else:
                        self._persist_lease_metadata()
                    return self._current_instance
                elif status == "paused":
                    if self._current_instance.status != "paused":
                        self._current_instance.status = "paused"
                        self._persist_instance()
                    raise RuntimeError(f"Sandbox lease {self.lease_id} is paused. Resume before executing commands.")
            except RuntimeError:
                raise
            except Exception as e:
                self._record_refresh_error(str(e))
                # Instance is dead, need to create new one
                pass

        with self._instance_lock():
            # Re-check persisted pointer after acquiring lock (winner-takes-recovery).
            refreshed = LeaseStore(db_path=self.db_path).get(self.lease_id)
            if refreshed and refreshed.get_instance():
                candidate = refreshed.get_instance()
                if candidate.status == "running" and refreshed._is_fresh() and not refreshed.needs_refresh:
                    self._current_instance = candidate
                    self.observed_at = refreshed.observed_at
                    self.refresh_error = refreshed.refresh_error
                    self.needs_refresh = refreshed.needs_refresh
                    self.refresh_hint_at = refreshed.refresh_hint_at
                    return self._current_instance
                try:
                    status = provider.get_session_status(candidate.instance_id)
                    self.observed_at = datetime.now()
                    self.refresh_error = None
                    self.needs_refresh = False
                    self.refresh_hint_at = None
                    if status == "running":
                        self._current_instance = candidate
                        self._persist_lease_metadata()
                        return self._current_instance
                    if status == "paused":
                        candidate.status = "paused"
                        self._current_instance = candidate
                        self._persist_instance()
                        raise RuntimeError(
                            f"Sandbox lease {self.lease_id} is paused. Resume before executing commands."
                        )
                except RuntimeError:
                    raise
                except Exception as e:
                    self._record_refresh_error(str(e))
                    pass

            # Create new instance
            self.status = "recovering"
            self._persist_lease_metadata()
            session_info = provider.create_session(context_id=f"leon-{self.lease_id}")
            instance = SandboxInstance(
                instance_id=session_info.session_id,
                provider_name=self.provider_name,
                status="running",
                created_at=datetime.now(),
            )
            self._current_instance = instance
            self.status = "active"
            self.observed_at = datetime.now()
            self.refresh_error = None
            self.needs_refresh = False
            self.refresh_hint_at = None
            self._persist_instance()
            return instance

    def _instance_lock(self) -> threading.Lock:
        with self._lock_guard:
            lock = self._lease_locks.get(self.lease_id)
            if lock is None:
                lock = threading.Lock()
                self._lease_locks[self.lease_id] = lock
            return lock

    def destroy_instance(self, provider: SandboxProvider) -> None:
        """Destroy current instance."""
        if self._current_instance:
            previous_instance = self._current_instance
            try:
                provider.destroy_session(self._current_instance.instance_id)
            except Exception:
                pass  # Already destroyed
            self._current_instance = None
            self.status = "expired"
            self.observed_at = datetime.now()
            self.refresh_error = None
            self.needs_refresh = False
            self.refresh_hint_at = None
            self._clear_instance(previous_instance)

    def pause_instance(self, provider: SandboxProvider) -> bool:
        """Pause current instance."""
        if not self._current_instance:
            return False

        try:
            if provider.pause_session(self._current_instance.instance_id):
                self._current_instance.status = "paused"
                self.observed_at = datetime.now()
                self.refresh_error = None
                self.needs_refresh = False
                self.refresh_hint_at = None
                self._persist_instance()
                return True
        except Exception as e:
            self._record_refresh_error(str(e))
        return False

    def resume_instance(self, provider: SandboxProvider) -> bool:
        """Resume paused instance."""
        if not self._current_instance:
            return False

        try:
            if provider.resume_session(self._current_instance.instance_id):
                self._current_instance.status = "running"
                self.observed_at = datetime.now()
                self.refresh_error = None
                self.needs_refresh = False
                self.refresh_hint_at = None
                self._persist_instance()
                return True
        except Exception as e:
            self._record_refresh_error(str(e))
        return False

    def refresh_instance_status(
        self,
        provider: SandboxProvider,
        *,
        force: bool = False,
        max_age_sec: float = LEASE_FRESHNESS_TTL_SEC,
    ) -> str:
        """Refresh status from provider and converge lease state."""
        if not self._current_instance:
            return "detached"
        if self.needs_refresh:
            force = True
        if not force and self._current_instance.status in {"running", "paused"} and self._is_fresh(max_age_sec):
            return self._current_instance.status
        try:
            status = provider.get_session_status(self._current_instance.instance_id)
            self.observed_at = datetime.now()
            self.refresh_error = None
            self.needs_refresh = False
            self.refresh_hint_at = None
        except Exception as e:
            self._record_refresh_error(str(e))
            return self._current_instance.status or "unknown"

        if status in {"running", "paused"}:
            if self._current_instance.status != status:
                self._current_instance.status = status
                self._persist_instance()
            else:
                self._persist_lease_metadata()
            return status

        if status in {"deleted", "stopped", "dead"}:
            previous_instance = self._current_instance
            self._current_instance = None
            self.refresh_error = None
            self._clear_instance(previous_instance)
            return "detached"

        return self._current_instance.status or "unknown"

    def mark_needs_refresh(self, hint_at: datetime | None = None) -> None:
        """Mark this lease as invalidated; next status read must force refresh."""
        self.needs_refresh = True
        self.refresh_hint_at = hint_at or datetime.now()
        self._persist_lease_metadata()

    def _persist_instance(self) -> None:
        """Persist current instance to DB."""
        if not self._current_instance:
            return

        with _connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE sandbox_leases
                SET current_instance_id = ?, instance_status = ?, instance_created_at = ?, observed_at = ?, refresh_error = ?,
                    needs_refresh = ?, refresh_hint_at = ?, status = ?, updated_at = ?
                WHERE lease_id = ?
                """,
                (
                    self._current_instance.instance_id,
                    self._current_instance.status,
                    self._current_instance.created_at.isoformat(),
                    self.observed_at.isoformat() if self.observed_at else None,
                    self.refresh_error,
                    1 if self.needs_refresh else 0,
                    self.refresh_hint_at.isoformat() if self.refresh_hint_at else None,
                    self.status,
                    datetime.now().isoformat(),
                    self.lease_id,
                ),
            )
            conn.execute(
                """
                INSERT INTO sandbox_instances (
                    instance_id, lease_id, provider_session_id, status, created_at, last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(instance_id) DO UPDATE SET
                    status = excluded.status,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    self._current_instance.instance_id,
                    self.lease_id,
                    self._current_instance.instance_id,
                    self._current_instance.status,
                    self._current_instance.created_at.isoformat(),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def _persist_lease_metadata(self) -> None:
        with _connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE sandbox_leases
                SET observed_at = ?, refresh_error = ?, needs_refresh = ?, refresh_hint_at = ?, status = ?, updated_at = ?
                WHERE lease_id = ?
                """,
                (
                    self.observed_at.isoformat() if self.observed_at else None,
                    self.refresh_error,
                    1 if self.needs_refresh else 0,
                    self.refresh_hint_at.isoformat() if self.refresh_hint_at else None,
                    self.status,
                    datetime.now().isoformat(),
                    self.lease_id,
                ),
            )
            conn.commit()

    def _clear_instance(self, previous_instance: SandboxInstance | None = None) -> None:
        """Clear instance from DB."""
        with _connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE sandbox_leases
                SET current_instance_id = NULL, instance_status = NULL, instance_created_at = NULL,
                    observed_at = ?, refresh_error = ?, needs_refresh = ?, refresh_hint_at = ?, status = ?, updated_at = ?
                WHERE lease_id = ?
                """,
                (
                    self.observed_at.isoformat() if self.observed_at else None,
                    self.refresh_error,
                    1 if self.needs_refresh else 0,
                    self.refresh_hint_at.isoformat() if self.refresh_hint_at else None,
                    self.status,
                    datetime.now().isoformat(),
                    self.lease_id,
                ),
            )
            if previous_instance:
                conn.execute(
                    """
                    UPDATE sandbox_instances
                    SET status = ?, last_seen_at = ?
                    WHERE instance_id = ?
                    """,
                    ("stopped", datetime.now().isoformat(), previous_instance.instance_id),
                )
            conn.commit()


class LeaseStore:
    """Store for managing SandboxLease persistence."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Ensure sandbox_leases table exists."""
        with _connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sandbox_leases (
                    lease_id TEXT PRIMARY KEY,
                    provider_name TEXT NOT NULL,
                    workspace_key TEXT,
                    current_instance_id TEXT,
                    instance_status TEXT,
                    instance_created_at TIMESTAMP,
                    observed_at TIMESTAMP,
                    refresh_error TEXT,
                    needs_refresh INTEGER NOT NULL DEFAULT 0,
                    refresh_hint_at TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sandbox_instances (
                    instance_id TEXT PRIMARY KEY,
                    lease_id TEXT NOT NULL,
                    provider_session_id TEXT NOT NULL,
                    status TEXT DEFAULT 'running',
                    created_at TIMESTAMP NOT NULL,
                    last_seen_at TIMESTAMP NOT NULL
                )
                """
            )
            conn.commit()
            lease_cols = {row[1] for row in conn.execute("PRAGMA table_info(sandbox_leases)").fetchall()}
            instance_cols = {row[1] for row in conn.execute("PRAGMA table_info(sandbox_instances)").fetchall()}
        missing_lease = REQUIRED_LEASE_COLUMNS - lease_cols
        if missing_lease:
            raise RuntimeError(
                f"sandbox_leases schema mismatch: missing {sorted(missing_lease)}. Purge ~/.leon/sandbox.db and retry."
            )
        missing_instances = REQUIRED_INSTANCE_COLUMNS - instance_cols
        if missing_instances:
            raise RuntimeError(
                f"sandbox_instances schema mismatch: missing {sorted(missing_instances)}. "
                "Purge ~/.leon/sandbox.db and retry."
            )

    def get(self, lease_id: str) -> SandboxLease | None:
        """Get lease by lease_id."""
        with _connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT lease_id, provider_name, workspace_key, current_instance_id, instance_status, instance_created_at,
                       observed_at, refresh_error, needs_refresh, refresh_hint_at, status
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
                status=row["status"] or "active",
                workspace_key=row["workspace_key"],
                observed_at=datetime.fromisoformat(row["observed_at"]) if row["observed_at"] else None,
                refresh_error=row["refresh_error"],
                needs_refresh=bool(row["needs_refresh"]),
                refresh_hint_at=datetime.fromisoformat(row["refresh_hint_at"]) if row["refresh_hint_at"] else None,
            )

    def create(
        self,
        lease_id: str,
        provider_name: str,
    ) -> SandboxLease:
        """Create new lease."""
        now = datetime.now().isoformat()

        with _connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO sandbox_leases (
                    lease_id, provider_name, observed_at, refresh_error, needs_refresh, refresh_hint_at, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (lease_id, provider_name, now, None, 0, None, "active", now, now),
            )
            conn.commit()

        return SQLiteLease(
            lease_id=lease_id,
            provider_name=provider_name,
            current_instance=None,
            db_path=self.db_path,
            status="active",
            needs_refresh=False,
            refresh_hint_at=None,
        )

    def find_by_instance(self, *, provider_name: str, instance_id: str) -> SandboxLease | None:
        """Find lease whose current instance matches provider+instance."""
        with _connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT lease_id
                FROM sandbox_leases
                WHERE provider_name = ? AND current_instance_id = ?
                LIMIT 1
                """,
                (provider_name, instance_id),
            ).fetchone()
            if not row:
                return None
            return self.get(row["lease_id"])

    def mark_needs_refresh(self, *, lease_id: str, hint_at: datetime | None = None) -> bool:
        """Mark a lease invalidated. Returns True when lease exists."""
        hinted_at = (hint_at or datetime.now()).isoformat()
        with _connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE sandbox_leases
                SET needs_refresh = 1, refresh_hint_at = ?, updated_at = ?
                WHERE lease_id = ?
                """,
                (hinted_at, datetime.now().isoformat(), lease_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete(self, lease_id: str) -> None:
        """Delete lease."""
        with _connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM sandbox_leases WHERE lease_id = ?",
                (lease_id,),
            )
            conn.commit()

    def list_all(self) -> list[dict]:
        """List all leases."""
        with _connect(self.db_path) as conn:
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
        with _connect(self.db_path) as conn:
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
