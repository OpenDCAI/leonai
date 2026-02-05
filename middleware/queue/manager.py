"""Message Queue Manager - global singleton for queue mode coordination"""

import threading
from collections import deque
from typing import Optional

from .types import QueueMessage, QueueMode


class MessageQueueManager:
    """
    Manages message queues for different queue modes.

    Thread-safe singleton that coordinates between TUI (producer) and
    SteeringMiddleware (consumer).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._steer_queue: deque[QueueMessage] = deque()
        self._followup_queue: deque[QueueMessage] = deque()
        self._collect_buffer: list[QueueMessage] = []
        self._current_mode: QueueMode = QueueMode.FOLLOWUP

    def set_mode(self, mode: QueueMode) -> None:
        """Set the current queue mode"""
        with self._lock:
            self._current_mode = mode

    def get_mode(self) -> QueueMode:
        """Get the current queue mode"""
        with self._lock:
            return self._current_mode

    def enqueue(self, content: str, mode: Optional[QueueMode] = None) -> None:
        """
        Enqueue a message with the specified mode.

        Args:
            content: Message content
            mode: Queue mode (defaults to current mode)
        """
        if mode is None:
            mode = self._current_mode

        msg = QueueMessage(content=content, mode=mode)

        with self._lock:
            if mode == QueueMode.STEER:
                self._steer_queue.append(msg)
            elif mode == QueueMode.FOLLOWUP:
                self._followup_queue.append(msg)
            elif mode == QueueMode.COLLECT:
                self._collect_buffer.append(msg)
            elif mode == QueueMode.STEER_BACKLOG:
                # Both steer and followup
                self._steer_queue.append(msg)
                self._followup_queue.append(msg)
            # INTERRUPT is handled directly by TUI, not queued

    def get_steer(self) -> Optional[str]:
        """
        Get and remove the next steer message.

        Called by SteeringMiddleware in before_model hook.
        Returns None if no steer message is queued.
        """
        with self._lock:
            if self._steer_queue:
                msg = self._steer_queue.popleft()
                return msg.content
            return None

    def get_followup(self) -> Optional[str]:
        """
        Get and remove the next followup message.

        Called by TUI after agent run completes.
        """
        with self._lock:
            if self._followup_queue:
                msg = self._followup_queue.popleft()
                return msg.content
            return None

    def flush_collect(self) -> Optional[str]:
        """
        Flush collect buffer and return merged content.

        Called when switching out of collect mode or on timeout.
        """
        with self._lock:
            if not self._collect_buffer:
                return None

            # Merge all collected messages
            contents = [msg.content for msg in self._collect_buffer]
            self._collect_buffer.clear()
            return "\n\n".join(contents)

    def has_steer(self) -> bool:
        """Check if there are pending steer messages"""
        with self._lock:
            return len(self._steer_queue) > 0

    def has_followup(self) -> bool:
        """Check if there are pending followup messages"""
        with self._lock:
            return len(self._followup_queue) > 0

    def clear_all(self) -> None:
        """Clear all queues"""
        with self._lock:
            self._steer_queue.clear()
            self._followup_queue.clear()
            self._collect_buffer.clear()

    def queue_sizes(self) -> dict[str, int]:
        """Get current queue sizes for debugging"""
        with self._lock:
            return {
                "steer": len(self._steer_queue),
                "followup": len(self._followup_queue),
                "collect": len(self._collect_buffer),
            }


# Global singleton
_queue_manager: Optional[MessageQueueManager] = None
_manager_lock = threading.Lock()


def get_queue_manager() -> MessageQueueManager:
    """Get the global MessageQueueManager singleton"""
    global _queue_manager
    with _manager_lock:
        if _queue_manager is None:
            _queue_manager = MessageQueueManager()
        return _queue_manager


def reset_queue_manager() -> None:
    """Reset the global manager (for testing)"""
    global _queue_manager
    with _manager_lock:
        _queue_manager = None
