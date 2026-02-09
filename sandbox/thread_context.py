"""Thread context tracking via ContextVar."""

from __future__ import annotations

from contextvars import ContextVar

_current_thread_id: ContextVar[str] = ContextVar("sandbox_thread_id", default="")


def set_current_thread_id(thread_id: str) -> None:
    _current_thread_id.set(thread_id)


def get_current_thread_id() -> str | None:
    value = _current_thread_id.get()
    return value if value else None
