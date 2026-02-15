from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.execute("PRAGMA busy_timeout=10000")
    conn.row_factory = sqlite3.Row
    return conn


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _iso_ago(*, hours: int) -> str:
    return (datetime.now() - timedelta(hours=int(hours))).isoformat(timespec="seconds")


def _sandbox_db_path() -> Path:
    return Path(os.getenv("LEON_SANDBOX_DB_PATH") or (Path.home() / ".leon" / "sandbox.db"))


def overview(*, dp_db_path: Path, window_hours: int = 24, stuck_after_sec: int = 600) -> dict[str, Any]:
    # @@@e2e-evidence - See `teams/log/leonai/data_platform/2026-02-15_e2e_dashboards_and_alerts.md`
    now = _now_iso()
    since = _iso_ago(hours=window_hours)
    stuck_cutoff = (datetime.now() - timedelta(seconds=int(stuck_after_sec))).isoformat(timespec="seconds")

    body: dict[str, Any] = {
        "window_hours": int(window_hours),
        "generated_at": now,
        "runs_by_status": {},
        "top_errors": [],
        "stuck_runs": {"cutoff_started_before": stuck_cutoff, "count": 0, "items": []},
        "sandboxes": {"active_sessions_count": 0},
    }

    if dp_db_path.exists():
        with _connect(dp_db_path) as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS c
                FROM dp_runs
                WHERE started_at >= ?
                GROUP BY status
                """,
                (since,),
            ).fetchall()
            body["runs_by_status"] = {r["status"]: int(r["c"]) for r in rows}

            rows = conn.execute(
                """
                SELECT error, COUNT(*) AS c, MAX(started_at) AS last_seen_at
                FROM dp_runs
                WHERE started_at >= ? AND error IS NOT NULL AND error != ''
                GROUP BY error
                ORDER BY c DESC, last_seen_at DESC
                LIMIT 10
                """,
                (since,),
            ).fetchall()
            body["top_errors"] = [
                {"error": r["error"], "count": int(r["c"]), "last_seen_at": r["last_seen_at"]} for r in rows
            ]

            rows = conn.execute(
                """
                SELECT run_id, thread_id, sandbox, started_at, input_message, error
                FROM dp_runs
                WHERE status = 'running' AND started_at < ?
                ORDER BY started_at ASC
                LIMIT 20
                """,
                (stuck_cutoff,),
            ).fetchall()
            body["stuck_runs"]["count"] = len(rows)
            body["stuck_runs"]["items"] = [
                {
                    "run_id": r["run_id"],
                    "thread_id": r["thread_id"],
                    "sandbox": r["sandbox"],
                    "started_at": r["started_at"],
                    "input_message": r["input_message"],
                    "error": r["error"],
                }
                for r in rows
            ]

    sandbox_db = _sandbox_db_path()
    if sandbox_db.exists():
        with _connect(sandbox_db) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "chat_sessions" in tables:
                row = conn.execute(
                    """
                    SELECT COUNT(*) AS c
                    FROM chat_sessions
                    WHERE status IN ('active', 'idle', 'paused')
                    """
                ).fetchone()
                body["sandboxes"]["active_sessions_count"] = int(row["c"] if row else 0)

    return body

