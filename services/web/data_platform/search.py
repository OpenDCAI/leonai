from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.execute("PRAGMA busy_timeout=10000")
    conn.row_factory = sqlite3.Row
    return conn


def _sandbox_db_path() -> Path:
    return Path(os.getenv("LEON_SANDBOX_DB_PATH") or (Path.home() / ".leon" / "sandbox.db"))


def search_all(
    *,
    dp_db_path: Path,
    q: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    # @@@e2e-evidence - See `teams/log/leonai/data_platform/2026-02-15_e2e_operator_search_and_sandboxes.md`
    q = (q or "").strip()
    if not q:
        return []

    like = f"%{q}%"
    hits: list[dict[str, Any]] = []

    if dp_db_path.exists():
        with _connect(dp_db_path) as conn:
            # Runs: id/thread/status/error
            rows = conn.execute(
                """
                SELECT run_id, thread_id, status, started_at, error
                FROM dp_runs
                WHERE run_id LIKE ? OR thread_id LIKE ? OR status LIKE ? OR error LIKE ?
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (like, like, like, like, int(limit)),
            ).fetchall()
            for r in rows:
                hits.append(
                    {
                        "type": "run",
                        "id": r["run_id"],
                        "thread_id": r["thread_id"],
                        "summary": f"status={r['status']} error={r['error'] or ''}".strip(),
                        "updated_at": r["started_at"],
                    }
                )

            # Events: payload substring
            rows = conn.execute(
                """
                SELECT event_id, run_id, thread_id, event_type, created_at
                FROM dp_run_events
                WHERE event_type LIKE ? OR payload_json LIKE ?
                ORDER BY event_id DESC
                LIMIT ?
                """,
                (like, like, int(limit)),
            ).fetchall()
            for r in rows:
                hits.append(
                    {
                        "type": "run_event",
                        "id": str(r["event_id"]),
                        "run_id": r["run_id"],
                        "thread_id": r["thread_id"],
                        "summary": f"{r['event_type']}",
                        "updated_at": r["created_at"],
                    }
                )

    sandbox_db_path = _sandbox_db_path()
    if sandbox_db_path.exists():
        with _connect(sandbox_db_path) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

            if "terminal_commands" in tables:
                rows = conn.execute(
                    """
                    SELECT command_id, terminal_id, status, created_at, stderr
                    FROM terminal_commands
                    WHERE command_id LIKE ? OR command_line LIKE ? OR stderr LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (like, like, like, int(limit)),
                ).fetchall()
                for r in rows:
                    hits.append(
                        {
                            "type": "terminal_command",
                            "id": r["command_id"],
                            "terminal_id": r["terminal_id"],
                            "summary": f"status={r['status']}",
                            "updated_at": r["created_at"],
                        }
                    )

            if "sandbox_leases" in tables:
                rows = conn.execute(
                    """
                    SELECT lease_id, provider_name, observed_state, updated_at, last_error
                    FROM sandbox_leases
                    WHERE lease_id LIKE ? OR provider_name LIKE ? OR last_error LIKE ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (like, like, like, int(limit)),
                ).fetchall()
                for r in rows:
                    hits.append(
                        {
                            "type": "lease",
                            "id": r["lease_id"],
                            "provider": r["provider_name"],
                            "summary": f"observed={r['observed_state']} error={r['last_error'] or ''}".strip(),
                            "updated_at": r["updated_at"],
                        }
                    )

            if "provider_events" in tables:
                rows = conn.execute(
                    """
                    SELECT event_id, provider_name, instance_id, event_type, created_at
                    FROM provider_events
                    WHERE event_type LIKE ? OR payload_json LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (like, like, int(limit)),
                ).fetchall()
                for r in rows:
                    hits.append(
                        {
                            "type": "provider_event",
                            "id": r["event_id"],
                            "provider": r["provider_name"],
                            "instance_id": r["instance_id"],
                            "summary": f"{r['event_type']}",
                            "updated_at": r["created_at"],
                        }
                    )

    # Deterministic-ish ordering: newest first where possible.
    def _key(h: dict[str, Any]) -> tuple:
        return (str(h.get("updated_at") or ""), str(h.get("type") or ""), str(h.get("id") or ""))

    hits.sort(key=_key, reverse=True)
    return hits[: int(limit)]
