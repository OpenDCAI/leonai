# Backward compat - deprecated, use core.runtime.middleware.queue instead
"""Queue middleware for message routing during agent execution."""

from core.runtime.middleware.queue import (  # noqa: F401
    MessageQueueManager,
    QueueItem,
    SteeringMiddleware,
    format_steer_reminder,
    format_task_notification,
)

__all__ = [
    "MessageQueueManager",
    "QueueItem",
    "SteeringMiddleware",
    "format_steer_reminder",
    "format_task_notification",
]
