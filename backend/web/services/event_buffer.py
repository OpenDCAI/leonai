"""In-memory event buffer for decoupling agent execution from SSE consumers."""

import asyncio
from dataclasses import dataclass, field


@dataclass
class RunEventBuffer:
    """Ordered event buffer with cursor-based reading and completion signal."""

    events: list[dict] = field(default_factory=list)
    finished: asyncio.Event = field(default_factory=asyncio.Event)
    _notify: asyncio.Condition = field(default_factory=asyncio.Condition)
    run_id: str = ""

    async def put(self, event: dict) -> None:
        self.events.append(event)
        async with self._notify:
            self._notify.notify_all()

    async def mark_done(self) -> None:
        self.finished.set()
        async with self._notify:
            self._notify.notify_all()

    async def read(self, cursor: int) -> tuple[list[dict], int]:
        """Return (new_events, new_cursor). Waits if no new events and not finished."""
        while True:
            if cursor < len(self.events):
                new = self.events[cursor:]
                return new, len(self.events)
            if self.finished.is_set():
                return [], cursor
            async with self._notify:
                await self._notify.wait()

    async def read_with_timeout(self, cursor: int, timeout: float = 30) -> tuple[list[dict] | None, int]:
        """Same as read() but returns (None, cursor) on timeout instead of blocking forever."""
        if cursor < len(self.events):
            return self.events[cursor:], len(self.events)
        if self.finished.is_set():
            return [], cursor
        async with self._notify:
            try:
                await asyncio.wait_for(self._notify.wait(), timeout)
            except TimeoutError:
                return None, cursor
        if cursor < len(self.events):
            return self.events[cursor:], len(self.events)
        return None, cursor
