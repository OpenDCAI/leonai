"""
MessageQueue — simple task queue for inter-process communication.

Used for: sandbox lifecycle commands, async notifications, etc.
SQLite-backed for single-machine; swap to Redis when scaling.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class Message:
    """A message in the queue."""

    id: str
    queue: str  # queue name (e.g. "sandbox.lifecycle", "sandbox.notify")
    payload: dict[str, Any]
    status: str = "pending"  # pending -> claimed -> completed | failed
    created_at: datetime | None = None
    claimed_at: datetime | None = None


class MessageQueue(ABC):
    """Abstract interface for a simple task queue.

    Operations are atomic: claim uses SELECT-then-UPDATE
    to prevent double-processing.
    """

    @abstractmethod
    def enqueue(self, queue: str, payload: dict[str, Any]) -> str:
        """Add a message to the queue. Returns message ID."""

    @abstractmethod
    def claim(self, queue: str) -> Message | None:
        """Atomically claim the oldest pending message. Returns None if empty."""

    @abstractmethod
    def complete(self, message_id: str) -> None:
        """Mark a claimed message as completed."""

    @abstractmethod
    def fail(self, message_id: str, error: str = "") -> None:
        """Mark a claimed message as failed."""

    @abstractmethod
    def peek(self, queue: str, limit: int = 10) -> list[Message]:
        """View pending messages without claiming."""

    @abstractmethod
    def close(self) -> None:
        """Release resources."""
