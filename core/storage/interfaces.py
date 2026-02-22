"""Storage repository interfaces."""

from typing import Protocol


class ThreadMetadataRepo(Protocol):
    """Persistence contract for thread metadata."""

    def save_thread_metadata(self, thread_id: str, sandbox_type: str, cwd: str | None) -> None:
        """Persist thread sandbox type and cwd."""

    def save_thread_model(self, thread_id: str, model: str) -> None:
        """Persist thread model selection."""

    def lookup_thread_model(self, thread_id: str) -> str | None:
        """Load persisted model for a thread."""

    def lookup_thread_metadata(self, thread_id: str) -> tuple[str, str | None] | None:
        """Load persisted (sandbox_type, cwd) for a thread."""
