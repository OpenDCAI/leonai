"""Thread context tracking via ContextVar.

Works across async boundaries. Set by TUI before each agent invoke.
"""

from __future__ import annotations

from contextvars import ContextVar

_current_thread_id: ContextVar[str] = ContextVar("sandbox_thread_id", default="")


def set_current_thread_id(thread_id: str):
    """Set thread_id for current context (called by TUI before agent invoke)."""
    _current_thread_id.set(thread_id)


def get_current_thread_id() -> str | None:
    """Get thread_id for current context."""
    value = _current_thread_id.get()
    return value if value else None
