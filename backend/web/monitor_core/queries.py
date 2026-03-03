"""SQL queries for monitor core observe module."""

from __future__ import annotations

import sqlite3

from sandbox.db import DEFAULT_DB_PATH


def connect_db() -> sqlite3.Connection:
    db = sqlite3.connect(str(DEFAULT_DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def query_threads(db: sqlite3.Connection) -> list[sqlite3.Row]:
    return db.execute(
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


def query_thread_sessions(db: sqlite3.Connection, thread_id: str) -> list[sqlite3.Row]:
    return db.execute(
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


def query_leases(db: sqlite3.Connection) -> list[sqlite3.Row]:
    return db.execute(
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


def query_lease(db: sqlite3.Connection, lease_id: str) -> sqlite3.Row | None:
    return db.execute(
        "SELECT * FROM sandbox_leases WHERE lease_id = ?",
        (lease_id,),
    ).fetchone()


def query_lease_threads(db: sqlite3.Connection, lease_id: str) -> list[sqlite3.Row]:
    return db.execute(
        "SELECT DISTINCT thread_id FROM chat_sessions WHERE lease_id = ?",
        (lease_id,),
    ).fetchall()


def query_lease_events(db: sqlite3.Connection, lease_id: str) -> list[sqlite3.Row]:
    return db.execute(
        """
        SELECT * FROM lease_events
        WHERE lease_id = ?
        ORDER BY created_at DESC
        """,
        (lease_id,),
    ).fetchall()


def query_diverged(db: sqlite3.Connection) -> list[sqlite3.Row]:
    return db.execute(
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


def query_events(db: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    return db.execute(
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


def query_event(db: sqlite3.Connection, event_id: str) -> sqlite3.Row | None:
    return db.execute(
        """
        SELECT le.*, sl.provider_name
        FROM lease_events le
        LEFT JOIN sandbox_leases sl ON le.lease_id = sl.lease_id
        WHERE le.event_id = ?
        """,
        (event_id,),
    ).fetchone()
