"""Queue Mode types for message injection during agent execution"""

import time
from dataclasses import dataclass, field
from enum import Enum


class QueueMode(Enum):
    """Message queue modes following OpenClaw semantics"""

    STEER = "steer"
    FOLLOWUP = "followup"
    COLLECT = "collect"
    STEER_BACKLOG = "steer_backlog"
    INTERRUPT = "interrupt"


@dataclass
class QueueMessage:
    """A queued user message"""

    content: str
    mode: QueueMode
    timestamp: float = field(default_factory=time.time)
