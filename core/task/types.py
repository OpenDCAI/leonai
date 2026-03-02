"""Type definitions for Task middleware.

Agent/bundle types are defined in config.types and re-exported here
for backward compatibility.
"""

from typing import Literal, NotRequired, TypedDict

from pydantic import BaseModel

# Re-export from config.types (canonical location)
from config.types import (
    AgentBundle,
    AgentConfig,
    McpServerConfig,
    RuntimeResourceConfig,
)


class TaskParams(TypedDict):
    """Parameters for task tool call."""

    SubagentType: str
    Prompt: str
    Description: NotRequired[str]
    Model: NotRequired[str]
    RunInBackground: NotRequired[bool]
    Resume: NotRequired[str]
    MaxTurns: NotRequired[int]


class TaskResult(BaseModel):
    """Result from task execution."""

    task_id: str
    thread_id: str | None = None
    status: Literal["completed", "running", "error", "timeout"]
    result: str | None = None
    error: str | None = None
    description: str | None = None
    turns_used: int = 0
