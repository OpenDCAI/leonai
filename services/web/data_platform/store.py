from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _iso_ago(*, seconds: int) -> str:
    return (datetime.now() - timedelta(seconds=int(seconds))).isoformat(timespec="seconds")


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


@dataclass(frozen=True)
class RunRow:
    run_id: str
    thread_id: str
    sandbox: str
    input_message: str
    status: str
    started_at: str
    finished_at: str | None
    error: str | None


@dataclass(frozen=True)
class RunEventRow:
    event_id: int
    run_id: str
    thread_id: str
    event_type: str
    payload: dict[str, Any]
    created_at: str


def ensure_tables(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dp_runs (
                run_id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                sandbox TEXT NOT NULL,
                input_message TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TIMESTAMP NOT NULL,
                finished_at TIMESTAMP,
                error TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_dp_runs_thread_started
            ON dp_runs(thread_id, started_at DESC)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dp_run_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (run_id) REFERENCES dp_runs(run_id)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_dp_run_events_run_event
            ON dp_run_events(run_id, event_id ASC)
            """
        )
        conn.commit()


def create_run(*, db_path: Path, thread_id: str, sandbox: str, input_message: str) -> str:
    run_id = str(uuid.uuid4())
    started_at = _now_iso()
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO dp_runs (run_id, thread_id, sandbox, input_message, status, started_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, thread_id, sandbox, input_message[:2000], "running", started_at),
        )
        conn.commit()
    return run_id


def finalize_run(*, db_path: Path, run_id: str, status: str, error: str | None = None) -> None:
    finished_at = _now_iso()
    with _connect(db_path) as conn:
        cur = conn.execute(
            """
            UPDATE dp_runs
            SET status = ?, finished_at = ?, error = ?
            WHERE run_id = ?
            """,
            (status, finished_at, error, run_id),
        )
        if cur.rowcount != 1:
            raise RuntimeError(f"Run not found: {run_id}")
        conn.commit()


def insert_event(
    *,
    db_path: Path,
    run_id: str,
    thread_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> int:
    created_at = _now_iso()
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with _connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO dp_run_events (run_id, thread_id, event_type, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, thread_id, event_type, payload_json, created_at),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_run(*, db_path: Path, run_id: str) -> RunRow | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT run_id, thread_id, sandbox, input_message, status, started_at, finished_at, error
            FROM dp_runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        if not row:
            return None
        return RunRow(
            run_id=row["run_id"],
            thread_id=row["thread_id"],
            sandbox=row["sandbox"],
            input_message=row["input_message"],
            status=row["status"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            error=row["error"],
        )


def list_runs(*, db_path: Path, thread_id: str, limit: int = 50, offset: int = 0) -> list[RunRow]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT run_id, thread_id, sandbox, input_message, status, started_at, finished_at, error
            FROM dp_runs
            WHERE thread_id = ?
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
            """,
            (thread_id, int(limit), int(offset)),
        ).fetchall()
        return [
            RunRow(
                run_id=r["run_id"],
                thread_id=r["thread_id"],
                sandbox=r["sandbox"],
                input_message=r["input_message"],
                status=r["status"],
                started_at=r["started_at"],
                finished_at=r["finished_at"],
                error=r["error"],
            )
            for r in rows
        ]


def get_latest_run_for_thread(*, db_path: Path, thread_id: str) -> RunRow | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT run_id, thread_id, sandbox, input_message, status, started_at, finished_at, error
            FROM dp_runs
            WHERE thread_id = ?
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (thread_id,),
        ).fetchone()
        if not row:
            return None
        return RunRow(
            run_id=row["run_id"],
            thread_id=row["thread_id"],
            sandbox=row["sandbox"],
            input_message=row["input_message"],
            status=row["status"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            error=row["error"],
        )


def get_last_event_id_for_run(*, db_path: Path, run_id: str) -> int:
    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT COALESCE(MAX(event_id), 0) AS max_id
            FROM dp_run_events
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        return int(row["max_id"] if row else 0)


def has_event_type(*, db_path: Path, run_id: str, event_type: str) -> bool:
    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM dp_run_events
            WHERE run_id = ? AND event_type = ?
            LIMIT 1
            """,
            (run_id, event_type),
        ).fetchone()
        return bool(row)


def list_stuck_runs(*, db_path: Path, stuck_after_sec: int, limit: int = 50) -> list[RunRow]:
    """Runs considered stuck for alerting/ops: status=running and started_at older than cutoff."""
    cutoff = _iso_ago(seconds=stuck_after_sec)
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT run_id, thread_id, sandbox, input_message, status, started_at, finished_at, error
            FROM dp_runs
            WHERE status = 'running' AND started_at < ?
            ORDER BY started_at ASC
            LIMIT ?
            """,
            (cutoff, int(limit)),
        ).fetchall()
        return [
            RunRow(
                run_id=r["run_id"],
                thread_id=r["thread_id"],
                sandbox=r["sandbox"],
                input_message=r["input_message"],
                status=r["status"],
                started_at=r["started_at"],
                finished_at=r["finished_at"],
                error=r["error"],
            )
            for r in rows
        ]


def list_events(
    *,
    db_path: Path,
    run_id: str,
    after_event_id: int = 0,
    limit: int = 200,
) -> list[RunEventRow]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT event_id, run_id, thread_id, event_type, payload_json, created_at
            FROM dp_run_events
            WHERE run_id = ? AND event_id > ?
            ORDER BY event_id ASC
            LIMIT ?
            """,
            (run_id, int(after_event_id), int(limit)),
        ).fetchall()
        items: list[RunEventRow] = []
        for r in rows:
            items.append(
                RunEventRow(
                    event_id=int(r["event_id"]),
                    run_id=r["run_id"],
                    thread_id=r["thread_id"],
                    event_type=r["event_type"],
                    payload=json.loads(r["payload_json"]),
                    created_at=r["created_at"],
                )
            )
        return items
