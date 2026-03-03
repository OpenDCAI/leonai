"""Observe capabilities for monitor core."""

import json
import sqlite3
from datetime import datetime
from typing import Any

from sandbox.db import DEFAULT_DB_PATH

from .errors import MonitorCoreNotFoundError


def _connect_db() -> sqlite3.Connection:
    db = sqlite3.connect(str(DEFAULT_DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def format_time_ago(iso_timestamp: str | None) -> str:
    """Convert ISO timestamp to human readable 'X hours ago'."""
    if not iso_timestamp:
        return "never"
    # @@@naive-local-time - SQLite timestamps in this module are local-time strings.
    if "Z" in iso_timestamp:
        iso_timestamp = iso_timestamp.replace("Z", "")
    if "+" in iso_timestamp:
        iso_timestamp = iso_timestamp.split("+")[0]
    dt = datetime.fromisoformat(iso_timestamp)
    now = datetime.now()
    delta = now - dt

    if delta.days > 0:
        return f"{delta.days}d ago"
    hours = delta.seconds // 3600
    if hours > 0:
        return f"{hours}h ago"
    minutes = (delta.seconds % 3600) // 60
    if minutes > 0:
        return f"{minutes}m ago"
    return "just now"


def make_badge(desired: str | None, observed: str | None) -> dict[str, Any]:
    """Build a state badge dict handling null states."""
    if not desired and not observed:
        return {"desired": None, "observed": None, "converged": True, "color": "green", "text": "destroyed"}
    if desired == observed:
        return {"desired": desired, "observed": observed, "converged": True, "color": "green", "text": observed}
    return {
        "desired": desired,
        "observed": observed,
        "converged": False,
        "color": "yellow",
        "text": f"{observed} -> {desired}",
    }


def list_threads() -> dict[str, Any]:
    with _connect_db() as db:
        rows = db.execute(
            """
            SELECT
                cs.thread_id,
                COUNT(DISTINCT cs.chat_session_id) as session_count,
                MAX(cs.last_active_at) as last_active,
                sl.lease_id,
                sl.provider_name,
                sl.desired_state,
                sl.observed_state,
                sl.current_instance_id
            FROM chat_sessions cs
            LEFT JOIN sandbox_leases sl ON cs.lease_id = sl.lease_id
            GROUP BY cs.thread_id
            ORDER BY MAX(cs.last_active_at) DESC
            """
        ).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        badge = make_badge(row["desired_state"], row["observed_state"])
        items.append(
            {
                "thread_id": row["thread_id"],
                "thread_url": f"/thread/{row['thread_id']}",
                "session_count": row["session_count"],
                "last_active": row["last_active"],
                "last_active_ago": format_time_ago(row["last_active"]),
                "lease": {
                    "lease_id": row["lease_id"],
                    "lease_url": f"/lease/{row['lease_id']}" if row["lease_id"] else None,
                    "provider": row["provider_name"],
                    "instance_id": row["current_instance_id"],
                },
                "state_badge": badge,
            }
        )

    return {"title": "All Threads", "count": len(items), "items": items}


def get_thread(thread_id: str) -> dict[str, Any]:
    with _connect_db() as db:
        sessions = db.execute(
            """
            SELECT
                cs.chat_session_id,
                cs.status,
                cs.started_at,
                cs.ended_at,
                cs.close_reason,
                cs.lease_id,
                sl.provider_name,
                sl.desired_state,
                sl.observed_state,
                sl.current_instance_id,
                sl.last_error
            FROM chat_sessions cs
            LEFT JOIN sandbox_leases sl ON cs.lease_id = sl.lease_id
            WHERE cs.thread_id = ?
            ORDER BY cs.started_at DESC
            """,
            (thread_id,),
        ).fetchall()

    session_items: list[dict[str, Any]] = []
    lease_ids: set[str] = set()

    for session in sessions:
        if session["lease_id"]:
            lease_ids.add(session["lease_id"])

        session_items.append(
            {
                "session_id": session["chat_session_id"],
                "session_url": f"/session/{session['chat_session_id']}",
                "status": session["status"],
                "started_at": session["started_at"],
                "started_ago": format_time_ago(session["started_at"]),
                "ended_at": session["ended_at"],
                "ended_ago": format_time_ago(session["ended_at"]) if session["ended_at"] else None,
                "close_reason": session["close_reason"],
                "lease": {
                    "lease_id": session["lease_id"],
                    "lease_url": f"/lease/{session['lease_id']}" if session["lease_id"] else None,
                    "provider": session["provider_name"],
                    "instance_id": session["current_instance_id"],
                },
                "state_badge": make_badge(session["desired_state"], session["observed_state"]),
                "error": session["last_error"],
            }
        )

    return {
        "thread_id": thread_id,
        "breadcrumb": [
            {"label": "Threads", "url": "/threads"},
            {"label": thread_id[:8], "url": f"/thread/{thread_id}"},
        ],
        "sessions": {"title": "Sessions", "count": len(session_items), "items": session_items},
        "related_leases": {
            "title": "Related Leases",
            "items": [{"lease_id": lease_id, "lease_url": f"/lease/{lease_id}"} for lease_id in lease_ids],
        },
    }


def list_leases() -> dict[str, Any]:
    with _connect_db() as db:
        rows = db.execute(
            """
            SELECT
                sl.lease_id,
                sl.provider_name,
                sl.desired_state,
                sl.observed_state,
                sl.current_instance_id,
                sl.last_error,
                sl.updated_at,
                MAX(cs.thread_id) as thread_id
            FROM sandbox_leases sl
            LEFT JOIN chat_sessions cs ON sl.lease_id = cs.lease_id
            GROUP BY sl.lease_id
            ORDER BY sl.updated_at DESC
            """
        ).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        items.append(
            {
                "lease_id": row["lease_id"],
                "lease_url": f"/lease/{row['lease_id']}",
                "provider": row["provider_name"],
                "instance_id": row["current_instance_id"],
                "thread": {
                    "thread_id": row["thread_id"],
                    "thread_url": f"/thread/{row['thread_id']}" if row["thread_id"] else None,
                    "is_orphan": not row["thread_id"],
                },
                "state_badge": make_badge(row["desired_state"], row["observed_state"]),
                "error": row["last_error"],
                "updated_at": row["updated_at"],
                "updated_ago": format_time_ago(row["updated_at"]),
            }
        )

    return {"title": "All Leases", "count": len(items), "items": items}


def get_lease(lease_id: str) -> dict[str, Any]:
    with _connect_db() as db:
        lease = db.execute("SELECT * FROM sandbox_leases WHERE lease_id = ?", (lease_id,)).fetchone()

        if not lease:
            raise MonitorCoreNotFoundError("Lease not found")

        threads = db.execute(
            "SELECT DISTINCT thread_id FROM chat_sessions WHERE lease_id = ?",
            (lease_id,),
        ).fetchall()

        events = db.execute(
            """
            SELECT * FROM lease_events
            WHERE lease_id = ?
            ORDER BY created_at DESC
            """,
            (lease_id,),
        ).fetchall()

    badge = make_badge(lease["desired_state"], lease["observed_state"])
    badge["error"] = lease["last_error"]

    return {
        "lease_id": lease_id,
        "breadcrumb": [{"label": "Leases", "url": "/leases"}, {"label": lease_id, "url": f"/lease/{lease_id}"}],
        "info": {
            "provider": lease["provider_name"],
            "instance_id": lease["current_instance_id"],
            "created_at": lease["created_at"],
            "created_ago": format_time_ago(lease["created_at"]),
            "updated_at": lease["updated_at"],
            "updated_ago": format_time_ago(lease["updated_at"]),
        },
        "state": badge,
        "related_threads": {
            "title": "Related Threads",
            "items": [{"thread_id": thread["thread_id"], "thread_url": f"/thread/{thread['thread_id']}"} for thread in threads],
        },
        "lease_events": {
            "title": "Lease Events",
            "count": len(events),
            "items": [
                {
                    "event_id": event["event_id"],
                    "event_url": f"/event/{event['event_id']}",
                    "event_type": event["event_type"],
                    "source": event["source"],
                    "created_at": event["created_at"],
                    "created_ago": format_time_ago(event["created_at"]),
                }
                for event in events
            ],
        },
    }


def list_diverged() -> dict[str, Any]:
    with _connect_db() as db:
        rows = db.execute(
            """
            SELECT
                sl.lease_id,
                sl.provider_name,
                sl.desired_state,
                sl.observed_state,
                sl.current_instance_id,
                sl.last_error,
                sl.updated_at,
                cs.thread_id,
                CAST((julianday('now', 'localtime') - julianday(sl.updated_at)) * 24 AS INTEGER) as hours_diverged
            FROM sandbox_leases sl
            LEFT JOIN chat_sessions cs ON sl.lease_id = cs.lease_id
            WHERE sl.desired_state != sl.observed_state
            ORDER BY hours_diverged DESC
            """
        ).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        items.append(
            {
                "lease_id": row["lease_id"],
                "lease_url": f"/lease/{row['lease_id']}",
                "provider": row["provider_name"],
                "instance_id": row["current_instance_id"],
                "thread": {
                    "thread_id": row["thread_id"],
                    "thread_url": f"/thread/{row['thread_id']}" if row["thread_id"] else None,
                    "is_orphan": not row["thread_id"],
                },
                "state_badge": {
                    "desired": row["desired_state"],
                    "observed": row["observed_state"],
                    "hours_diverged": row["hours_diverged"],
                    "color": "red" if row["hours_diverged"] > 24 else "yellow",
                },
                "error": row["last_error"],
            }
        )

    return {
        "title": "Diverged Leases",
        "description": "Leases where desired_state != observed_state",
        "count": len(items),
        "items": items,
    }


def list_events(limit: int = 100) -> dict[str, Any]:
    with _connect_db() as db:
        rows = db.execute(
            """
            SELECT le.event_id, le.lease_id, le.event_type, le.source,
                   le.payload_json, le.error, le.created_at,
                   sl.provider_name
            FROM lease_events le
            LEFT JOIN sandbox_leases sl ON le.lease_id = sl.lease_id
            ORDER BY le.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        items.append(
            {
                "event_id": row["event_id"],
                "event_url": f"/event/{row['event_id']}",
                "event_type": row["event_type"],
                "source": row["source"],
                "provider": row["provider_name"],
                "lease": {
                    "lease_id": row["lease_id"],
                    "lease_url": f"/lease/{row['lease_id']}" if row["lease_id"] else None,
                },
                "error": row["error"],
                "created_at": row["created_at"],
                "created_ago": format_time_ago(row["created_at"]),
            }
        )

    return {
        "title": "Lease Events",
        "description": "Audit log of all lease lifecycle operations",
        "count": len(items),
        "items": items,
    }


def get_event(event_id: str) -> dict[str, Any]:
    with _connect_db() as db:
        event = db.execute(
            """
            SELECT le.*, sl.provider_name
            FROM lease_events le
            LEFT JOIN sandbox_leases sl ON le.lease_id = sl.lease_id
            WHERE le.event_id = ?
            """,
            (event_id,),
        ).fetchone()

    if not event:
        raise MonitorCoreNotFoundError("Event not found")

    payload = json.loads(event["payload_json"]) if event["payload_json"] else {}

    return {
        "event_id": event_id,
        "breadcrumb": [
            {"label": "Events", "url": "/events"},
            {"label": event["event_type"], "url": f"/event/{event_id}"},
        ],
        "info": {
            "event_type": event["event_type"],
            "source": event["source"],
            "provider": event["provider_name"],
            "created_at": event["created_at"],
            "created_ago": format_time_ago(event["created_at"]),
        },
        "related_lease": {
            "lease_id": event["lease_id"],
            "lease_url": f"/lease/{event['lease_id']}" if event["lease_id"] else None,
        },
        "error": event["error"],
        "payload": payload,
    }
