"""Agent Profile - 配置数据结构与加载"""
import os
from pathlib import Path
from typing import Any

try:
    from pydantic import BaseModel, Field, field_validator
except ImportError:
    raise ImportError("需要安装 pydantic: pip install pydantic")


class ToolConfig(BaseModel):
    enabled: bool = True


class FileSystemConfig(ToolConfig):
    read_only: bool = False
    allowed_extensions: list[str] | None = None


class CommandConfig(ToolConfig):
    block_dangerous_commands: bool = True
    block_network_commands: bool = False


class AgentConfig(BaseModel):
    model: str = "claude-sonnet-4-5-20250929"
    workspace_root: str | None = None
    read_only: bool = False
    enable_audit_log: bool = True


class ToolsConfig(BaseModel):
    filesystem: FileSystemConfig = Field(default_factory=FileSystemConfig)
    search: ToolConfig = Field(default_factory=ToolConfig)
    web: ToolConfig = Field(default_factory=ToolConfig)
    command: CommandConfig = Field(default_factory=CommandConfig)


class AgentProfile(BaseModel):
    agent: AgentConfig = Field(default_factory=AgentConfig)
    system_prompt: str | None = None
    tools: ToolsConfig = Field(default_factory=ToolsConfig)

    @field_validator("agent", mode="after")
    @classmethod
    def validate_agent(cls, v: AgentConfig) -> AgentConfig:
        if v.workspace_root:
            ws_str = v.workspace_root
            if not ("$" in ws_str or "{" in ws_str):
                ws = Path(ws_str).expanduser()
                if not ws.exists():
                    raise ValueError(f"workspace_root 不存在: {ws}")
        return v

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
