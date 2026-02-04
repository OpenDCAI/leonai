"""Agent Profile - 配置数据结构与加载"""
import os
from pathlib import Path
from typing import Any

try:
    from pydantic import BaseModel, Field, field_validator
except ImportError:
    raise ImportError("需要安装 pydantic: pip install pydantic")


class AgentConfig(BaseModel):
    model: str = "claude-sonnet-4-5-20250929"
    workspace_root: str | None = None
    read_only: bool = False
    enable_audit_log: bool = True
    allowed_extensions: list[str] | None = None
    block_dangerous_commands: bool = True
    block_network_commands: bool = False


class ReadFileConfig(BaseModel):
    enabled: bool = True
    max_file_size: int = 10 * 1024 * 1024


class FileSystemToolsConfig(BaseModel):
    read_file: ReadFileConfig = Field(default_factory=ReadFileConfig)
    write_file: bool = True
    edit_file: bool = True
    multi_edit: bool = True
    list_dir: bool = True


class FileSystemConfig(BaseModel):
    enabled: bool = True
    tools: FileSystemToolsConfig = Field(default_factory=FileSystemToolsConfig)


class GrepSearchConfig(BaseModel):
    enabled: bool = True
    max_file_size: int = 10 * 1024 * 1024


class SearchToolsConfig(BaseModel):
    grep_search: GrepSearchConfig = Field(default_factory=GrepSearchConfig)
    find_by_name: bool = True


class SearchConfig(BaseModel):
    enabled: bool = True
    max_results: int = 50
    tools: SearchToolsConfig = Field(default_factory=SearchToolsConfig)


class WebSearchConfig(BaseModel):
    enabled: bool = True
    max_results: int = 5
    tavily_api_key: str | None = None
    exa_api_key: str | None = None
    firecrawl_api_key: str | None = None


class ReadUrlContentConfig(BaseModel):
    enabled: bool = True
    jina_api_key: str | None = None


class WebToolsConfig(BaseModel):
    web_search: WebSearchConfig = Field(default_factory=WebSearchConfig)
    read_url_content: ReadUrlContentConfig = Field(default_factory=ReadUrlContentConfig)
    view_web_content: bool = True


class WebConfig(BaseModel):
    enabled: bool = True
    timeout: int = 15
    tools: WebToolsConfig = Field(default_factory=WebToolsConfig)


class RunCommandConfig(BaseModel):
    enabled: bool = True
    default_timeout: int = 120


class CommandToolsConfig(BaseModel):
    run_command: RunCommandConfig = Field(default_factory=RunCommandConfig)
    command_status: bool = True


class CommandConfig(BaseModel):
    enabled: bool = True
    tools: CommandToolsConfig = Field(default_factory=CommandToolsConfig)


class ToolConfig(BaseModel):
    filesystem: FileSystemConfig = Field(default_factory=FileSystemConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    command: CommandConfig = Field(default_factory=CommandConfig)


class MCPServerConfig(BaseModel):
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    allowed_tools: list[str] | None = None


class MCPConfig(BaseModel):
    enabled: bool = True
    servers: dict[str, MCPServerConfig] = Field(default_factory=dict)


class SkillsConfig(BaseModel):
    enabled: bool = True
    paths: list[str] = Field(default_factory=list)
    skills: dict[str, bool] = Field(default_factory=dict)  # skill_name: enabled


# ==================== Sandbox Configuration ====================


class SandboxProviderConfig(BaseModel):
    """Configuration for a specific sandbox provider."""
    api_key: str | None = None
    region_id: str = "ap-southeast-1"
    context_path: str = "/workspace"


class SandboxToolsConfig(BaseModel):
    """Which sandbox tools to enable."""
    read_file: bool = True
    write_file: bool = True
    edit_file: bool = True
    list_dir: bool = True
    run_command: bool = True
    sandbox_upload: bool = True
    sandbox_download: bool = True


class SandboxConfig(BaseModel):
    """
    Sandbox configuration for isolated execution environments.

    Lifecycle:
    - create: 'lazy' (first tool call) or 'eager' (thread start)
    - on_thread_switch: 'pause' or 'keep_running'
    - on_exit: 'pause' or 'destroy'
    """
    enabled: bool = False  # Disabled by default
    provider: str = "agentbay"  # 'agentbay', 'e2b', 'docker'
    context_id: str | None = None  # Persistent context for data
    replace_local_tools: bool = True  # When True, disable local filesystem/command tools

    # Provider-specific configs
    agentbay: SandboxProviderConfig = Field(default_factory=SandboxProviderConfig)

    # Lifecycle settings
    create: str = "lazy"  # 'lazy' or 'eager'
    on_thread_switch: str = "pause"  # 'pause' or 'keep_running'
    on_exit: str = "pause"  # 'pause' or 'destroy'

    # Tool configuration
    tools: SandboxToolsConfig = Field(default_factory=SandboxToolsConfig)


class AgentProfile(BaseModel):
    agent: AgentConfig = Field(default_factory=AgentConfig)
    system_prompt: str | None = None
    tool: ToolConfig = Field(default_factory=ToolConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)


    @classmethod
    def from_file(cls, path: str | Path) -> "AgentProfile":
        """从 YAML/JSON/TOML 加载"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Profile 文件不存在: {path}")

        content = path.read_text()

        if path.suffix in [".yaml", ".yml"]:
            import yaml
            data = yaml.safe_load(content)
        elif path.suffix == ".json":
            import json
            data = json.loads(content)
        elif path.suffix == ".toml":
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib
            data = tomllib.loads(content)
        else:
            raise ValueError(f"不支持的文件格式: {path.suffix}")

        # 环境变量展开
        data = cls._expand_env_vars(data)
        return cls(**data)

    @classmethod
    def from_dict(cls, data: dict) -> "AgentProfile":
        """从字典加载"""
        data = cls._expand_env_vars(data)
        return cls(**data)

    @classmethod
    def default(cls) -> "AgentProfile":
        """默认配置"""
        return cls()

    @staticmethod
    def _expand_env_vars(obj: Any) -> Any:
        """递归展开环境变量 ${VAR}"""
        if isinstance(obj, dict):
            return {k: AgentProfile._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [AgentProfile._expand_env_vars(v) for v in obj]
        elif isinstance(obj, str):
            return os.path.expandvars(obj)
        return obj
