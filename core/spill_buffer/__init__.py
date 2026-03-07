# Backward compat - deprecated, use core.runtime.middleware.spill_buffer instead
"""SpillBuffer - catches oversized tool outputs, writes to disk, returns preview."""

from core.runtime.middleware.spill_buffer import SpillBufferMiddleware, spill_if_needed  # noqa: F401

__all__ = ["SpillBufferMiddleware", "spill_if_needed"]
