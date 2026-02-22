"""Observation provider configuration schema.

Per-provider named fields, following sandbox/config.py pattern.
"""

from pydantic import BaseModel, Field


class LangfuseConfig(BaseModel):
    """Langfuse provider config (dual key + host)."""

    secret_key: str | None = None
    public_key: str | None = None
    host: str | None = Field(None, description="e.g. https://cloud.langfuse.com")


class LangSmithConfig(BaseModel):
    """LangSmith provider config (api_key + project)."""

    api_key: str | None = None
    project: str | None = None
    endpoint: str | None = None


class ObservationConfig(BaseModel):
    """Observation configuration with per-provider named fields."""

    active: str | None = Field(None, description="'langfuse' | 'langsmith' | None (disabled)")
    langfuse: LangfuseConfig = Field(default_factory=LangfuseConfig)
    langsmith: LangSmithConfig = Field(default_factory=LangSmithConfig)
