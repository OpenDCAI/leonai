"""Three-tier runtime configuration loader with merge strategies.

Configuration priority (highest to lowest):
1. CLI overrides
2. Project config (.leon/runtime.json in workspace)
3. User config (~/.leon/runtime.json)
4. System defaults (config/defaults/runtime.json)

Merge strategies:
- Runtime/Memory/Tools configs: deep merge (system + user + project)
- MCP/Skills: lookup (first found wins, no merge)
- System prompt: lookup (project > user > system)

Model identity (model name, provider, API keys) is handled by ModelsLoader.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from config.schema import LeonSettings


class ConfigLoader:
    """Three-tier runtime configuration loader."""

    def __init__(self, workspace_root: str | None = None):
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else None
        self._system_defaults_dir = Path(__file__).parent / "defaults"

    def load(self, cli_overrides: dict[str, Any] | None = None) -> LeonSettings:
        """Load runtime configuration with three-tier merge."""
        system_config = self._load_system_defaults()
        user_config = self._load_user_config()
        project_config = self._load_project_config()

        # Deep merge: runtime, memory, tools
        merged_runtime = self._deep_merge(
            system_config.get("runtime", {}),
            user_config.get("runtime", {}),
            project_config.get("runtime", {}),
        )

        # Backward compat: if old-style top-level keys exist, fold them into runtime
        for cfg in (system_config, user_config, project_config):
            for key in (
                "context_limit",
                "enable_audit_log",
                "allowed_extensions",
                "block_dangerous_commands",
                "block_network_commands",
                "queue_mode",
                "temperature",
                "max_tokens",
                "model_kwargs",
            ):
                if key in cfg and key not in merged_runtime:
                    merged_runtime[key] = cfg[key]

        merged_memory = self._deep_merge(
            system_config.get("memory", {}),
            user_config.get("memory", {}),
            project_config.get("memory", {}),
        )

        merged_tools = self._deep_merge(
            system_config.get("tools", {}),
            user_config.get("tools", {}),
            project_config.get("tools", {}),
        )

        # Lookup strategy for mcp/skills (first found wins)
        merged_mcp = self._lookup_merge("mcp", project_config, user_config, system_config)
        merged_skills = self._lookup_merge("skills", project_config, user_config, system_config)

        system_prompt = (
            project_config.get("system_prompt")
            or user_config.get("system_prompt")
            or system_config.get("system_prompt")
        )

        final_config: dict[str, Any] = {
            "runtime": merged_runtime,
            "memory": merged_memory,
            "tools": merged_tools,
            "mcp": merged_mcp,
            "skills": merged_skills,
            "system_prompt": system_prompt,
        }

        if cli_overrides:
            final_config = self._deep_merge(final_config, cli_overrides)

        final_config = self._expand_env_vars(final_config)
        final_config = self._remove_none_values(final_config)

        return LeonSettings(**final_config)

    def _load_system_defaults(self) -> dict[str, Any]:
        """Load system defaults from runtime.json."""
        path = self._system_defaults_dir / "runtime.json"
        return self._load_json(path)

    def _load_user_config(self) -> dict[str, Any]:
        """Load user config from ~/.leon/runtime.json."""
        return self._load_json(Path.home() / ".leon" / "runtime.json")

    def _load_project_config(self) -> dict[str, Any]:
        """Load project config from .leon/runtime.json."""
        if not self.workspace_root:
            return {}
        return self._load_json(self.workspace_root / ".leon" / "runtime.json")

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _deep_merge(self, *dicts: dict[str, Any]) -> dict[str, Any]:
        """Deep merge multiple dictionaries. Later dicts override earlier ones."""
        result: dict[str, Any] = {}
        for d in dicts:
            for key, value in d.items():
                if key not in result:
                    result[key] = value
                elif value is None:
                    continue
                elif isinstance(value, dict) and isinstance(result[key], dict):
                    result[key] = self._deep_merge(result[key], value)
                else:
                    result[key] = value
        return result

    def _lookup_merge(self, key: str, *configs: dict[str, Any]) -> Any:
        """Lookup strategy: first found wins."""
        for config in configs:
            if key in config and config[key] is not None:
                return config[key]
        return {}

    def _expand_env_vars(self, obj: Any) -> Any:
        """Recursively expand ${VAR} and ~ in string values."""
        if isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._expand_env_vars(v) for v in obj]
        if isinstance(obj, str):
            return os.path.expandvars(os.path.expanduser(obj))
        return obj

    def _remove_none_values(self, obj: Any) -> Any:
        """Recursively remove None values to allow Pydantic defaults."""
        if isinstance(obj, dict):
            return {k: self._remove_none_values(v) for k, v in obj.items() if v is not None}
        if isinstance(obj, list):
            return [self._remove_none_values(v) for v in obj if v is not None]
        return obj


def load_config(
    workspace_root: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> LeonSettings:
    """Convenience function to load runtime configuration."""
    return ConfigLoader(workspace_root=workspace_root).load(cli_overrides=cli_overrides)
