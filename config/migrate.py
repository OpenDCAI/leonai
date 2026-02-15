"""Configuration migration tool for old profile.yaml format.

Migrates from old format:
- profile.yaml (agent/tool/mcp/skills sections)
- config.env (environment variables)
- sandboxes/*.json (sandbox configs)

To new format:
- config.json (unified configuration)
- .env (environment variables)

Example usage:
    >>> from config.migrate import migrate_config
    >>> from pathlib import Path
    >>>
    >>> # Dry run to preview changes
    >>> report = migrate_config("~/.leon", dry_run=True)
    >>> print(report['changes'])
    {'renamed_sections': ['agent → api', 'tool → tools']}
    >>>
    >>> # Actual migration
    >>> report = migrate_config("~/.leon")
    >>> print(f"Migrated to {report['new_files']['config.json']}")
    'Migrated to /Users/username/.leon/config.json'

Key changes:
- agent.* → api.* (renamed section)
- tool.* → tools.* (pluralized)
- agent.workspace_root → workspace_root (moved to root)
- agent.memory → memory (moved to root)
- Memory config fields renamed (see migration guide)
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import yaml


class ConfigMigrationError(Exception):
    """Configuration migration error."""

    pass


class ConfigMigrator:
    """Migrate old configuration format to new format."""

    def __init__(self, config_dir: Path):
        """Initialize migrator.

        Args:
            config_dir: Configuration directory (~/.leon or .leon/)
        """
        self.config_dir = Path(config_dir)
        self.backup_suffix = ".bak"

    def detect_old_config(self) -> dict[str, Path]:
        """Detect old configuration files.

        Returns:
            Dict of {file_type: path} for found old config files

        Example:
            >>> migrator = ConfigMigrator(Path("~/.leon"))
            >>> old_files = migrator.detect_old_config()
            >>> old_files
            {'profile.yaml': Path('/Users/username/.leon/profile.yaml')}
        """
        old_files = {}

        # Check for profile.yaml
        profile_yaml = self.config_dir / "profile.yaml"
        if profile_yaml.exists():
            old_files["profile.yaml"] = profile_yaml

        # Check for config.env
        config_env = self.config_dir / "config.env"
        if config_env.exists():
            old_files["config.env"] = config_env

        # Check for sandboxes/*.json
        sandboxes_dir = self.config_dir / "sandboxes"
        if sandboxes_dir.exists() and sandboxes_dir.is_dir():
            sandbox_files = list(sandboxes_dir.glob("*.json"))
            if sandbox_files:
                old_files["sandboxes"] = sandboxes_dir

        return old_files

    def migrate(self, dry_run: bool = False) -> dict[str, Any]:
        """Migrate old configuration to new format.

        Args:
            dry_run: If True, only validate without writing files

        Returns:
            Migration report with changes and validation results

        Raises:
            ConfigMigrationError: If migration fails
        """
        # Detect old files
        old_files = self.detect_old_config()
        if not old_files:
            raise ConfigMigrationError("No old configuration files found")

        report = {
            "old_files": {k: str(v) for k, v in old_files.items()},
            "new_files": {},
            "changes": {},
            "validation": {},
        }

        # Load old configuration
        old_config = {}
        if "profile.yaml" in old_files:
            with open(old_files["profile.yaml"]) as f:
                old_config = yaml.safe_load(f) or {}

        # Convert to new format
        new_config = self._convert_profile(old_config)

        # Validate new config
        validation_errors = self._validate_config(new_config)
        report["validation"]["errors"] = validation_errors
        if validation_errors:
            raise ConfigMigrationError(f"Validation failed: {validation_errors}")

        # Generate change summary
        report["changes"] = self._generate_changes(old_config, new_config)

        if dry_run:
            report["dry_run"] = True
            return report

        # Backup old files
        self._backup_files(old_files)
        report["backups"] = {k: f"{v}{self.backup_suffix}" for k, v in old_files.items()}

        # Write new config
        new_config_path = self.config_dir / "config.json"
        with open(new_config_path, "w") as f:
            json.dump(new_config, f, indent=2)
        report["new_files"]["config.json"] = str(new_config_path)

        # Migrate config.env to .env if exists
        if "config.env" in old_files:
            new_env_path = self.config_dir / ".env"
            shutil.copy2(old_files["config.env"], new_env_path)
            report["new_files"][".env"] = str(new_env_path)

        return report

    def _convert_profile(self, old_config: dict[str, Any]) -> dict[str, Any]:
        """Convert old profile.yaml format to new config.json format.

        Old format:
            agent:
              model: ...
              model_provider: ...
            tool:
              filesystem: ...
            mcp: ...
            skills: ...

        New format:
            api:
              model: ...
              model_provider: ...
            tools:
              filesystem: ...
            mcp: ...
            skills: ...
        """
        new_config: dict[str, Any] = {}

        # Convert agent.* → api.*
        if "agent" in old_config:
            agent = old_config["agent"]
            new_config["api"] = {
                "model": agent.get("model", "claude-sonnet-4-5-20250929"),
                "model_provider": agent.get("model_provider"),
                "api_key": agent.get("api_key"),
                "base_url": agent.get("base_url"),
                "temperature": agent.get("temperature"),
                "max_tokens": agent.get("max_tokens"),
                "model_kwargs": agent.get("model_kwargs", {}),
                "context_limit": agent.get("context_limit", 100000),
                "enable_audit_log": agent.get("enable_audit_log", True),
                "allowed_extensions": agent.get("allowed_extensions"),
                "block_dangerous_commands": agent.get("block_dangerous_commands", True),
                "block_network_commands": agent.get("block_network_commands", False),
                "queue_mode": agent.get("queue_mode", "steer"),
            }

            # Convert memory config if exists
            if "memory" in agent:
                new_config["memory"] = self._convert_memory_config(agent["memory"])

        # Convert tool.* → tools.*
        if "tool" in old_config:
            new_config["tools"] = old_config["tool"]

        # Copy mcp as-is
        if "mcp" in old_config:
            new_config["mcp"] = old_config["mcp"]

        # Copy skills as-is
        if "skills" in old_config:
            new_config["skills"] = old_config["skills"]

        # Copy system_prompt if exists
        if "system_prompt" in old_config:
            new_config["system_prompt"] = old_config["system_prompt"]

        return new_config

    def _convert_memory_config(self, old_memory: dict[str, Any]) -> dict[str, Any]:
        """Convert old memory config to new format.

        Old format:
            pruning:
              soft_trim_chars: 3000
              hard_clear_threshold: 10000
              protect_recent: 3
            compaction:
              reserve_tokens: 16384
              keep_recent_tokens: 20000

        New format:
            pruning:
              enabled: true
              keep_recent: 10
              trim_tool_results: true
              max_tool_result_length: 5000
            compaction:
              enabled: true
              trigger_ratio: 0.8
              min_messages: 20
        """
        new_memory: dict[str, Any] = {}

        # Convert pruning config
        if "pruning" in old_memory:
            old_pruning = old_memory["pruning"]
            new_memory["pruning"] = {
                "enabled": old_memory.get("enabled", True),
                "keep_recent": old_pruning.get("protect_recent", 10),
                "trim_tool_results": True,
                "max_tool_result_length": old_pruning.get("soft_trim_chars", 5000),
            }

        # Convert compaction config
        if "compaction" in old_memory:
            old_compaction = old_memory["compaction"]
            new_memory["compaction"] = {
                "enabled": old_memory.get("enabled", True),
                "trigger_ratio": 0.8,  # Default value
                "min_messages": 20,  # Default value
            }

        return new_memory

    def _validate_config(self, config: dict[str, Any]) -> list[str]:
        """Validate migrated configuration.

        Args:
            config: New configuration dict

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate required fields
        if "api" not in config:
            errors.append("Missing 'api' section")
        else:
            api = config["api"]
            if "model" not in api:
                errors.append("Missing 'api.model' field")

        # Validate tools structure
        if "tools" in config:
            tools = config["tools"]
            valid_tools = ["filesystem", "search", "web", "command"]
            for tool_name in tools:
                if tool_name not in valid_tools:
                    errors.append(f"Unknown tool: {tool_name}")

        # Validate mcp structure
        if "mcp" in config:
            mcp = config["mcp"]
            if "servers" in mcp:
                for server_name, server_config in mcp["servers"].items():
                    if not isinstance(server_config, dict):
                        errors.append(f"Invalid MCP server config: {server_name}")
                    elif "command" not in server_config:
                        errors.append(f"Missing 'command' in MCP server: {server_name}")

        return errors

    def _generate_changes(self, old_config: dict[str, Any], new_config: dict[str, Any]) -> dict[str, Any]:
        """Generate summary of changes between old and new config.

        Args:
            old_config: Old configuration
            new_config: New configuration

        Returns:
            Dict describing changes
        """
        changes = {
            "renamed_sections": [],
            "new_fields": [],
            "removed_fields": [],
        }

        # Track renamed sections
        if "agent" in old_config and "api" in new_config:
            changes["renamed_sections"].append("agent → api")
        if "tool" in old_config and "tools" in new_config:
            changes["renamed_sections"].append("tool → tools")

        # Track memory config changes
        if "agent" in old_config and "memory" in old_config["agent"]:
            old_memory = old_config["agent"]["memory"]
            if "pruning" in old_memory:
                changes["removed_fields"].extend(
                    [
                        "memory.pruning.soft_trim_chars",
                        "memory.pruning.hard_clear_threshold",
                        "memory.pruning.protect_recent",
                    ]
                )
                changes["new_fields"].extend(
                    [
                        "memory.pruning.keep_recent",
                        "memory.pruning.trim_tool_results",
                        "memory.pruning.max_tool_result_length",
                    ]
                )
            if "compaction" in old_memory:
                changes["removed_fields"].extend(
                    [
                        "memory.compaction.reserve_tokens",
                        "memory.compaction.keep_recent_tokens",
                    ]
                )
                changes["new_fields"].extend(
                    [
                        "memory.compaction.trigger_ratio",
                        "memory.compaction.min_messages",
                    ]
                )

        return changes

    def _backup_files(self, old_files: dict[str, Path]) -> None:
        """Backup old configuration files.

        Args:
            old_files: Dict of {file_type: path}
        """
        for file_type, path in old_files.items():
            if file_type == "sandboxes":
                # Backup entire sandboxes directory
                backup_path = path.parent / f"{path.name}{self.backup_suffix}"
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                shutil.copytree(path, backup_path)
            else:
                # Backup individual file
                backup_path = path.parent / f"{path.name}{self.backup_suffix}"
                shutil.copy2(path, backup_path)

    def rollback(self) -> None:
        """Rollback migration by restoring backup files.

        Restores all .bak files and removes new config.json.

        Raises:
            ConfigMigrationError: If rollback fails (no backups found)

        Example:
            >>> migrator = ConfigMigrator(Path("~/.leon"))
            >>> migrator.rollback()  # Restores profile.yaml.bak → profile.yaml
        """
        # Find backup files
        backup_files = list(self.config_dir.glob(f"*{self.backup_suffix}"))
        if not backup_files:
            raise ConfigMigrationError("No backup files found")

        # Restore backups
        for backup_path in backup_files:
            original_path = backup_path.parent / backup_path.name.replace(self.backup_suffix, "")
            if backup_path.is_dir():
                if original_path.exists():
                    shutil.rmtree(original_path)
                shutil.copytree(backup_path, original_path)
            else:
                shutil.copy2(backup_path, original_path)

        # Remove new config.json
        new_config_path = self.config_dir / "config.json"
        if new_config_path.exists():
            new_config_path.unlink()


def migrate_config(config_dir: str | Path, dry_run: bool = False) -> dict[str, Any]:
    """Migrate old configuration to new format.

    Args:
        config_dir: Configuration directory (~/.leon or .leon/)
        dry_run: If True, only validate without writing files

    Returns:
        Migration report

    Raises:
        ConfigMigrationError: If migration fails
    """
    migrator = ConfigMigrator(config_dir)
    return migrator.migrate(dry_run=dry_run)
