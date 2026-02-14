from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from enum import Enum
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
    def __init__(self, thread_id: str, run_id: str) -> None:
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

        async with self._cond:
            self._seq += 1
            ev = RunEvent(seq=self._seq, ts=time.time(), event=event, data=payload)
            self._events.append(ev)
            self._cond.notify_all()
            return ev.seq

    async def finish(self, status: RunStatus, error: str | None = None) -> None:
        async with self._cond:
            self.status = status
            self.error = error
            self.ended_at = time.time()
            self._cond.notify_all()

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
    def __init__(self) -> None:
        self._active_by_thread: dict[str, str] = {}
        self._runs: dict[str, RunRecord] = {}
        self._guard = asyncio.Lock()

    async def start_run(self, thread_id: str) -> RunRecord:
        async with self._guard:
            active = self._active_by_thread.get(thread_id)
            if active:
                rec = self._runs.get(active)
                if rec and rec.status == RunStatus.RUNNING:
                    raise RuntimeError(f"thread has active run run_id={active}")
                self._active_by_thread.pop(thread_id, None)

            run_id = str(uuid.uuid4())
            rec = RunRecord(thread_id=thread_id, run_id=run_id)
            self._runs[run_id] = rec
            self._active_by_thread[thread_id] = run_id
            return rec

    async def set_task(self, run_id: str, task: asyncio.Task) -> None:
        async with self._guard:
            rec = self._runs.get(run_id)
            if rec:
                rec.task = task

    async def cancel(self, thread_id: str, run_id: str) -> None:
        async with self._guard:
            rec = self._runs.get(run_id)
            if not rec or rec.thread_id != thread_id:
                raise KeyError("run not found")
            task = rec.task
            if task and not task.done():
                task.cancel()

    async def get_active_run_id(self, thread_id: str) -> str | None:
        async with self._guard:
            rid = self._active_by_thread.get(thread_id)
            rec = self._runs.get(rid) if rid else None
            if rec and rec.status == RunStatus.RUNNING:
                return rid
            return None

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

    async def shutdown(self) -> None:
        async with self._guard:
            tasks = [r.task for r in self._runs.values() if r.task and not r.task.done()]
        for t in tasks:
            t.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def stream_sse(
        self,
        thread_id: str,
        run_id: str,
        *,
        cursor: int = 0,
    ) -> AsyncGenerator[dict[str, str], None]:
        rec = await self.get_run(thread_id, run_id)
        if not rec:
            yield {"event": "error", "data": json.dumps({"error": "run not found"}, ensure_ascii=False)}
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

