"""Observe capabilities for monitor core."""

from typing import Any

from .errors import MonitorCoreNotFoundError
from .mappers import (
    map_diverged,
    map_event_detail,
    map_events,
    map_lease_detail,
    map_leases,
    map_thread_detail,
    map_threads,
)
from .queries import (
    connect_db,
    query_diverged,
    query_event,
    query_events,
    query_lease,
    query_lease_events,
    query_lease_threads,
    query_leases,
    query_thread_sessions,
    query_threads,
)


def list_threads() -> dict[str, Any]:
    with connect_db() as db:
        rows = query_threads(db)
    return map_threads(rows)


def get_thread(thread_id: str) -> dict[str, Any]:
    with connect_db() as db:
        sessions = query_thread_sessions(db, thread_id)
    return map_thread_detail(thread_id, sessions)


def list_leases() -> dict[str, Any]:
    with connect_db() as db:
        rows = query_leases(db)
    return map_leases(rows)


def get_lease(lease_id: str) -> dict[str, Any]:
    with connect_db() as db:
        lease = query_lease(db, lease_id)
        if not lease:
            raise MonitorCoreNotFoundError("Lease not found")
        threads = query_lease_threads(db, lease_id)
        events = query_lease_events(db, lease_id)
    return map_lease_detail(lease_id, lease, threads, events)


def list_diverged() -> dict[str, Any]:
    with connect_db() as db:
        rows = query_diverged(db)
    return map_diverged(rows)


def list_events(limit: int = 100) -> dict[str, Any]:
    with connect_db() as db:
        rows = query_events(db, limit)
    return map_events(rows)


def get_event(event_id: str) -> dict[str, Any]:
    with connect_db() as db:
        event = query_event(db, event_id)
    if not event:
        raise MonitorCoreNotFoundError("Event not found")
    return map_event_detail(event_id, event)
