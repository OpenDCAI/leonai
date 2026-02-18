"""Per-thread persistent config schema (L2 in the L1/L2/L3 config hierarchy)."""

from pydantic import BaseModel


class ThreadConfig(BaseModel):
    """Per-thread persistent config stored in SQLite thread_metadata."""

    sandbox_type: str = "local"
    cwd: str | None = None
    model: str | None = None
    queue_mode: str = "steer"
