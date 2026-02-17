"""Configuration migration tool.

Migrates from old formats to new models.json + runtime.json:
- profile.yaml → runtime.json (old agent/tool sections)
- config.json → models.json (api.model, api_key, base_url, model_provider)
- settings.json → models.json (providers, model_mapping, enabled_models, custom_models)
- providers.json → models.json (provider credentials)
- settings.json workspace fields → preferences.json
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import yaml


class ConfigMigrationError(Exception):
    pass


class ConfigMigrator:
    """Migrate old configuration format to new format."""

    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self.backup_suffix = ".bak"

    def detect_old_config(self) -> dict[str, Path]:
        """Detect old configuration files."""
        old_files = {}

        for name in ("profile.yaml", "config.json", "settings.json", "providers.json", "config.env"):
            path = self.config_dir / name
            if path.exists():
                old_files[name] = path

        sandboxes_dir = self.config_dir / "sandboxes"
        if sandboxes_dir.exists() and list(sandboxes_dir.glob("*.json")):
            old_files["sandboxes"] = sandboxes_dir

        return old_files

    def migrate(self, dry_run: bool = False) -> dict[str, Any]:
        """Migrate old configuration to new format."""
        old_files = self.detect_old_config()
        if not old_files:
            raise ConfigMigrationError("No old configuration files found")

        report: dict[str, Any] = {
            "old_files": {k: str(v) for k, v in old_files.items()},
            "new_files": {},
            "changes": [],
        }

        models_data: dict[str, Any] = {}
        runtime_data: dict[str, Any] = {}

        # 1. Migrate profile.yaml → runtime.json
        if "profile.yaml" in old_files:
            with open(old_files["profile.yaml"]) as f:
                old_config = yaml.safe_load(f) or {}
            runtime_data, profile_models = self._convert_profile(old_config)
            models_data.update(profile_models)
            report["changes"].append("profile.yaml → runtime.json + models.json")

        # 2. Migrate config.json → models.json (api section)
        if "config.json" in old_files:
            with open(old_files["config.json"], encoding="utf-8") as f:
                config_json = json.load(f)
            api = config_json.get("api", {})
            if api.get("api_key") or api.get("base_url"):
                provider_name = api.get("model_provider", "default")
                p: dict[str, Any] = {}
                if api.get("api_key"):
                    p["api_key"] = api["api_key"]
                if api.get("base_url"):
                    p["base_url"] = api["base_url"]
                models_data.setdefault("providers", {})[provider_name] = p
            report["changes"].append("config.json api.* → models.json")

        # 3. Migrate settings.json → models.json
        if "settings.json" in old_files:
            with open(old_files["settings.json"], encoding="utf-8") as f:
                settings = json.load(f)
            if settings.get("providers"):
                for name, cfg in settings["providers"].items():
                    models_data.setdefault("providers", {})[name] = cfg
            if settings.get("model_mapping"):
                for vname, model_id in settings["model_mapping"].items():
                    models_data.setdefault("mapping", {})[vname] = {"model": model_id}
            if settings.get("enabled_models"):
                models_data.setdefault("pool", {})["enabled"] = settings["enabled_models"]
            if settings.get("custom_models"):
                models_data.setdefault("pool", {})["custom"] = settings["custom_models"]
            report["changes"].append("settings.json → models.json + preferences.json (workspace only)")

        # 4. Migrate providers.json → models.json
        if "providers.json" in old_files:
            with open(old_files["providers.json"], encoding="utf-8") as f:
                raw = json.load(f)
            # providers.json may be {"providers": {...}} or flat {"openai": {...}}
            providers = raw.get("providers", raw) if isinstance(raw, dict) else {}
            for name, cfg in providers.items():
                if isinstance(cfg, dict):
                    models_data.setdefault("providers", {})[name] = cfg
            report["changes"].append("providers.json → models.json providers")

        if dry_run:
            report["dry_run"] = True
            report["models_data"] = models_data
            report["runtime_data"] = runtime_data
            return report

        # Backup old files
        self._backup_files(old_files)

        # Write new files
        if models_data:
            models_path = self.config_dir / "models.json"
            with open(models_path, "w", encoding="utf-8") as f:
                json.dump(models_data, f, indent=2, ensure_ascii=False)
            report["new_files"]["models.json"] = str(models_path)

        if runtime_data:
            runtime_path = self.config_dir / "runtime.json"
            with open(runtime_path, "w", encoding="utf-8") as f:
                json.dump(runtime_data, f, indent=2, ensure_ascii=False)
            report["new_files"]["runtime.json"] = str(runtime_path)

        # Preserve workspace-only preferences.json (renamed from settings.json)
        if "settings.json" in old_files:
            with open(old_files["settings.json"], encoding="utf-8") as f:
                settings = json.load(f)
            slim = {}
            if settings.get("default_workspace"):
                slim["default_workspace"] = settings["default_workspace"]
            if settings.get("recent_workspaces"):
                slim["recent_workspaces"] = settings["recent_workspaces"]
            if slim:
                with open(self.config_dir / "preferences.json", "w", encoding="utf-8") as f:
                    json.dump(slim, f, indent=2, ensure_ascii=False)

        # Migrate config.env → .env
        if "config.env" in old_files:
            new_env_path = self.config_dir / ".env"
            shutil.copy2(old_files["config.env"], new_env_path)
            report["new_files"][".env"] = str(new_env_path)

        return report

    def _convert_profile(self, old_config: dict[str, Any]) -> tuple[dict, dict]:
        """Convert profile.yaml → (runtime_data, models_data)."""
        runtime: dict[str, Any] = {}
        models: dict[str, Any] = {}

        if "agent" in old_config:
            agent = old_config["agent"]
            # Provider credentials → models_data
            if agent.get("api_key") or agent.get("base_url"):
                p: dict[str, Any] = {}
                if agent.get("api_key"):
                    p["api_key"] = agent["api_key"]
                if agent.get("base_url"):
                    p["base_url"] = agent["base_url"]
                provider_name = agent.get("model_provider", "default")
                models.setdefault("providers", {})[provider_name] = p

            # Runtime behavior → runtime_data
            rt: dict[str, Any] = {}
            for key in (
                "temperature",
                "max_tokens",
                "model_kwargs",
                "context_limit",
                "enable_audit_log",
                "allowed_extensions",
                "block_dangerous_commands",
                "block_network_commands",
                "queue_mode",
            ):
                if key in agent:
                    rt[key] = agent[key]
            if rt:
                runtime["runtime"] = rt

            # Memory
            if "memory" in agent:
                runtime["memory"] = self._convert_memory_config(agent["memory"])

        # Tools
        if "tool" in old_config:
            runtime["tools"] = old_config["tool"]

        # MCP / Skills / system_prompt
        for key in ("mcp", "skills", "system_prompt"):
            if key in old_config:
                runtime[key] = old_config[key]

        return runtime, models

    def _convert_memory_config(self, old_memory: dict[str, Any]) -> dict[str, Any]:
        """Convert old memory config to new format."""
        new_memory: dict[str, Any] = {}

        if "pruning" in old_memory:
            old_pruning = old_memory["pruning"]
            new_memory["pruning"] = {
                "enabled": old_memory.get("enabled", True),
                "soft_trim_chars": old_pruning.get("soft_trim_chars", 3000),
                "hard_clear_threshold": old_pruning.get("hard_clear_threshold", 10000),
                "protect_recent": old_pruning.get("protect_recent", 3),
                "trim_tool_results": True,
            }

        if "compaction" in old_memory:
            old_compaction = old_memory["compaction"]
            new_memory["compaction"] = {
                "enabled": old_memory.get("enabled", True),
                "reserve_tokens": old_compaction.get("reserve_tokens", 16384),
                "keep_recent_tokens": old_compaction.get("keep_recent_tokens", 20000),
                "min_messages": old_compaction.get("min_messages", 20),
            }

        return new_memory

    def _backup_files(self, old_files: dict[str, Path]) -> None:
        """Backup old configuration files."""
        for file_type, path in old_files.items():
            if file_type == "sandboxes":
                backup_path = path.parent / f"{path.name}{self.backup_suffix}"
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                shutil.copytree(path, backup_path)
            else:
                backup_path = path.parent / f"{path.name}{self.backup_suffix}"
                shutil.copy2(path, backup_path)

    def rollback(self) -> None:
        """Rollback migration by restoring backup files."""
        backup_files = list(self.config_dir.glob(f"*{self.backup_suffix}"))
        if not backup_files:
            raise ConfigMigrationError("No backup files found")

        for backup_path in backup_files:
            original_path = backup_path.parent / backup_path.name.replace(self.backup_suffix, "")
            if backup_path.is_dir():
                if original_path.exists():
                    shutil.rmtree(original_path)
                shutil.copytree(backup_path, original_path)
            else:
                shutil.copy2(backup_path, original_path)

        # Remove new files
        for name in ("models.json", "runtime.json"):
            new_path = self.config_dir / name
            if new_path.exists():
                new_path.unlink()


def migrate_config(config_dir: str | Path, dry_run: bool = False) -> dict[str, Any]:
    """Migrate old configuration to new format."""
    migrator = ConfigMigrator(config_dir)
    return migrator.migrate(dry_run=dry_run)
