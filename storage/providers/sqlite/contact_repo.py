"""SQLite repository for contacts."""

from __future__ import annotations

import sqlite3
import threading
import uuid
from pathlib import Path

from storage.contracts import ContactRow
from storage.providers.sqlite.connection import create_connection
from storage.providers.sqlite.kernel import SQLiteDBRole, resolve_role_db_path


class SQLiteContactRepo:

    def __init__(self, db_path: str | Path | None = None, conn: sqlite3.Connection | None = None) -> None:
        self._own_conn = conn is None
        self._lock = threading.Lock()
        if conn is not None:
            self._conn = conn
        else:
            if db_path is None:
                db_path = resolve_role_db_path(SQLiteDBRole.CONVERSATION)
            self._conn = create_connection(db_path)
        self._ensure_table()

    def close(self) -> None:
        if self._own_conn:
            self._conn.close()

    def create_pair(self, owner_a: str, owner_b: str, created_at: float) -> None:
        """Create bidirectional contact: A→B and B→A. Idempotent."""
        with self._lock:
            for a, b in [(owner_a, owner_b), (owner_b, owner_a)]:
                self._conn.execute(
                    "INSERT OR IGNORE INTO contacts (id, owner_id, contact_id, created_at)"
                    " VALUES (?, ?, ?, ?)",
                    (str(uuid.uuid4()), a, b, created_at),
                )
            self._conn.commit()

    def list_by_owner(self, owner_id: str) -> list[ContactRow]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, owner_id, contact_id, created_at FROM contacts WHERE owner_id = ? ORDER BY created_at",
                (owner_id,),
            ).fetchall()
            return [ContactRow(id=r[0], owner_id=r[1], contact_id=r[2], created_at=r[3]) for r in rows]

    def exists(self, owner_id: str, contact_id: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM contacts WHERE owner_id = ? AND contact_id = ? LIMIT 1",
                (owner_id, contact_id),
            ).fetchone()
            return row is not None

    def delete_pair(self, owner_a: str, owner_b: str) -> None:
        """Delete both directions."""
        with self._lock:
            self._conn.execute(
                "DELETE FROM contacts WHERE (owner_id = ? AND contact_id = ?) OR (owner_id = ? AND contact_id = ?)",
                (owner_a, owner_b, owner_b, owner_a),
            )
            self._conn.commit()

    def _ensure_table(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS contacts (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                contact_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                UNIQUE(owner_id, contact_id)
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_contacts_owner ON contacts (owner_id)"
        )
        self._conn.commit()
