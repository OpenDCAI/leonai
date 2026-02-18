"""Message Queue Manager - per-thread queue isolation for queue mode coordination"""

import threading
from collections import deque
from dataclasses import dataclass, field

from .types import QueueMessage, QueueMode

DEFAULT_THREAD = "__global__"


@dataclass
class _ThreadQueue:
    steer: deque[QueueMessage] = field(default_factory=deque)
    followup: deque[QueueMessage] = field(default_factory=deque)
    collect: list[QueueMessage] = field(default_factory=list)
    mode: QueueMode = QueueMode.STEER


class MessageQueueManager:
    """Thread-safe message queue manager with per-thread isolation"""

    def __init__(self):
        self._lock = threading.Lock()
        self._threads: dict[str, _ThreadQueue] = {}

    def _get_thread(self, thread_id: str | None = None) -> _ThreadQueue:
        tid = thread_id or DEFAULT_THREAD
        if tid not in self._threads:
            self._threads[tid] = _ThreadQueue()
        return self._threads[tid]

    def set_mode(self, mode: QueueMode, thread_id: str | None = None) -> None:
        with self._lock:
            self._get_thread(thread_id).mode = mode

    def get_mode(self, thread_id: str | None = None) -> QueueMode:
        with self._lock:
            return self._get_thread(thread_id).mode

    def enqueue(self, content: str, mode: QueueMode | None = None, thread_id: str | None = None) -> None:
        msg_mode = mode if mode is not None else self.get_mode(thread_id)
        msg = QueueMessage(content=content, mode=msg_mode)

        with self._lock:
            tq = self._get_thread(thread_id)
            if msg_mode == QueueMode.STEER:
                tq.steer.append(msg)
            elif msg_mode == QueueMode.FOLLOWUP:
                tq.followup.append(msg)
            elif msg_mode == QueueMode.COLLECT:
                tq.collect.append(msg)
            elif msg_mode == QueueMode.STEER_BACKLOG:
                tq.steer.append(msg)
                tq.followup.append(msg)

    def get_steer(self, thread_id: str | None = None) -> str | None:
        with self._lock:
            tq = self._get_thread(thread_id)
            return tq.steer.popleft().content if tq.steer else None

    def get_followup(self, thread_id: str | None = None) -> str | None:
        with self._lock:
            tq = self._get_thread(thread_id)
            return tq.followup.popleft().content if tq.followup else None

    def flush_collect(self, thread_id: str | None = None) -> str | None:
        with self._lock:
            tq = self._get_thread(thread_id)
            if not tq.collect:
                return None
            contents = [msg.content for msg in tq.collect]
            tq.collect.clear()
            return "\n\n".join(contents)

    def has_steer(self, thread_id: str | None = None) -> bool:
        with self._lock:
            return bool(self._get_thread(thread_id).steer)

    def has_followup(self, thread_id: str | None = None) -> bool:
        with self._lock:
            return bool(self._get_thread(thread_id).followup)

    def clear_all(self, thread_id: str | None = None) -> None:
        with self._lock:
            tq = self._get_thread(thread_id)
            tq.steer.clear()
            tq.followup.clear()
            tq.collect.clear()

    def clear_thread(self, thread_id: str) -> None:
        """Remove all state for a thread."""
        with self._lock:
            self._threads.pop(thread_id, None)

    def queue_sizes(self, thread_id: str | None = None) -> dict[str, int]:
        with self._lock:
            tq = self._get_thread(thread_id)
            return {
                "steer": len(tq.steer),
                "followup": len(tq.followup),
                "collect": len(tq.collect),
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
