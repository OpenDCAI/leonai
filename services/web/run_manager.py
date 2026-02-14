from __future__ import annotations

import asyncio
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator


class RunStatus(str, Enum):
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class RunEvent:
    seq: int
    ts: float
    event: str
    data: str


class RunRecord:
    def __init__(
        self,
        thread_id: str,
        run_id: str,
        *,
        persist_event: Any | None = None,
        persist_finish: Any | None = None,
    ) -> None:
        self.thread_id = thread_id
        self.run_id = run_id
        self.status: RunStatus = RunStatus.RUNNING
        self.error: str | None = None
        self.started_at = time.time()
        self.ended_at: float | None = None

        self._events: list[RunEvent] = []
        self._seq = 0
        self._cond = asyncio.Condition()
        self._task: asyncio.Task | None = None
        self._persist_event = persist_event
        self._persist_finish = persist_finish

    @property
    def task(self) -> asyncio.Task | None:
        return self._task

    @task.setter
    def task(self, task: asyncio.Task | None) -> None:
        self._task = task

    @property
    def last_seq(self) -> int:
        return self._seq

    def events_after(self, cursor: int) -> list[RunEvent]:
        # seq starts from 1, so index is seq-1
        if cursor < 0:
            cursor = 0
        start_idx = cursor
        if start_idx <= 0:
            return list(self._events)
        if start_idx >= len(self._events):
            return []
        return self._events[start_idx:]

    async def append(self, event: str, data: Any) -> int:
        if isinstance(data, str):
            payload = data
        else:
            payload = json.dumps(data, ensure_ascii=False)

        ev: RunEvent | None = None
        async with self._cond:
            self._seq += 1
            ev = RunEvent(seq=self._seq, ts=time.time(), event=event, data=payload)
            self._events.append(ev)
            self._cond.notify_all()

        # Persist outside the condition so streaming waits aren't blocked by sqlite IO.
        if self._persist_event:
            await self._persist_event(ev)

        return ev.seq

    async def finish(self, status: RunStatus, error: str | None = None) -> None:
        async with self._cond:
            self.status = status
            self.error = error
            self.ended_at = time.time()
            self._cond.notify_all()
            ended_at = self.ended_at

        if self._persist_finish:
            await self._persist_finish(status, error, ended_at)

    async def wait_for_more(self, cursor: int, timeout: float = 15.0) -> None:
        async with self._cond:
            if self._seq > cursor:
                return
            if self.status != RunStatus.RUNNING:
                return
            try:
                await asyncio.wait_for(self._cond.wait(), timeout=timeout)
            except TimeoutError:
                return


