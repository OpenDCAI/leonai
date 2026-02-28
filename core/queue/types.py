"""Queue types — deprecated module.

QueueMode and QueueMessage are deprecated. Message routing is now determined
by send timing (inject for steer, enqueue/dequeue for followup), not by
session-level mode declarations.
"""

import warnings


def __getattr__(name: str):
    if name == "QueueMode":
        warnings.warn(
            "QueueMode is deprecated and will be removed. "
            "Use MessageQueueManager.inject() for steer and .enqueue() for followup.",
            DeprecationWarning,
            stacklevel=2,
        )
        from enum import Enum

        class QueueMode(Enum):
            STEER = "steer"
            FOLLOWUP = "followup"
            COLLECT = "collect"
            STEER_BACKLOG = "steer_backlog"
            INTERRUPT = "interrupt"

        return QueueMode

    if name == "QueueMessage":
        warnings.warn(
            "QueueMessage is deprecated and will be removed.",
            DeprecationWarning,
            stacklevel=2,
        )
        import time
        from dataclasses import dataclass, field

        @dataclass
        class QueueMessage:
            content: str
            mode: object
            timestamp: float = field(default_factory=time.time)

        return QueueMessage

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
