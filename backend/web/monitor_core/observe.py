"""Observe capabilities for monitor core."""

from typing import Any

from storage.providers.sqlite.sandbox_monitor_repo import SQLiteSandboxMonitorRepo

from . import mappers


def _repo() -> SQLiteSandboxMonitorRepo:
    return SQLiteSandboxMonitorRepo()


def list_threads() -> dict[str, Any]:
    repo = _repo()
    try:
        rows = repo.query_threads()
    finally:
        repo.close()
    return mappers.map_threads(rows)


def get_thread(thread_id: str) -> dict[str, Any]:
    repo = _repo()
    try:
        sessions = repo.query_thread_sessions(thread_id)
    finally:
        repo.close()
    return mappers.map_thread_detail(thread_id, sessions)


def list_leases() -> dict[str, Any]:
    repo = _repo()
    try:
        rows = repo.query_leases()
    finally:
        repo.close()
    return mappers.map_leases(rows)


def get_lease(lease_id: str) -> dict[str, Any]:
    repo = _repo()
    try:
        lease = repo.query_lease(lease_id)
        if not lease:
            raise KeyError("Lease not found")
        threads = repo.query_lease_threads(lease_id)
        events = repo.query_lease_events(lease_id)
    finally:
        repo.close()
    return mappers.map_lease_detail(lease_id, lease, threads, events)


def list_diverged() -> dict[str, Any]:
    repo = _repo()
    try:
        rows = repo.query_diverged()
    finally:
        repo.close()
    return mappers.map_diverged(rows)


def list_events(limit: int = 100) -> dict[str, Any]:
    repo = _repo()
    try:
        rows = repo.query_events(limit)
    finally:
        repo.close()
    return mappers.map_events(rows)


def get_event(event_id: str) -> dict[str, Any]:
    repo = _repo()
    try:
        event = repo.query_event(event_id)
    finally:
        repo.close()
    if not event:
        raise KeyError("Event not found")
    return mappers.map_event_detail(event_id, event)
