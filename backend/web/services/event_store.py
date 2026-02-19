"""Persistent event log backed by SQLite — enables SSE reconnection after restart."""

import sqlite3
import threading
from pathlib import Path
from typing import Any

_DB_PATH = Path.home() / ".leon" / "leon.db"
_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Return a per-thread SQLite connection (reused across calls)."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        _local.conn = conn
    return conn


def init_event_store() -> None:
    """Create the run_events table if it doesn't exist."""
    conn = _get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS run_events (
            seq        INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id  TEXT NOT NULL,
            run_id     TEXT NOT NULL,
            event_type TEXT NOT NULL,
            data       TEXT NOT NULL,
            message_id TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_run_events_thread_run
        ON run_events (thread_id, run_id, seq);
        """
    )


def append_event(
    thread_id: str,
    run_id: str,
    event: dict[str, Any],
    message_id: str | None = None,
) -> int:
    """Persist one SSE event and return its sequence number."""
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO run_events (thread_id, run_id, event_type, data, message_id) VALUES (?, ?, ?, ?, ?)",
        (thread_id, run_id, event.get("event", ""), event.get("data", ""), message_id),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def read_events_after(
    thread_id: str,
    run_id: str,
    after_seq: int = 0,
) -> list[dict[str, Any]]:
    """Return events with seq > after_seq for the given run."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT seq, event_type, data, message_id FROM run_events "
        "WHERE thread_id = ? AND run_id = ? AND seq > ? ORDER BY seq",
        (thread_id, run_id, after_seq),
    ).fetchall()
    return [
        {
            "seq": r[0],
            "event": r[1],
            "data": r[2],
            "message_id": r[3],
        }
        for r in rows
    ]


def get_latest_run_id(thread_id: str) -> str | None:
    """Return the run_id of the most recent run for a thread, or None."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT run_id FROM run_events WHERE thread_id = ? ORDER BY seq DESC LIMIT 1",
        (thread_id,),
    ).fetchone()
    return row[0] if row else None


def cleanup_old_runs(thread_id: str, keep_latest: int = 1) -> int:
    """Delete all but the N most recent runs for a thread. Returns deleted count."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT DISTINCT run_id FROM run_events WHERE thread_id = ? ORDER BY seq DESC",
        (thread_id,),
    ).fetchall()
    run_ids = [r[0] for r in rows]
    if len(run_ids) <= keep_latest:
        return 0
    old_ids = run_ids[keep_latest:]
    placeholders = ",".join("?" for _ in old_ids)
    cur = conn.execute(
        f"DELETE FROM run_events WHERE thread_id = ? AND run_id IN ({placeholders})",
        [thread_id, *old_ids],
    )
    conn.commit()
    return cur.rowcount


def cleanup_thread(thread_id: str) -> int:
    """Delete all events for a thread. Returns deleted count."""
    conn = _get_conn()
    cur = conn.execute("DELETE FROM run_events WHERE thread_id = ?", (thread_id,))
    conn.commit()
    return cur.rowcount
