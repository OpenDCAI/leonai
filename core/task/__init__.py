"""Task middleware - Agent definitions and loader (legacy, kept for config loading)."""

from .loader import AgentLoader
from .types import AgentBundle, AgentConfig, TaskParams, TaskResult

__all__ = [
    "AgentLoader",
    "AgentBundle",
    "AgentConfig",
    "TaskParams",
    "TaskResult",
]
