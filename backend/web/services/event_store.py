"""Persistent run-event service via storage repository boundary."""

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any

import aiosqlite
from core.storage.runtime import build_storage_container

_DB_PATH = Path.home() / ".leon" / "leon.db"
_default_run_event_repo: Any | None = None
_default_run_event_repo_path: Path | None = None

# Single async connection, lazily created, serialises all writes via the event loop.
# NOTE: assumes single uvicorn worker. Multi-worker (--workers > 1) needs a connection pool.
_conn: aiosqlite.Connection | None = None
_lock = asyncio.Lock()


async def _get_conn() -> aiosqlite.Connection:
    global _conn
    if _conn is not None:
        return _conn
    async with _lock:
        if _conn is not None:
            return _conn
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = await aiosqlite.connect(str(_DB_PATH))
        await _conn.execute("PRAGMA journal_mode=WAL")
        await _conn.execute("PRAGMA synchronous=NORMAL")
        return _conn


def init_event_store() -> None:
    """Create the run_events table if it doesn't exist (sync, called once at import)."""
    global _default_run_event_repo, _default_run_event_repo_path
    if _default_run_event_repo is not None:
        close_fn = getattr(_default_run_event_repo, "close", None)
        if callable(close_fn):
            close_fn()
    _default_run_event_repo = None
    _default_run_event_repo_path = None
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
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
    conn.close()


def _resolve_run_event_repo(run_event_repo: Any | None) -> Any:
    if run_event_repo is not None:
        return run_event_repo

    global _default_run_event_repo, _default_run_event_repo_path
    if _default_run_event_repo is not None and _default_run_event_repo_path == _DB_PATH:
        return _default_run_event_repo

    if _default_run_event_repo is not None:
        close_fn = getattr(_default_run_event_repo, "close", None)
        if callable(close_fn):
            close_fn()
        _default_run_event_repo = None
        _default_run_event_repo_path = None

    container = build_storage_container(main_db_path=_DB_PATH)
    repo_factory = getattr(container, "run_event_repo", None)
    if not callable(repo_factory):
        raise RuntimeError("StorageContainer must expose callable run_event_repo().")
    # @@@event-store-single-path - keep one persistence boundary; when caller omits repo, resolve default repo from storage container.
    _default_run_event_repo = repo_factory()
    _default_run_event_repo_path = _DB_PATH
    return _default_run_event_repo


async def append_event(
    thread_id: str,
    run_id: str,
    event: dict[str, Any],
    message_id: str | None = None,
    run_event_repo: Any | None = None,
) -> int:
    """Persist one SSE event and return its sequence number."""
    repo = _resolve_run_event_repo(run_event_repo)
    payload = _event_payload_to_dict(event)
    return int(
        await asyncio.to_thread(
            repo.append_event,
            thread_id,
            run_id,
            event.get("event", ""),
            payload,
            message_id,
        )
    )


async def read_events_after(
    thread_id: str,
    run_id: str,
    after_seq: int = 0,
    run_event_repo: Any | None = None,
) -> list[dict[str, Any]]:
    """Return events with seq > after_seq for the given run."""
    repo = _resolve_run_event_repo(run_event_repo)
    rows = await asyncio.to_thread(
        repo.list_events,
        thread_id,
        run_id,
        after=after_seq,
        limit=10000,
    )
    return [
        {
            "seq": row.get("seq"),
            "event": row.get("event_type", ""),
            "data": json.dumps(row.get("data", {}), ensure_ascii=False),
            "message_id": row.get("message_id"),
        }
        for row in rows
    ]


async def get_last_seq(thread_id: str, run_event_repo: Any | None = None) -> int:
    """Return the highest seq for a thread, or 0."""
    repo = _resolve_run_event_repo(run_event_repo)
    return int(await asyncio.to_thread(repo.latest_seq, thread_id))


async def get_latest_run_id(thread_id: str, run_event_repo: Any | None = None) -> str | None:
    """Return the run_id of the most recent run for a thread, or None."""
    repo = _resolve_run_event_repo(run_event_repo)
    return await asyncio.to_thread(repo.latest_run_id, thread_id)


async def cleanup_old_runs(
    thread_id: str,
    keep_latest: int = 1,
    run_event_repo: Any | None = None,
) -> int:
    """Delete all but the N most recent runs for a thread. Returns deleted count."""
    repo = _resolve_run_event_repo(run_event_repo)
    run_ids = await asyncio.to_thread(repo.list_run_ids, thread_id)
    if len(run_ids) <= keep_latest:
        return 0
    old_ids = run_ids[keep_latest:]
    return int(await asyncio.to_thread(repo.delete_runs, thread_id, old_ids))


async def cleanup_thread(thread_id: str, run_event_repo: Any | None = None) -> int:
    """Delete all events for a thread. Returns deleted count."""
    repo = _resolve_run_event_repo(run_event_repo)
    return int(await asyncio.to_thread(repo.delete_thread_events, thread_id))


def _event_payload_to_dict(event: dict[str, Any]) -> dict[str, Any]:
    raw_data = event.get("data", {})
    if isinstance(raw_data, dict):
        return raw_data
    if raw_data in (None, ""):
        return {}
    if not isinstance(raw_data, str):
        raise RuntimeError(
            "Run event data must be a dict or JSON string when using storage_container run_event_repo."
        )
    try:
        payload = json.loads(raw_data)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Run event data must be valid JSON when using storage_container run_event_repo."
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            "Run event data JSON must decode to an object when using storage_container run_event_repo."
        )
    return payload
