"""Type definitions for Task middleware."""

from typing import NotRequired, TypedDict

from pydantic import BaseModel


class AgentConfig(BaseModel):
    """Agent configuration parsed from .md file."""

    name: str
    description: str
    tools: list[str]
    system_prompt: str
    max_turns: int = 50
    model: str | None = None


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
    status: str  # completed/running/error
    result: str | None = None
    error: str | None = None
    turns_used: int = 0
