"""SpillBuffer - catches oversized tool outputs, writes to disk, returns preview."""

from core.spill_buffer.middleware import SpillBufferMiddleware
from core.spill_buffer.spill import spill_if_needed

__all__ = ["SpillBufferMiddleware", "spill_if_needed"]
