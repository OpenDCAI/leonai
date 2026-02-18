from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any


def _sandbox_db_path() -> Path:
    return Path(os.getenv("LEON_SANDBOX_DB_PATH") or (Path.home() / ".leon" / "sandbox.db"))


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.execute("PRAGMA busy_timeout=10000")
    conn.row_factory = sqlite3.Row
    return conn


def list_provider_events(
    *,
    thread_id: str | None = None,
    provider: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Query provider webhook/event logs.

    Returns events sorted by received_at DESC.
    """
    db_path = _sandbox_db_path()
    if not db_path.exists():
        return []

    with _connect(db_path) as conn:
        # Check if provider_events table exists
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "provider_events" not in tables:
            # @@@print-not-match - Table doesn't exist yet, return empty
            return []

        # Build WHERE clause
        where_parts = []
        params = []

        if thread_id:
            where_parts.append("thread_id = ?")
            params.append(thread_id)

        if provider:
            where_parts.append("provider = ?")
            params.append(provider)

        where_clause = " AND ".join(where_parts) if where_parts else "1=1"

        rows = conn.execute(
            f"""
            SELECT
              event_id,
              provider,
              event_type,
              thread_id,
              instance_id,
              payload,
              received_at
            FROM provider_events
            WHERE {where_clause}
            ORDER BY received_at DESC
            LIMIT ?
            """,
            (*params, int(limit)),
        ).fetchall()

        return [
            {
                "event_id": r["event_id"],
                "provider": r["provider"],
                "event_type": r["event_type"],
                "thread_id": r["thread_id"],
                "instance_id": r["instance_id"],
                "payload": r["payload"],
                "received_at": r["received_at"],
            }
            for r in rows
        ]
