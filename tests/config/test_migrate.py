"""Comprehensive tests for config.migrate module."""

import json
from pathlib import Path

import pytest
import yaml

from config.migrate import ConfigMigrationError, ConfigMigrator, migrate_config


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory for testing."""
    config_dir = tmp_path / ".leon"
    config_dir.mkdir()
    return config_dir


class TestConfigMigrator:
    """Tests for ConfigMigrator."""

    def test_init(self, temp_config_dir):
        migrator = ConfigMigrator(temp_config_dir)
        assert migrator.config_dir == temp_config_dir
        assert migrator.backup_suffix == ".bak"

    def test_detect_old_config_profile_yaml(self, temp_config_dir):
        # Create old profile.yaml
        profile_yaml = temp_config_dir / "profile.yaml"
        profile_yaml.write_text("agent:\n  model: gpt-4\n")

        migrator = ConfigMigrator(temp_config_dir)
        old_files = migrator.detect_old_config()

        assert "profile.yaml" in old_files
        assert old_files["profile.yaml"] == profile_yaml

    def test_detect_old_config_config_env(self, temp_config_dir):
        # Create old config.env
        config_env = temp_config_dir / "config.env"
        config_env.write_text("OPENAI_API_KEY=test\n")

        migrator = ConfigMigrator(temp_config_dir)
        old_files = migrator.detect_old_config()

        assert "config.env" in old_files
        assert old_files["config.env"] == config_env

    def test_detect_old_config_sandboxes(self, temp_config_dir):
        # Create sandboxes directory
        sandboxes_dir = temp_config_dir / "sandboxes"
        sandboxes_dir.mkdir()
        (sandboxes_dir / "local.json").write_text("{}")

        migrator = ConfigMigrator(temp_config_dir)
        old_files = migrator.detect_old_config()

        assert "sandboxes" in old_files
        assert old_files["sandboxes"] == sandboxes_dir

    def test_detect_old_config_none(self, temp_config_dir):
        migrator = ConfigMigrator(temp_config_dir)
        old_files = migrator.detect_old_config()

        assert old_files == {}

    def test_convert_profile_agent_to_api(self):
        migrator = ConfigMigrator(Path("/tmp"))

        old_config = {
            "agent": {
                "model": "gpt-4",
                "model_provider": "openai",
                "api_key": "test-key",
                "base_url": "https://api.openai.com",
                "temperature": 0.7,
                "max_tokens": 4096,
                "model_kwargs": {"top_p": 0.9},
                "context_limit": 128000,
                "enable_audit_log": False,
                "allowed_extensions": [".py", ".js"],
                "block_dangerous_commands": False,
                "block_network_commands": True,
                "queue_mode": "followup",
            }
        }

        new_config = migrator._convert_profile(old_config)

        assert "api" in new_config
        assert new_config["api"]["model"] == "gpt-4"
        assert new_config["api"]["model_provider"] == "openai"
        assert new_config["api"]["api_key"] == "test-key"
        assert new_config["api"]["base_url"] == "https://api.openai.com"
        assert new_config["api"]["temperature"] == 0.7
        assert new_config["api"]["max_tokens"] == 4096
        assert new_config["api"]["model_kwargs"] == {"top_p": 0.9}
        assert new_config["api"]["context_limit"] == 128000
        assert new_config["api"]["enable_audit_log"] is False
        assert new_config["api"]["allowed_extensions"] == [".py", ".js"]
        assert new_config["api"]["block_dangerous_commands"] is False
        assert new_config["api"]["block_network_commands"] is True
        assert new_config["api"]["queue_mode"] == "followup"

    def test_convert_profile_tool_to_tools(self):
        migrator = ConfigMigrator(Path("/tmp"))

        old_config = {
            "tool": {
                "filesystem": {"enabled": False},
                "search": {"max_results": 100},
            }
        }

        new_config = migrator._convert_profile(old_config)

        assert "tools" in new_config
        assert new_config["tools"]["filesystem"]["enabled"] is False
        assert new_config["tools"]["search"]["max_results"] == 100

    def test_convert_profile_mcp_passthrough(self):
        migrator = ConfigMigrator(Path("/tmp"))

        old_config = {
            "mcp": {
                "enabled": True,
                "servers": {
                    "test_server": {
                        "command": "node",
                        "args": ["server.js"],
                    }
                },
            }
        }

        new_config = migrator._convert_profile(old_config)

        assert "mcp" in new_config
        assert new_config["mcp"]["enabled"] is True
        assert "test_server" in new_config["mcp"]["servers"]

    def test_convert_profile_skills_passthrough(self):
        migrator = ConfigMigrator(Path("/tmp"))

        old_config = {
            "skills": {
                "enabled": False,
                "paths": ["./custom_skills"],
                "skills": {"skill1": True},
            }
        }

        new_config = migrator._convert_profile(old_config)

        assert "skills" in new_config
        assert new_config["skills"]["enabled"] is False
        assert new_config["skills"]["paths"] == ["./custom_skills"]

    def test_convert_profile_system_prompt(self):
        migrator = ConfigMigrator(Path("/tmp"))

        old_config = {"system_prompt": "Custom system prompt"}

        new_config = migrator._convert_profile(old_config)

        assert new_config["system_prompt"] == "Custom system prompt"

    def test_convert_memory_config(self):
        migrator = ConfigMigrator(Path("/tmp"))

        old_memory = {
            "enabled": True,
            "pruning": {
                "soft_trim_chars": 3000,
                "hard_clear_threshold": 10000,
                "protect_recent": 5,
            },
            "compaction": {
                "reserve_tokens": 16384,
                "keep_recent_tokens": 20000,
            },
        }

        new_memory = migrator._convert_memory_config(old_memory)

        assert new_memory["pruning"]["enabled"] is True
        assert new_memory["pruning"]["keep_recent"] == 5
        assert new_memory["pruning"]["trim_tool_results"] is True
        assert new_memory["pruning"]["max_tool_result_length"] == 3000

        assert new_memory["compaction"]["enabled"] is True
        assert new_memory["compaction"]["trigger_ratio"] == 0.8
        assert new_memory["compaction"]["min_messages"] == 20

    def test_validate_config_valid(self):
        migrator = ConfigMigrator(Path("/tmp"))

        config = {
            "api": {"model": "gpt-4"},
            "tools": {"filesystem": {"enabled": True}},
            "mcp": {"servers": {"test": {"command": "node"}}},
        }

        errors = migrator._validate_config(config)
        assert errors == []

    def test_validate_config_missing_api(self):
        migrator = ConfigMigrator(Path("/tmp"))

        config = {"tools": {}}

        errors = migrator._validate_config(config)
        assert len(errors) > 0
        assert any("api" in err for err in errors)

    def test_validate_config_missing_model(self):
        migrator = ConfigMigrator(Path("/tmp"))

        config = {"api": {}}

        errors = migrator._validate_config(config)
        assert len(errors) > 0
        assert any("model" in err for err in errors)

    def test_validate_config_unknown_tool(self):
        migrator = ConfigMigrator(Path("/tmp"))

        config = {
            "api": {"model": "gpt-4"},
            "tools": {"unknown_tool": {}},
        }

        errors = migrator._validate_config(config)
        assert len(errors) > 0
        assert any("unknown_tool" in err for err in errors)

    def test_validate_config_invalid_mcp_server(self):
        migrator = ConfigMigrator(Path("/tmp"))

        config = {
            "api": {"model": "gpt-4"},
            "mcp": {"servers": {"test": {}}},  # Missing command
        }

        errors = migrator._validate_config(config)
        assert len(errors) > 0
        assert any("command" in err for err in errors)

    def test_generate_changes(self):
        migrator = ConfigMigrator(Path("/tmp"))

        old_config = {
            "agent": {
                "model": "gpt-4",
                "memory": {
                    "pruning": {
                        "soft_trim_chars": 3000,
                        "protect_recent": 5,
                    },
                    "compaction": {
                        "reserve_tokens": 16384,
                    },
                },
            },
            "tool": {"filesystem": {}},
        }

        new_config = {
            "api": {"model": "gpt-4"},
            "tools": {"filesystem": {}},
        }

        changes = migrator._generate_changes(old_config, new_config)

        assert "agent → api" in changes["renamed_sections"]
        assert "tool → tools" in changes["renamed_sections"]

    def test_backup_files(self, temp_config_dir):
        migrator = ConfigMigrator(temp_config_dir)

        # Create files to backup
        profile_yaml = temp_config_dir / "profile.yaml"
        profile_yaml.write_text("test")

        config_env = temp_config_dir / "config.env"
        config_env.write_text("test")

        old_files = {
            "profile.yaml": profile_yaml,
            "config.env": config_env,
        }

        migrator._backup_files(old_files)

        assert (temp_config_dir / "profile.yaml.bak").exists()
        assert (temp_config_dir / "config.env.bak").exists()

    def test_backup_sandboxes_directory(self, temp_config_dir):
        migrator = ConfigMigrator(temp_config_dir)

        # Create sandboxes directory
        sandboxes_dir = temp_config_dir / "sandboxes"
        sandboxes_dir.mkdir()
        (sandboxes_dir / "local.json").write_text("{}")

        old_files = {"sandboxes": sandboxes_dir}

        migrator._backup_files(old_files)

        backup_dir = temp_config_dir / "sandboxes.bak"
        assert backup_dir.exists()
        assert (backup_dir / "local.json").exists()

    def test_migrate_dry_run(self, temp_config_dir):
        # Create old config
        profile_yaml = temp_config_dir / "profile.yaml"
        old_config = {"agent": {"model": "gpt-4"}}
        with open(profile_yaml, "w") as f:
            yaml.dump(old_config, f)

        migrator = ConfigMigrator(temp_config_dir)
        report = migrator.migrate(dry_run=True)

        assert report["dry_run"] is True
        assert "profile.yaml" in report["old_files"]
        assert "validation" in report
        assert report["validation"]["errors"] == []

        # Should not create new files
        assert not (temp_config_dir / "config.json").exists()
        assert not (temp_config_dir / "profile.yaml.bak").exists()

    def test_migrate_success(self, temp_config_dir):
        # Create old config
        profile_yaml = temp_config_dir / "profile.yaml"
        old_config = {"agent": {"model": "gpt-4"}}
        with open(profile_yaml, "w") as f:
            yaml.dump(old_config, f)

        migrator = ConfigMigrator(temp_config_dir)
        report = migrator.migrate(dry_run=False)

        assert "dry_run" not in report
        assert "profile.yaml" in report["old_files"]
        assert "config.json" in report["new_files"]
        assert "backups" in report

        # Should create new config
        assert (temp_config_dir / "config.json").exists()
        assert (temp_config_dir / "profile.yaml.bak").exists()

        # Verify new config content
        with open(temp_config_dir / "config.json") as f:
            new_config = json.load(f)
        assert new_config["api"]["model"] == "gpt-4"

    def test_migrate_with_config_env(self, temp_config_dir):
        # Create old configs
        profile_yaml = temp_config_dir / "profile.yaml"
        with open(profile_yaml, "w") as f:
            yaml.dump({"agent": {"model": "gpt-4"}}, f)

        config_env = temp_config_dir / "config.env"
        config_env.write_text("OPENAI_API_KEY=test\n")

        migrator = ConfigMigrator(temp_config_dir)
        report = migrator.migrate(dry_run=False)

        assert ".env" in report["new_files"]
        assert (temp_config_dir / ".env").exists()

    def test_migrate_validation_error(self, temp_config_dir):
        # Create invalid config (unknown tool)
        profile_yaml = temp_config_dir / "profile.yaml"
        old_config = {
            "agent": {"model": "gpt-4"},
            "tool": {"invalid_tool": {}},  # Unknown tool
        }
        with open(profile_yaml, "w") as f:
            yaml.dump(old_config, f)

        migrator = ConfigMigrator(temp_config_dir)

        with pytest.raises(ConfigMigrationError, match="Validation failed"):
            migrator.migrate(dry_run=False)

    def test_migrate_no_old_config(self, temp_config_dir):
        migrator = ConfigMigrator(temp_config_dir)

        with pytest.raises(ConfigMigrationError, match="No old configuration files found"):
            migrator.migrate(dry_run=False)

    def test_rollback(self, temp_config_dir):
        # Create old config and migrate
        profile_yaml = temp_config_dir / "profile.yaml"
        with open(profile_yaml, "w") as f:
            yaml.dump({"agent": {"model": "gpt-4"}}, f)

        migrator = ConfigMigrator(temp_config_dir)
        migrator.migrate(dry_run=False)

        # Verify migration happened
        assert (temp_config_dir / "config.json").exists()
        assert (temp_config_dir / "profile.yaml.bak").exists()

        # Rollback
        migrator.rollback()

        # Verify rollback
        assert (temp_config_dir / "profile.yaml").exists()
        assert not (temp_config_dir / "config.json").exists()

    def test_rollback_no_backups(self, temp_config_dir):
        migrator = ConfigMigrator(temp_config_dir)

        with pytest.raises(ConfigMigrationError, match="No backup files found"):
            migrator.rollback()

    def test_migrate_complex_config(self, temp_config_dir):
        # Create complex old config
        profile_yaml = temp_config_dir / "profile.yaml"
        old_config = {
            "agent": {
                "model": "gpt-4",
                "temperature": 0.7,
                "memory": {
                    "pruning": {
                        "soft_trim_chars": 3000,
                        "protect_recent": 5,
                    },
                    "compaction": {
                        "reserve_tokens": 16384,
                    },
                },
            },
            "tool": {
                "filesystem": {"enabled": False},
                "search": {"max_results": 100},
            },
            "mcp": {
                "servers": {
                    "test_server": {
                        "command": "node",
                        "args": ["server.js"],
                    }
                }
            },
            "skills": {
                "enabled": True,
                "paths": ["./skills"],
            },
            "system_prompt": "Custom prompt",
        }
        with open(profile_yaml, "w") as f:
            yaml.dump(old_config, f)

        migrator = ConfigMigrator(temp_config_dir)
        report = migrator.migrate(dry_run=False)

        # Verify migration
        with open(temp_config_dir / "config.json") as f:
            new_config = json.load(f)

        assert new_config["api"]["model"] == "gpt-4"
        assert new_config["api"]["temperature"] == 0.7
        assert new_config["memory"]["pruning"]["keep_recent"] == 5
        assert new_config["tools"]["filesystem"]["enabled"] is False
        assert new_config["tools"]["search"]["max_results"] == 100
        assert "test_server" in new_config["mcp"]["servers"]
        assert new_config["skills"]["enabled"] is True
        assert new_config["system_prompt"] == "Custom prompt"

        # Verify changes report
        assert "agent → api" in report["changes"]["renamed_sections"]
        assert "tool → tools" in report["changes"]["renamed_sections"]


class TestMigrateConfigFunction:
    """Tests for migrate_config convenience function."""

    def test_migrate_config_basic(self, temp_config_dir):
        # Create old config
        profile_yaml = temp_config_dir / "profile.yaml"
        with open(profile_yaml, "w") as f:
            yaml.dump({"agent": {"model": "gpt-4"}}, f)

        report = migrate_config(temp_config_dir, dry_run=False)

        assert "config.json" in report["new_files"]
        assert (temp_config_dir / "config.json").exists()

    def test_migrate_config_dry_run(self, temp_config_dir):
        # Create old config
        profile_yaml = temp_config_dir / "profile.yaml"
        with open(profile_yaml, "w") as f:
            yaml.dump({"agent": {"model": "gpt-4"}}, f)

        report = migrate_config(temp_config_dir, dry_run=True)

        assert report["dry_run"] is True
        assert not (temp_config_dir / "config.json").exists()

    def test_migrate_config_string_path(self, temp_config_dir):
        # Create old config
        profile_yaml = temp_config_dir / "profile.yaml"
        with open(profile_yaml, "w") as f:
            yaml.dump({"agent": {"model": "gpt-4"}}, f)

        report = migrate_config(str(temp_config_dir), dry_run=False)

        assert "config.json" in report["new_files"]
