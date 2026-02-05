"""Queue Mode types for message injection during agent execution"""

from dataclasses import dataclass, field
from enum import Enum
import time


class QueueMode(Enum):
    """Message queue modes following OpenClaw semantics"""

    STEER = "steer"
    """Inject message into current run, skip remaining tool calls"""

    FOLLOWUP = "followup"
    """Queue message to process after current run completes"""

    COLLECT = "collect"
    """Collect multiple messages, merge and process as single followup"""

    STEER_BACKLOG = "steer_backlog"
    """Steer current run AND queue as followup"""

    INTERRUPT = "interrupt"
    """Cancel current run immediately"""


@dataclass
class QueueMessage:
    """A queued user message"""

    content: str
    mode: QueueMode
    timestamp: float = field(default_factory=time.time)