class RunManager:
    def __init__(self, *, db_path: Path | None = None) -> None:
        self._active_by_thread: dict[str, str] = {}
        self._runs: dict[str, RunRecord] = {}
        self._guard = asyncio.Lock()
        self._db_path = Path(db_path) if db_path else None

    def has_db(self) -> bool:
        return self._db_path is not None

    async def ensure_schema(self) -> None:
        if not self._db_path:
            return

        def _init() -> None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(self._db_path), timeout=30) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS run_records (
                        run_id TEXT PRIMARY KEY,
                        thread_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        error TEXT,
                        started_at REAL NOT NULL,
                        ended_at REAL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS run_events (
                        run_id TEXT NOT NULL,
                        thread_id TEXT NOT NULL,
                        seq INTEGER NOT NULL,
                        ts REAL NOT NULL,
                        event TEXT NOT NULL,
                        data TEXT NOT NULL,
                        PRIMARY KEY (run_id, seq)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS run_active (
                        thread_id TEXT PRIMARY KEY,
                        run_id TEXT NOT NULL,
                        updated_at REAL NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS run_signals (
                        run_id TEXT PRIMARY KEY,
                        cancel_requested INTEGER NOT NULL DEFAULT 0,
                        updated_at REAL NOT NULL
                    )
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_run_events_thread_id ON run_events(thread_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_run_events_run_id ON run_events(run_id)")
                conn.commit()

        await asyncio.to_thread(_init)

    async def _db_claim_thread(self, thread_id: str, run_id: str) -> None:
        if not self._db_path:
            return

        def _claim() -> None:
            now = time.time()
            with sqlite3.connect(str(self._db_path), timeout=30) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                try:
                    conn.execute(
                        "INSERT INTO run_active(thread_id, run_id, updated_at) VALUES (?, ?, ?)",
                        (thread_id, run_id, now),
                    )
                    conn.commit()
                    return
                except sqlite3.IntegrityError:
                    row = conn.execute("SELECT run_id FROM run_active WHERE thread_id = ?", (thread_id,)).fetchone()
                    existing = row[0] if row else None
                    if not existing:
                        raise
                    status_row = conn.execute(
                        "SELECT status FROM run_records WHERE run_id = ? AND thread_id = ?",
                        (existing, thread_id),
                    ).fetchone()
                    status = status_row[0] if status_row else None
                    if status == RunStatus.RUNNING.value:
                        raise RuntimeError(f"thread has active run run_id={existing}")
                    # Stale mapping, clear and let caller retry.
                    conn.execute("DELETE FROM run_active WHERE thread_id = ?", (thread_id,))
                    conn.commit()
                    raise RuntimeError("stale active run mapping cleared; retry")

        await asyncio.to_thread(_claim)

    async def _db_insert_run_start(self, rec: RunRecord) -> None:
        if not self._db_path:
            return

        def _ins() -> None:
            now = rec.started_at
            with sqlite3.connect(str(self._db_path), timeout=30) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute(
                    "INSERT INTO run_records(run_id, thread_id, status, error, started_at, ended_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (rec.run_id, rec.thread_id, RunStatus.RUNNING.value, None, now, None),
                )
                conn.execute(
                    "INSERT OR REPLACE INTO run_signals(run_id, cancel_requested, updated_at) VALUES (?, ?, ?)",
                    (rec.run_id, 0, time.time()),
                )
                conn.commit()

        await asyncio.to_thread(_ins)

    async def _db_insert_event(self, ev: RunEvent, thread_id: str, run_id: str) -> None:
        if not self._db_path:
            return

        def _ins() -> None:
            with sqlite3.connect(str(self._db_path), timeout=30) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute(
                    "INSERT INTO run_events(run_id, thread_id, seq, ts, event, data) VALUES (?, ?, ?, ?, ?, ?)",
                    (run_id, thread_id, ev.seq, ev.ts, ev.event, ev.data),
                )
                conn.commit()

        await asyncio.to_thread(_ins)

    async def _db_finish_run(self, thread_id: str, run_id: str, status: RunStatus, error: str | None, ended_at: float | None) -> None:
        if not self._db_path:
            return

        def _finish() -> None:
            with sqlite3.connect(str(self._db_path), timeout=30) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute(
                    "UPDATE run_records SET status = ?, error = ?, ended_at = ? WHERE run_id = ? AND thread_id = ?",
                    (status.value, error, ended_at, run_id, thread_id),
                )
                # Best-effort: clear mapping if it still points to this run.
                conn.execute(
                    "DELETE FROM run_active WHERE thread_id = ? AND run_id = ?",
                    (thread_id, run_id),
                )
                conn.commit()

        await asyncio.to_thread(_finish)

    async def start_run(self, thread_id: str) -> RunRecord:
        await self.ensure_schema()

        # Cross-worker claim must happen before we expose the run.
        while True:
            run_id = str(uuid.uuid4())
            if self._db_path:
                try:
                    await self._db_claim_thread(thread_id, run_id)
                except RuntimeError as e:
                    # Stale mapping cleared; retry once with a fresh run_id.
                    if "retry" in str(e):
                        continue
                    raise
            break

        async with self._guard:
            active = self._active_by_thread.get(thread_id)
            if active:
                rec_existing = self._runs.get(active)
                if rec_existing and rec_existing.status == RunStatus.RUNNING:
                    raise RuntimeError(f"thread has active run run_id={active}")
                self._active_by_thread.pop(thread_id, None)

            async def _persist_event(ev: RunEvent) -> None:
                await self._db_insert_event(ev, thread_id, run_id)

            async def _persist_finish(status: RunStatus, error: str | None, ended_at: float | None) -> None:
                await self._db_finish_run(thread_id, run_id, status, error, ended_at)

            rec = RunRecord(
                thread_id=thread_id,
                run_id=run_id,
                persist_event=_persist_event if self._db_path else None,
                persist_finish=_persist_finish if self._db_path else None,
            )
            self._runs[run_id] = rec
            self._active_by_thread[thread_id] = run_id

        if self._db_path:
            await self._db_insert_run_start(rec)

        return rec

    async def set_task(self, run_id: str, task: asyncio.Task) -> None:
        async with self._guard:
            rec = self._runs.get(run_id)
            if rec:
                rec.task = task

    async def cancel(self, thread_id: str, run_id: str) -> None:
        await self.ensure_schema()

        if self._db_path:
            def _signal() -> None:
                with sqlite3.connect(str(self._db_path), timeout=30) as conn:
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute(
                        "INSERT OR REPLACE INTO run_signals(run_id, cancel_requested, updated_at) VALUES (?, ?, ?)",
                        (run_id, 1, time.time()),
                    )
                    conn.commit()

            await asyncio.to_thread(_signal)

        async with self._guard:
            rec = self._runs.get(run_id)
            if not rec or rec.thread_id != thread_id:
                raise KeyError("run not found")
            task = rec.task
            if task and not task.done():
                task.cancel()

    async def is_cancel_requested(self, thread_id: str, run_id: str) -> bool:
        if not self._db_path:
            return False

        def _get() -> bool:
            with sqlite3.connect(str(self._db_path), timeout=30) as conn:
                row = conn.execute(
                    "SELECT cancel_requested FROM run_signals WHERE run_id = ?",
                    (run_id,),
                ).fetchone()
                if not row:
                    return False
                return bool(row[0])

        return await asyncio.to_thread(_get)

    async def get_active_run_id(self, thread_id: str) -> str | None:
        async with self._guard:
            rid = self._active_by_thread.get(thread_id)
            rec = self._runs.get(rid) if rid else None
            if rec and rec.status == RunStatus.RUNNING:
                return rid

        if not self._db_path:
            return None

        await self.ensure_schema()

        def _db_get() -> str | None:
            with sqlite3.connect(str(self._db_path), timeout=30) as conn:
                row = conn.execute("SELECT run_id FROM run_active WHERE thread_id = ?", (thread_id,)).fetchone()
                if not row:
                    return None
                run_id = row[0]
                status_row = conn.execute(
                    "SELECT status FROM run_records WHERE run_id = ? AND thread_id = ?",
                    (run_id, thread_id),
                ).fetchone()
                status = status_row[0] if status_row else None
                if status == RunStatus.RUNNING.value:
                    return run_id
                conn.execute("DELETE FROM run_active WHERE thread_id = ?", (thread_id,))
                conn.commit()
                return None

        return await asyncio.to_thread(_db_get)

    async def get_run(self, thread_id: str, run_id: str) -> RunRecord | None:
        async with self._guard:
            rec = self._runs.get(run_id)
            if not rec or rec.thread_id != thread_id:
                return None
            return rec

    async def clear_active_if_match(self, thread_id: str, run_id: str) -> None:
        async with self._guard:
            if self._active_by_thread.get(thread_id) == run_id:
                self._active_by_thread.pop(thread_id, None)
        if self._db_path:
            await self.ensure_schema()

            def _clear() -> None:
                with sqlite3.connect(str(self._db_path), timeout=30) as conn:
                    conn.execute(
                        "DELETE FROM run_active WHERE thread_id = ? AND run_id = ?",
                        (thread_id, run_id),
                    )
                    conn.commit()

            await asyncio.to_thread(_clear)

    async def shutdown(self) -> None:
        async with self._guard:
            tasks = [r.task for r in self._runs.values() if r.task and not r.task.done()]
        for t in tasks:
            t.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def get_run_cursor(self, thread_id: str, run_id: str) -> int:
        rec = await self.get_run(thread_id, run_id)
        if rec:
            return rec.last_seq
        if not self._db_path:
            return 0
        await self.ensure_schema()

        def _max() -> int:
            with sqlite3.connect(str(self._db_path), timeout=30) as conn:
                row = conn.execute(
                    "SELECT MAX(seq) FROM run_events WHERE run_id = ? AND thread_id = ?",
                    (run_id, thread_id),
                ).fetchone()
                return int(row[0] or 0)

        return await asyncio.to_thread(_max)

    async def get_last_status(self, thread_id: str, run_id: str) -> dict[str, Any] | None:
        if not self._db_path:
            return None
        await self.ensure_schema()

        def _get() -> dict[str, Any] | None:
            with sqlite3.connect(str(self._db_path), timeout=30) as conn:
                row = conn.execute(
                    "SELECT data FROM run_events WHERE run_id = ? AND thread_id = ? AND event = 'status' ORDER BY seq DESC LIMIT 1",
                    (run_id, thread_id),
                ).fetchone()
                if not row:
                    return None
                try:
                    payload = json.loads(row[0])
                except Exception:
                    return None
                return payload if isinstance(payload, dict) else None

        return await asyncio.to_thread(_get)

    async def _stream_sse_db(
        self,
        thread_id: str,
        run_id: str,
        *,
        cursor: int = 0,
    ) -> AsyncGenerator[dict[str, str], None]:
        if not self._db_path:
            yield {"event": "error", "data": json.dumps({"error": "run not found"}, ensure_ascii=False)}
            return

        await self.ensure_schema()

        last_seen = cursor
        while True:
            def _fetch() -> tuple[list[RunEvent], str | None]:
                with sqlite3.connect(str(self._db_path), timeout=30) as conn:
                    rows = conn.execute(
                        "SELECT seq, ts, event, data FROM run_events WHERE run_id = ? AND thread_id = ? AND seq > ? ORDER BY seq ASC LIMIT 200",
                        (run_id, thread_id, last_seen),
                    ).fetchall()
                    events = [RunEvent(seq=int(r[0]), ts=float(r[1]), event=str(r[2]), data=str(r[3])) for r in rows]
                    status_row = conn.execute(
                        "SELECT status FROM run_records WHERE run_id = ? AND thread_id = ?",
                        (run_id, thread_id),
                    ).fetchone()
                    status = status_row[0] if status_row else None
                    return events, status

            events, status = await asyncio.to_thread(_fetch)
            if events:
                for ev in events:
                    last_seen = ev.seq
                    yield {"event": ev.event, "data": ev.data, "id": str(ev.seq)}
                continue

            if status and status != RunStatus.RUNNING.value:
                return

            await asyncio.sleep(0.2)

    async def stream_sse(
        self,
        thread_id: str,
        run_id: str,
        *,
        cursor: int = 0,
    ) -> AsyncGenerator[dict[str, str], None]:
        rec = await self.get_run(thread_id, run_id)
        if not rec:
            # In multi-worker deployments, the run can be owned by another process. Fall back to sqlite.
            async for item in self._stream_sse_db(thread_id, run_id, cursor=cursor):
                yield item
            return

        # cursor is last seen seq, so we start after it
        last_seen = cursor
        while True:
            events = rec.events_after(last_seen)
            if events:
                for ev in events:
                    last_seen = ev.seq
                    yield {"event": ev.event, "data": ev.data, "id": str(ev.seq)}
                continue

            if rec.status != RunStatus.RUNNING:
                return

            await rec.wait_for_more(last_seen)
