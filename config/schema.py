"""Core configuration schema for Leon using Pydantic.

This module defines the complete configuration structure with:
- Nested config groups (API, Memory, Tools, MCP, Skills)
- Virtual model mapping (leon:mini/medium/large/max)
- Field validators for API keys, paths, extensions
- Environment variable loading with nested delimiter
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# Default model used across the codebase — single source of truth
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

# ============================================================================
# API Configuration
# ============================================================================


class ModelSpec(BaseModel):
    """Virtual model specification for leon:* model names."""

    model: str = Field(..., description="Actual model name to use")
    provider: str | None = Field(None, description="Model provider (openai/anthropic/etc)")
    temperature: float | None = Field(None, ge=0.0, le=2.0, description="Temperature override")
    max_tokens: int | None = Field(None, gt=0, description="Max tokens override")


class APIConfig(BaseModel):
    """API configuration for LLM providers."""

    model: str = Field(DEFAULT_MODEL, description="Default model name")
    model_provider: str | None = Field(None, description="Explicit provider (openai/anthropic/etc)")
    api_key: str | None = Field(None, description="API key (falls back to env vars)")
    base_url: str | None = Field(None, description="Base URL for API (falls back to env vars)")
    temperature: float | None = Field(None, ge=0.0, le=2.0, description="Temperature")
    max_tokens: int | None = Field(None, gt=0, description="Max tokens")
    model_kwargs: dict[str, Any] = Field(default_factory=dict, description="Extra kwargs for init_chat_model")
    context_limit: int = Field(100000, gt=0, description="Context window limit in tokens")
    enable_audit_log: bool = Field(True, description="Enable audit logging")
    allowed_extensions: list[str] | None = Field(None, description="Alle extensions (None = all)")
    block_dangerous_commands: bool = Field(True, description="Block dangerous commands")
    block_network_commands: bool = Field(False, description="Block network commands")
    queue_mode: str = Field("steer", description="Queue mode: steer/followup/collect/steer_backlog/interrupt")

    @field_validator("base_url")
    @classmethod
    def normalize_base_url(cls, v: str | None) -> str | None:
        """Ensure base_url ends with /v1 for OpenAI-compatible APIs."""
        if not v:
            return v
        v = v.rstrip("/")
        if v.endswith("/v1") or "/v1/" in v:
            return v
        return f"{v}/v1"


# ============================================================================
# Memory Configuration
# ============================================================================


class PruningConfig(BaseModel):
    """Configuration for message pruning.

    Field names match SessionPruner constructor for direct passthrough.
    """

    enabled: bool = Field(True, description="Enable message pruning")
    soft_trim_chars: int = Field(3000, gt=0, description="Soft-trim tool results longer than this")
    hard_clear_threshold: int = Field(10000, gt=0, description="Hard-clear tool results longer than this")
    protect_recent: int = Field(3, gt=0, description="Keep last N tool messages untrimmed")
    trim_tool_results: bool = Field(True, description="Trim large tool results")


class CompactionConfig(BaseModel):
    """Configuration for context compaction.

    Field names match ContextCompactor constructor for direct passthrough.
    """

    enabled: bool = Field(True, description="Enable context compaction")
    reserve_tokens: int = Field(16384, gt=0, description="Reserve space for new messages")
    keep_recent_tokens: int = Field(20000, gt=0, description="Keep recent messages verbatim")
    min_messages: int = Field(20, gt=0, description="Minimum messages before compaction")


class MemoryConfig(BaseModel):
    """Memory management configuration."""

    pruning: PruningConfig = Field(default_factory=PruningConfig)
    compaction: CompactionConfig = Field(default_factory=CompactionConfig)


# ============================================================================
# Tools Configuration
# ============================================================================


class ReadFileConfig(BaseModel):
    """Configuration for read_file tool."""

    enabled: bool = True
    max_file_size: int = Field(10485760, gt=0, description="Max file size in bytes (10MB)")


class FileSystemToolsConfig(BaseModel):
    """Configuration for filesystem tools."""

    read_file: ReadFileConfig = Field(default_factory=ReadFileConfig)
    write_file: bool = True
    edit_file: bool = True
    multi_edit: bool = True
    list_dir: bool = True


class FileSystemConfig(BaseModel):
    """Configuration for filesystem middleware."""

    enabled: bool = True
    tools: FileSystemToolsConfig = Field(default_factory=FileSystemToolsConfig)


class GrepSearchConfig(BaseModel):
    """Configuration for grep_search tool."""

    enabled: bool = True
    max_file_size: int = Field(10485760, gt=0, description="Max file size in bytes (10MB)")


class SearchToolsConfig(BaseModel):
    """Configuration for search tools."""

    grep_search: GrepSearchConfig = Field(default_factory=GrepSearchConfig)
    find_by_name: bool = True


class SearchConfig(BaseModel):
    """Configuration for search middleware."""

    enabled: bool = True
    max_results: int = Field(50, gt=0, description="Max search results")
    tools: SearchToolsConfig = Field(default_factory=SearchToolsConfig)


class WebSearchConfig(BaseModel):
    """Configuration for web_search tool."""

    enabled: bool = True
    max_results: int = Field(5, gt=0, description="Max search results")
    tavily_api_key: str | None = Field(None, description="Tavily API key")
    exa_api_key: str | None = Field(None, description="Exa API key")
    firecrawl_api_key: str | None = Field(None, description="Firecrawl API key")


class ReadUrlConfig(BaseModel):
    """Configuration for read_url_content tool."""

    enabled: bool = True
    jina_api_key: str | None = Field(None, description="Jina AI API key")


class WebToolsConfig(BaseModel):
    """Configuration for web tools."""

    web_search: WebSearchConfig = Field(default_factory=WebSearchConfig)
    read_url_content: ReadUrlConfig = Field(default_factory=ReadUrlConfig)
    view_web_content: bool = True


class WebConfig(BaseModel):
    """Configuration for web middleware."""

    enabled: bool = True
    timeout: int = Field(15, gt=0, description="Request timeout in seconds")
    tools: WebToolsConfig = Field(default_factory=WebToolsConfig)


class RunCommandConfig(BaseModel):
    """Configuration for run_command tool."""

    enabled: bool = True
    default_timeout: int = Field(120, gt=0, description="Default timeout in seconds")


class CommandToolsConfig(BaseModel):
    """Configuration for command tools."""

    run_command: RunCommandConfig = Field(default_factory=RunCommandConfig)
    command_status: bool = True


class CommandConfig(BaseModel):
    """Configuration for command middleware."""

    enabled: bool = True
    tools: CommandToolsConfig = Field(default_factory=CommandToolsConfig)


class ToolsConfig(BaseModel):
    """Tools configuration."""

    filesystem: FileSystemConfig = Field(default_factory=FileSystemConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    command: CommandConfig = Field(default_factory=CommandConfig)


# ============================================================================
# MCP Configuration
# ============================================================================


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""

    command: str = Field(..., description="Command to run the MCP server")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")


class MCPConfig(BaseModel):
    """MCP (Model Context Protocol) configuration."""

    enabled: bool = True
    servers: dict[str, MCPServerConfig] = Field(default_factory=dict, description="MCP server configurations")


# ============================================================================
# Skills Configuration
# ============================================================================


class SkillsConfig(BaseModel):
    """Skills configuration."""

    enabled: bool = True
    paths: list[str] = Field(default_factory=lambda: ["./skills"], description="Skill search paths")
    skills: dict[str, bool] = Field(default_factory=dict, description="Skill enable/disable map")

    @field_validator("paths")
    @classmethod
    def validate_paths(cls, v: list[str]) -> list[str]:
        """Validate skill paths exist."""
        for path_str in v:
            path = Path(path_str).expanduser()
            if not path.exists():
                raise ValueError(f"Skill path does not exist: {path}")
        return v


# ============================================================================
# Main Settings
# ============================================================================


class LeonSettings(BaseModel):
    """Main Leon configuration.

    Configuration priority (highest to lowest):
    1. CLI overrides
    2. Project config (.leon/config.json)
    3. User config (~/.leon/config.json)
    4. System defaults (config/defaults/)
    5. Environment variables (for API keys)

    Note: This uses BaseModel instead of BaseSettings to avoid
    automatic environment variable loading conflicts with our
    three-tier config system.
    """

    # Core configuration groups
    api: APIConfig = Field(default_factory=APIConfig, description="API configuration")
    memory: MemoryConfig = Field(default_factory=MemoryConfig, description="Memory management")
    tools: ToolsConfig = Field(default_factory=ToolsConfig, description="Tools configuration")
    mcp: MCPConfig = Field(default_factory=MCPConfig, description="MCP configuration")
    skills: SkillsConfig = Field(default_factory=SkillsConfig, description="Skills configuration")

    # Virtual model mapping
    model_mapping: dict[str, ModelSpec] = Field(
        default_factory=lambda: {
            "leon:mini": ModelSpec(model="claude-haiku-4-5-20250929", provider="anthropic"),
            "leon:medium": ModelSpec(model=DEFAULT_MODEL, provider="anthropic"),
            "leon:large": ModelSpec(model="claude-opus-4-6", provider="anthropic"),
            "leon:max": ModelSpec(model="claude-opus-4-6", provider="anthropic", temperature=0.0),
        },
        description="Virtual model name mapping",
    )

    # Agent configuration
    system_prompt: str | None = Field(None, description="Custom system prompt")
    workspace_root: str | None = Field(None, description="Workspace root directory")

    @field_validator("workspace_root")
    @classmethod
    def validate_workspace_root(cls, v: str | None) -> str | None:
        """Validate workspace_root exists."""
        if v is None:
            return v
        path = Path(v).expanduser().resolve()
        if not path.exists():
            raise ValueError(f"Workspace root does not exist: {path}")
        if not path.is_dir():
            raise ValueError(f"Workspace root is not a directory: {path}")
        return str(path)

    @model_validator(mode="after")
    def validate_api_keys(self) -> LeonSettings:
        """Validate API key dependencies.

        If api_key is not set, check environment variables:
        - OPENAI_API_KEY
        - ANTHROPIC_API_KEY
        - OPENROUTER_API_KEY
        """
        if self.api.api_key is None:
            # Check common API key environment variables
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENROUTER_API_KEY")
            if api_key:
                self.api.api_key = api_key
            else:
                raise ValueError(
                    "No API key found. Set LEON__API__API_KEY, OPENAI_API_KEY, "
                    "ANTHROPIC_API_KEY, or OPENROUTER_API_KEY environment variable."
                )

        # Also check base_url from environment if not set
        if self.api.base_url is None:
            base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("ANTHROPIC_BASE_URL")
            if base_url:
                self.api.base_url = base_url

        return self

    def resolve_model(self, model_name: str) -> tuple[str, dict[str, Any]]:
        """Resolve virtual model name to actual model and config.

        Args:
            model_name: Model name (can be leon:* virtual name)

        Returns:
            Tuple of (actual_model_name, model_kwargs)

        Raises:
            ValueError: If virtual model name not found in mapping
        """
        if not model_name.startswith("leon:"):
            return model_name, {}

        if model_name not in self.model_mapping:
            raise ValueError(f"Unknown virtual model: {model_name}. Available: {', '.join(self.model_mapping.keys())}")

        spec = self.model_mapping[model_name]
        kwargs = {}
        if spec.provider:
            kwargs["model_provider"] = spec.provider
        if spec.temperature is not None:
            kwargs["temperature"] = spec.temperature
        if spec.max_tokens is not None:
            kwargs["max_tokens"] = spec.max_tokens

        return spec.model, kwargs
