"""AbstractTerminal - Durable terminal identity + state snapshot.

This module implements the terminal abstraction layer that separates
durable terminal state (cwd, env_delta) from ephemeral runtime processes.

Architecture:
    Thread → AbstractTerminal (durable state) → SandboxLease → Instance
    Thread → ChatSession → PhysicalTerminalRuntime (ephemeral process)
"""

from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sandbox.lease import SandboxLease

DEFAULT_DB_PATH = Path.home() / ".leon" / "leon.db"


@dataclass
class TerminalState:
    """Terminal state snapshot.

    Represents the current state of a terminal that needs to persist
    across session boundaries. This is the "continuity" layer that
    makes terminals feel persistent even when physical processes die.
    """

    cwd: str
    env_delta: dict[str, str] = field(default_factory=dict)
    state_version: int = 0

    def to_json(self) -> str:
        """Serialize to JSON for DB storage."""
        return json.dumps({
            "cwd": self.cwd,
            "env_delta": self.env_delta,
            "state_version": self.state_version,
        })

    @classmethod
    def from_json(cls, data: str) -> TerminalState:
        """Deserialize from JSON."""
        obj = json.loads(data)
        return cls(
            cwd=obj["cwd"],
            env_delta=obj.get("env_delta", {}),
            state_version=obj.get("state_version", 0),
        )


class AbstractTerminal(ABC):
    """Durable terminal identity + state snapshot.

    This is the logical terminal that persists across ChatSession boundaries.
    It does NOT own the physical process - that's owned by PhysicalTerminalRuntime.

    Responsibilities:
    - Store terminal identity (terminal_id, thread_id, lease_id)
    - Maintain state snapshot (cwd, env_delta, state_version)
    - Persist state to database
    - Provide state to PhysicalTerminalRuntime for hydration

    Does NOT:
    - Own physical shell/pty process
    - Execute commands directly
    - Manage process lifecycle
    """

    def __init__(
        self,
        terminal_id: str,
        thread_id: str,
        lease_id: str,
        state: TerminalState,
    ):
        self.terminal_id = terminal_id
        self.thread_id = thread_id
        self.lease_id = lease_id
        self._state = state

    def get_state(self) -> TerminalState:
        """Get current terminal state snapshot."""
        return self._state

    def update_state(self, state: TerminalState) -> None:
        """Update terminal state snapshot.

        This should be called after each command execution to persist
        the new cwd/env state.
        """
        state.state_version = self._state.state_version + 1
        self._state = state
        self._persist_state()

    @abstractmethod
    def _persist_state(self) -> None:
        """Persist state to storage backend."""
        ...


class SQLiteTerminal(AbstractTerminal):
    """SQLite-backed terminal implementation."""

    def __init__(
        self,
        terminal_id: str,
        thread_id: str,
        lease_id: str,
        state: TerminalState,
        db_path: Path = DEFAULT_DB_PATH,
    ):
        super().__init__(terminal_id, thread_id, lease_id, state)
        self.db_path = db_path

    def _persist_state(self) -> None:
        """Persist state to SQLite."""
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.execute(
                """
                UPDATE abstract_terminals
                SET cwd = ?, env_delta_json = ?, state_version = ?, updated_at = ?
                WHERE terminal_id = ?
                """,
                (
                    self._state.cwd,
                    json.dumps(self._state.env_delta),
                    self._state.state_version,
                    datetime.now().isoformat(),
                    self.terminal_id,
                ),
            )
            conn.commit()


class TerminalStore:
    """Store for managing AbstractTerminal persistence.

    Handles CRUD operations for terminals in the database.
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Ensure abstract_terminals table exists."""
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS abstract_terminals (
                    terminal_id TEXT PRIMARY KEY,
                    thread_id TEXT UNIQUE NOT NULL,
                    lease_id TEXT NOT NULL,
                    cwd TEXT NOT NULL,
                    env_delta_json TEXT DEFAULT '{}',
                    state_version INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def get(self, thread_id: str) -> AbstractTerminal | None:
        """Get terminal by thread_id."""
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT terminal_id, thread_id, lease_id, cwd, env_delta_json, state_version
                FROM abstract_terminals
                WHERE thread_id = ?
                """,
                (thread_id,),
            ).fetchone()

            if not row:
                return None

            state = TerminalState(
                cwd=row["cwd"],
                env_delta=json.loads(row["env_delta_json"]),
                state_version=row["state_version"],
            )

            return SQLiteTerminal(
                terminal_id=row["terminal_id"],
                thread_id=row["thread_id"],
                lease_id=row["lease_id"],
                state=state,
                db_path=self.db_path,
            )

    def get_by_id(self, terminal_id: str) -> AbstractTerminal | None:
        """Get terminal by terminal_id."""
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT terminal_id, thread_id, lease_id, cwd, env_delta_json, state_version
                FROM abstract_terminals
                WHERE terminal_id = ?
                """,
                (terminal_id,),
            ).fetchone()

            if not row:
                return None

            state = TerminalState(
                cwd=row["cwd"],
                env_delta=json.loads(row["env_delta_json"]),
                state_version=row["state_version"],
            )

            return SQLiteTerminal(
                terminal_id=row["terminal_id"],
                thread_id=row["thread_id"],
                lease_id=row["lease_id"],
                state=state,
                db_path=self.db_path,
            )

    def create(
        self,
        terminal_id: str,
        thread_id: str,
        lease_id: str,
        initial_cwd: str = "/root",
    ) -> AbstractTerminal:
        """Create new terminal."""
        state = TerminalState(cwd=initial_cwd, env_delta={}, state_version=0)
        now = datetime.now().isoformat()

        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.execute(
                """
                INSERT INTO abstract_terminals (terminal_id, thread_id, lease_id, cwd, env_delta_json, state_version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    terminal_id,
                    thread_id,
                    lease_id,
                    state.cwd,
                    json.dumps(state.env_delta),
                    state.state_version,
                    now,
                    now,
                ),
            )
            conn.commit()

        return SQLiteTerminal(
            terminal_id=terminal_id,
            thread_id=thread_id,
            lease_id=lease_id,
            state=state,
            db_path=self.db_path,
        )

    def delete(self, terminal_id: str) -> None:
        """Delete terminal."""
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.execute(
                "DELETE FROM abstract_terminals WHERE terminal_id = ?",
                (terminal_id,),
            )
            conn.commit()

    def list_all(self) -> list[dict]:
        """List all terminals."""
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT terminal_id, thread_id, lease_id, cwd, state_version, created_at, updated_at
                FROM abstract_terminals
                ORDER BY created_at DESC
                """
            ).fetchall()

            return [dict(row) for row in rows]
