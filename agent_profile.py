"""Agent Profile - 配置数据结构与加载"""
import os
from pathlib import Path
from typing import Any

try:
    from pydantic import BaseModel, Field, field_validator
except ImportError:
    raise ImportError("需要安装 pydantic: pip install pydantic")


class FileSystemConfig(BaseModel):
    enabled: bool = True
    read_only: bool = False
    allowed_extensions: list[str] | None = None
    read_file: bool = True
    write_file: bool = True
    edit_file: bool = True
    multi_edit: bool = True
    list_dir: bool = True


class SearchConfig(BaseModel):
    enabled: bool = True
    grep_search: bool = True
    find_by_name: bool = True


class WebConfig(BaseModel):
    enabled: bool = True
    web_search: bool = True
    read_url_content: bool = True
    view_web_content: bool = True


class CommandConfig(BaseModel):
    enabled: bool = True
    block_dangerous_commands: bool = True
    block_network_commands: bool = False
    run_command: bool = True
    command_status: bool = True


class AgentConfig(BaseModel):
    model: str = "claude-sonnet-4-5-20250929"
    workspace_root: str | None = None
    read_only: bool = False
    enable_audit_log: bool = True


class ToolsConfig(BaseModel):
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


class AgentProfile(BaseModel):
    agent: AgentConfig = Field(default_factory=AgentConfig)
    system_prompt: str | None = None
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)


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
