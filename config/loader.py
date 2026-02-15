"""Three-tier configuration loader with merge strategies.

Configuration priority (highest to lowest):
1. Project config (.leon/config.json in workspace)
2. User config (~/.leon/config.json)
3. System defaults (leon/config/defaults/)

Merge strategies:
- Agent configs: deep merge (system + user + project)
- Sandbox/MCP/Skills: lookup (first found wins, no merge)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from config.schema import LeonSettings


class ConfigLoader:
    """Three-tier configuration loader."""

    def __init__(self, workspace_root: str | None = None):
        """Initialize loader.

        Args:
            workspace_root: Project workspace root (for .leon/config.json)
        """
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else None
        self._system_defaults_dir = Path(__file__).parent / "defaults"

    def load(self, cli_overrides: dict[str, Any] | None = None) -> LeonSettings:
        """Load configuration with three-tier merge.

        Args:
            cli_overrides: CLI overrides (highest priority)

        Returns:
            Merged LeonSettings instance
        """
        # Load three tiers
        system_config = self._load_system_defaults()
        user_config = self._load_user_config()
        project_config = self._load_project_config()

        # Merge agent configs (deep merge)
        merged_api = self._deep_merge(
            system_config.get("api", {}),
            user_config.get("api", {}),
            project_config.get("api", {}),
        )

        # Merge memory configs (deep merge)
        merged_memory = self._deep_merge(
            system_config.get("memory", {}),
            user_config.get("memory", {}),
            project_config.get("memory", {}),
        )

        # Merge tool configs (deep merge)
        merged_tools = self._deep_merge(
            system_config.get("tools", {}),
            user_config.get("tools", {}),
            project_config.get("tools", {}),
        )

        # Lookup strategy for sandbox/mcp/skills (first found wins)
        merged_mcp = self._lookup_merge("mcp", project_config, user_config, system_config)
        merged_skills = self._lookup_merge("skills", project_config, user_config, system_config)

        # Merge system_prompt (project > user > system)
        system_prompt = (
            project_config.get("system_prompt")
            or user_config.get("system_prompt")
            or system_config.get("system_prompt")
        )

        # Build final config
        final_config = {
            "api": merged_api,
            "memory": merged_memory,
            "tools": merged_tools,
            "mcp": merged_mcp,
            "skills": merged_skills,
            "system_prompt": system_prompt,
        }

        # Apply CLI overrides
        if cli_overrides:
            final_config = self._deep_merge(final_config, cli_overrides)

        # Expand environment variables
        final_config = self._expand_env_vars(final_config)

        # Convert to LeonSettings (validates schema)
        return LeonSettings(**final_config)

    def _load_system_defaults(self) -> dict[str, Any]:
        """Load system default configuration."""
        default_agent_path = self._system_defaults_dir / "agents" / "default.json"
        if not default_agent_path.exists():
            return {}

        with open(default_agent_path) as f:
            return json.load(f)

    def _load_user_config(self) -> dict[str, Any]:
        """Load user configuration from ~/.leon/config.json."""
        user_config_path = Path.home() / ".leon" / "config.json"
        if not user_config_path.exists():
            return {}

        with open(user_config_path) as f:
            return json.load(f)

    def _load_project_config(self) -> dict[str, Any]:
        """Load project configuration from .leon/config.json."""
        if not self.workspace_root:
            return {}

        project_config_path = self.workspace_root / ".leon" / "config.json"
        if not project_config_path.exists():
            return {}

        with open(project_config_path) as f:
            return json.load(f)

    def _deep_merge(self, *dicts: dict[str, Any]) -> dict[str, Any]:
        """Deep merge multiple dictionaries.

        Later dicts override earlier ones. None values are preserved (don't override).

        Args:
            *dicts: Dictionaries to merge

        Returns:
            Merged dictionary
        """
        result: dict[str, Any] = {}

        for d in dicts:
            for key, value in d.items():
                if key not in result:
                    result[key] = value
                elif value is None:
                    # Preserve None values (don't override)
                    continue
                elif isinstance(value, dict) and isinstance(result[key], dict):
                    # Recursively merge nested dicts
                    result[key] = self._deep_merge(result[key], value)
                else:
                    # Override with new value
                    result[key] = value

        return result

    def _lookup_merge(self, key: str, *configs: dict[str, Any]) -> Any:
        """Lookup strategy: first found wins.

        Args:
            key: Config key to lookup
            *configs: Configs in priority order (highest first)

        Returns:
            First non-None value found
        """
        for config in configs:
            if key in config and config[key] is not None:
                return config[key]
        return {}

    def _expand_env_vars(self, obj: Any) -> Any:
        """Recursively expand environment variables ${VAR}.

        Args:
            obj: Object to expand (dict/list/str)

        Returns:
            Expanded object
        """
        if isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_env_vars(v) for v in obj]
        elif isinstance(obj, str):
            # Expand ~ and environment variables
            expanded = os.path.expanduser(obj)
            expanded = os.path.expandvars(expanded)
            return expanded
        return obj


def load_config(
    workspace_root: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> LeonSettings:
    """Convenience function to load configuration.

    Args:
        workspace_root: Project workspace root
        cli_overrides: CLI overrides

    Returns:
        Loaded LeonSettings instance
    """
    loader = ConfigLoader(workspace_root=workspace_root)
    return loader.load(cli_overrides=cli_overrides)
