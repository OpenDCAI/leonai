"""Diagnose capabilities for monitor core."""

import sqlite3
from datetime import datetime, timezone
from typing import Any

from sandbox.db import DEFAULT_DB_PATH

from .control import list_sessions


def runtime_health_snapshot() -> dict[str, Any]:
    """Return a lightweight control-plane health snapshot."""
    db_exists = DEFAULT_DB_PATH.exists()
    tables: dict[str, int] = {"chat_sessions": 0, "sandbox_leases": 0, "lease_events": 0}

    if db_exists:
        with sqlite3.connect(str(DEFAULT_DB_PATH), timeout=10) as conn:
            for table_name in tables:
                row = conn.execute(f"SELECT COUNT(1) FROM {table_name}").fetchone()
                tables[table_name] = int(row[0]) if row else 0

    sessions = list_sessions()
    provider_counts: dict[str, int] = {}
    for session in sessions:
        provider = str(session.get("provider") or "unknown")
        provider_counts[provider] = provider_counts.get(provider, 0) + 1

    return {
        "snapshot_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "db": {"path": str(DEFAULT_DB_PATH), "exists": db_exists, "counts": tables},
        "sessions": {
            "total": len(sessions),
            "providers": provider_counts,
        },
    }
