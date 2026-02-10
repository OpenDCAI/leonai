"""Message Queue Manager - global singleton for queue mode coordination"""

import threading
from collections import deque

from .types import QueueMessage, QueueMode


class MessageQueueManager:
    """Thread-safe message queue manager for TUI and SteeringMiddleware coordination"""

    def __init__(self):
        self._lock = threading.Lock()
        self._steer_queue: deque[QueueMessage] = deque()
        self._followup_queue: deque[QueueMessage] = deque()
        self._collect_buffer: list[QueueMessage] = []
        self._current_mode: QueueMode = QueueMode.STEER

    def set_mode(self, mode: QueueMode) -> None:
        """Set the current queue mode"""
        with self._lock:
            self._current_mode = mode

    def get_mode(self) -> QueueMode:
        """Get the current queue mode"""
        with self._lock:
            return self._current_mode

    def enqueue(self, content: str, mode: QueueMode | None = None) -> None:
        """Enqueue a message with the specified mode (defaults to current mode)"""
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
                self._steer_queue.append(msg)
                self._followup_queue.append(msg)

    def get_steer(self) -> str | None:
        """Get and remove the next steer message"""
        with self._lock:
            return self._steer_queue.popleft().content if self._steer_queue else None

    def get_followup(self) -> str | None:
        """Get and remove the next followup message"""
        with self._lock:
            return self._followup_queue.popleft().content if self._followup_queue else None

    def flush_collect(self) -> str | None:
        """Flush collect buffer and return merged content"""
        with self._lock:
            if not self._collect_buffer:
                return None
            contents = [msg.content for msg in self._collect_buffer]
            self._collect_buffer.clear()
            return "\n\n".join(contents)

    def has_steer(self) -> bool:
        """Check if there are pending steer messages"""
        with self._lock:
            return bool(self._steer_queue)

    def has_followup(self) -> bool:
        """Check if there are pending followup messages"""
        with self._lock:
            return bool(self._followup_queue)

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


_queue_manager: MessageQueueManager | None = None
_manager_lock = threading.Lock()


def get_queue_manager() -> MessageQueueManager:
    """Get the global MessageQueueManager singleton"""
    global _queue_manager
    if _queue_manager is None:
        with _manager_lock:
            if _queue_manager is None:
                _queue_manager = MessageQueueManager()
    return _queue_manager


def reset_queue_manager() -> None:
    """Reset the global manager (for testing)"""
    global _queue_manager
    with _manager_lock:
        _queue_manager = None
