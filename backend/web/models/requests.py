"""Pydantic request models for Leon web API."""

from pydantic import BaseModel


class CreateThreadRequest(BaseModel):
    sandbox: str = "local"
    cwd: str | None = None
    model: str | None = None


class RunRequest(BaseModel):
    message: str
    enable_trajectory: bool = False
    model: str | None = None


class SteerRequest(BaseModel):
    message: str


class QueueModeRequest(BaseModel):
    mode: str


class TaskAgentRequest(BaseModel):
    subagent_type: str
    prompt: str
    description: str | None = None
    model: str | None = None
    max_turns: int | None = None
