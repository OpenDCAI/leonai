"""
SQLiteMessageQueue — SQLite-backed implementation of MessageQueue.

Uses atomic UPDATE...WHERE to prevent double-claiming.
"""

import json
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from sandbox.message_queue import Message, MessageQueue

DEFAULT_DB_PATH = Path.home() / ".leon" / "leon.db"


class SQLiteMessageQueue(MessageQueue):
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._lock = threading.Lock()
        self._conn = self._init_db()

    def _init_db(self) -> sqlite3.Connection:
        if isinstance(self.db_path, Path):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS message_queue (
                id TEXT PRIMARY KEY,
                queue TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                error TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                claimed_at TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_mq_queue_status
            ON message_queue (queue, status, created_at)
        """)
        conn.commit()
        return conn

    def enqueue(self, queue: str, payload: dict[str, Any]) -> str:
        msg_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._conn.execute(
                "INSERT INTO message_queue (id, queue, payload) VALUES (?, ?, ?)",
                (msg_id, queue, json.dumps(payload)),
            )
            self._conn.commit()
        return msg_id

    def claim(self, queue: str) -> Message | None:
        """@@@ Atomic claim — SELECT oldest pending, UPDATE to claimed in one lock."""
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            row = self._conn.execute(
                """
                SELECT id FROM message_queue
                WHERE queue = ? AND status = 'pending'
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (queue,),
            ).fetchone()
            if not row:
                return None

            now = datetime.now()
            self._conn.execute(
                "UPDATE message_queue SET status = 'claimed', claimed_at = ? WHERE id = ?",
                (now, row["id"]),
            )
            self._conn.commit()

            full = self._conn.execute(
                "SELECT * FROM message_queue WHERE id = ?",
                (row["id"],),
            ).fetchone()
            return self._row_to_message(full)

    def complete(self, message_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE message_queue SET status = 'completed' WHERE id = ?",
                (message_id,),
            )
            self._conn.commit()

    def fail(self, message_id: str, error: str = "") -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE message_queue SET status = 'failed', error = ? WHERE id = ?",
                (error, message_id),
            )
            self._conn.commit()

    def peek(self, queue: str, limit: int = 10) -> list[Message]:
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            rows = self._conn.execute(
                """
                SELECT * FROM message_queue
                WHERE queue = ? AND status = 'pending'
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (queue, limit),
            ).fetchall()
            return [self._row_to_message(r) for r in rows]

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> Message:
        return Message(
            id=row["id"],
            queue=row["queue"],
            payload=json.loads(row["payload"]),
            status=row["status"],
            created_at=row["created_at"],
            claimed_at=row["claimed_at"],
        )
