"""Message Queue Manager — dual-channel message routing.

Two channels:
- inject/pop_steer: in-memory steer buffer (immediate injection into current run)
- enqueue/dequeue: SQLite-persisted followup queue (consumed when agent goes IDLE)
"""

import sqlite3
import threading
from collections import deque
from pathlib import Path


class MessageQueueManager:
    """Dual-channel message routing: inject (memory steer) + enqueue/dequeue (SQLite followup)."""

    def __init__(self, db_path: str | None = None):
        self._steer: dict[str, deque[str]] = {}
        self._lock = threading.Lock()
        self._db_path = db_path or str(Path.home() / ".leon" / "leon.db")
        self._ensure_table()

    # ------------------------------------------------------------------
    # SQLite setup
    # ------------------------------------------------------------------

    def _ensure_table(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS message_queue ("
                "  id         INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  thread_id  TEXT NOT NULL,"
                "  content    TEXT NOT NULL,"
                "  created_at TEXT DEFAULT (datetime('now'))"
                ")"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mq_thread ON message_queue (thread_id, id)"
            )
            conn.commit()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------
    # Steer channel (in-memory)
    # ------------------------------------------------------------------

    def inject(self, content: str, thread_id: str) -> None:
        """Inject a steer message into the in-memory buffer. Called when agent is ACTIVE."""
        with self._lock:
            if thread_id not in self._steer:
                self._steer[thread_id] = deque()
            self._steer[thread_id].append(content)

    def pop_steer(self, thread_id: str) -> str | None:
        """Pop one steer message. Called by SteeringMiddleware after each tool call."""
        with self._lock:
            dq = self._steer.get(thread_id)
            return dq.popleft() if dq else None

    def has_steer(self, thread_id: str) -> bool:
        """Check whether steer messages are pending."""
        with self._lock:
            dq = self._steer.get(thread_id)
            return bool(dq)

    def drain_steer(self, thread_id: str) -> list[str]:
        """Pop ALL pending steer messages at once."""
        with self._lock:
            dq = self._steer.get(thread_id)
            if not dq:
                return []
            items = list(dq)
            dq.clear()
            return items

    # ------------------------------------------------------------------
    # Followup channel (SQLite)
    # ------------------------------------------------------------------

    def enqueue(self, content: str, thread_id: str) -> None:
        """Persist a followup message. Consumed when agent reaches IDLE."""
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO message_queue (thread_id, content) VALUES (?, ?)",
                (thread_id, content),
            )
            conn.commit()

    def dequeue(self, thread_id: str) -> str | None:
        """Atomically pop the oldest followup message (DELETE + RETURNING)."""
        with self._conn() as conn:
            row = conn.execute(
                "DELETE FROM message_queue "
                "WHERE id = (SELECT MIN(id) FROM message_queue WHERE thread_id = ?) "
                "RETURNING content",
                (thread_id,),
            ).fetchone()
            conn.commit()
            return row["content"] if row else None

    def peek(self, thread_id: str) -> bool:
        """Check if the followup queue has messages (without consuming)."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM message_queue WHERE thread_id = ? LIMIT 1",
                (thread_id,),
            ).fetchone()
            return row is not None

    def list_queue(self, thread_id: str) -> list[dict]:
        """List all pending followup messages (for API queries)."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, content, created_at FROM message_queue "
                "WHERE thread_id = ? ORDER BY id",
                (thread_id,),
            ).fetchall()
            return [{"id": r["id"], "content": r["content"], "created_at": r["created_at"]} for r in rows]

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def clear_steer(self, thread_id: str) -> None:
        """Clear in-memory steer buffer for a thread."""
        with self._lock:
            self._steer.pop(thread_id, None)

    def clear_queue(self, thread_id: str) -> None:
        """Clear persisted followup queue for a thread."""
        with self._conn() as conn:
            conn.execute("DELETE FROM message_queue WHERE thread_id = ?", (thread_id,))
            conn.commit()

    def clear_all(self, thread_id: str) -> None:
        """Clear both steer and followup for a thread."""
        self.clear_steer(thread_id)
        self.clear_queue(thread_id)

    def clear_thread(self, thread_id: str) -> None:
        """Alias for clear_all (backward compat)."""
        self.clear_all(thread_id)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def queue_sizes(self, thread_id: str) -> dict[str, int]:
        """Return sizes of both channels."""
        with self._lock:
            steer_size = len(self._steer.get(thread_id, []))
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM message_queue WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
            followup_size = row["cnt"] if row else 0
        return {"steer": steer_size, "followup": followup_size}


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_queue_manager: MessageQueueManager | None = None
_manager_lock = threading.Lock()


def get_queue_manager() -> MessageQueueManager:
    """Get the global MessageQueueManager singleton."""
    global _queue_manager
    if _queue_manager is None:
        with _manager_lock:
            if _queue_manager is None:
                _queue_manager = MessageQueueManager()
    return _queue_manager


def reset_queue_manager() -> None:
    """Reset the global manager (for testing)."""
    global _queue_manager
    with _manager_lock:
        _queue_manager = None
