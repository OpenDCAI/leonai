"""Tests for configuration migration."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from config.migrate import ConfigMigrationError, ConfigMigrator


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def old_profile_yaml(temp_config_dir):
    """Create old profile.yaml file."""
    profile_data = {
        "agent": {
            "model": "gpt-4",
            "model_provider": "openai",
            "temperature": 0.7,
            "enable_audit_log": True,
            "block_dangerous_commands": True,
            "memory": {
                "enabled": True,
                "pruning": {
                    "soft_trim_chars": 3000,
                    "hard_clear_threshold": 10000,
                    "protect_recent": 3,
                },
                "compaction": {
                    "reserve_tokens": 16384,
                    "keep_recent_tokens": 20000,
                },
            },
        },
        "tool": {
            "filesystem": {"enabled": True},
            "search": {"enabled": True},
            "web": {"enabled": True},
            "command": {"enabled": True},
        },
        "mcp": {
            "enabled": True,
            "servers": {
                "context7": {
                    "command": "npx",
                    "args": ["-y", "@upstash/context7-mcp"],
                }
            },
        },
        "skills": {
            "enabled": True,
            "paths": ["~/.leon/skills"],
        },
    }

    profile_path = temp_config_dir / "profile.yaml"
    with open(profile_path, "w") as f:
        yaml.dump(profile_data, f)

    return profile_path


@pytest.fixture
def old_config_env(temp_config_dir):
    """Create old config.env file."""
    env_content = """OPENAI_API_KEY=sk-test123
OPENAI_BASE_URL=https://api.openai.com
MODEL_NAME=gpt-4
"""
    env_path = temp_config_dir / "config.env"
    env_path.write_text(env_content)
    return env_path


class TestConfigMigrator:
    """Test configuration migrator."""

    def test_detect_old_config(self, temp_config_dir, old_profile_yaml):
        """Test detecting old configuration files."""
        migrator = ConfigMigrator(temp_config_dir)
        old_files = migrator.detect_old_config()

        assert "profile.yaml" in old_files
        assert old_files["profile.yaml"] == old_profile_yaml

    def test_detect_no_old_config(self, temp_config_dir):
        """Test detecting when no old config exists."""
        migrator = ConfigMigrator(temp_config_dir)
        old_files = migrator.detect_old_config()

        assert len(old_files) == 0

    def test_convert_profile_basic(self, temp_config_dir, old_profile_yaml):
        """Test basic profile conversion."""
        migrator = ConfigMigrator(temp_config_dir)

        with open(old_profile_yaml) as f:
            old_config = yaml.safe_load(f)

        new_config = migrator._convert_profile(old_config)

        # Check agent → api conversion
        assert "api" in new_config
        assert new_config["api"]["model"] == "gpt-4"
        assert new_config["api"]["model_provider"] == "openai"
        assert new_config["api"]["temperature"] == 0.7

        # Check tool → tools conversion
        assert "tools" in new_config
        assert new_config["tools"]["filesystem"]["enabled"] is True

        # Check mcp copied as-is
        assert "mcp" in new_config
        assert "context7" in new_config["mcp"]["servers"]

        # Check skills copied as-is
        assert "skills" in new_config
        assert new_config["skills"]["enabled"] is True

    def test_convert_memory_config(self, temp_config_dir, old_profile_yaml):
        """Test memory config conversion."""
        migrator = ConfigMigrator(temp_config_dir)

        with open(old_profile_yaml) as f:
            old_config = yaml.safe_load(f)

        new_config = migrator._convert_profile(old_config)

        # Check memory conversion
        assert "memory" in new_config
        assert "pruning" in new_config["memory"]
        assert "compaction" in new_config["memory"]

        # Check pruning fields
        pruning = new_config["memory"]["pruning"]
        assert pruning["enabled"] is True
        assert pruning["keep_recent"] == 3  # From protect_recent
        assert pruning["max_tool_result_length"] == 3000  # From soft_trim_chars

        # Check compaction fields
        compaction = new_config["memory"]["compaction"]
        assert compaction["enabled"] is True
        assert compaction["trigger_ratio"] == 0.8
        assert compaction["min_messages"] == 20

    def test_validate_config_valid(self, temp_config_dir, old_profile_yaml):
        """Test validation of valid config."""
        migrator = ConfigMigrator(temp_config_dir)

        with open(old_profile_yaml) as f:
            old_config = yaml.safe_load(f)

        new_config = migrator._convert_profile(old_config)
        errors = migrator._validate_config(new_config)

        assert len(errors) == 0

    def test_validate_config_missing_api(self, temp_config_dir):
        """Test validation fails when api section missing."""
        migrator = ConfigMigrator(temp_config_dir)

        new_config = {"tools": {}}
        errors = migrator._validate_config(new_config)

        assert len(errors) > 0
        assert any("api" in err for err in errors)

    def test_validate_config_missing_model(self, temp_config_dir):
        """Test validation fails when model missing."""
        migrator = ConfigMigrator(temp_config_dir)

        new_config = {"api": {}}
        errors = migrator._validate_config(new_config)

        assert len(errors) > 0
        assert any("model" in err for err in errors)

    def test_validate_config_invalid_mcp(self, temp_config_dir):
        """Test validation fails for invalid MCP config."""
        migrator = ConfigMigrator(temp_config_dir)

        new_config = {
            "api": {"model": "gpt-4"},
            "mcp": {
                "servers": {
                    "test": {}  # Missing command
                }
            },
        }
        errors = migrator._validate_config(new_config)

        assert len(errors) > 0
        assert any("command" in err and "test" in err for err in errors)

    def test_generate_changes(self, temp_config_dir, old_profile_yaml):
        """Test change summary generation."""
        migrator = ConfigMigrator(temp_config_dir)

        with open(old_profile_yaml) as f:
            old_config = yaml.safe_load(f)

        new_config = migrator._convert_profile(old_config)
        changes = migrator._generate_changes(old_config, new_config)

        # Check renamed sections
        assert "agent → api" in changes["renamed_sections"]
        assert "tool → tools" in changes["renamed_sections"]

        # Check memory field changes
        assert any("soft_trim_chars" in field for field in changes["removed_fields"])
        assert any("keep_recent" in field for field in changes["new_fields"])

    def test_migrate_dry_run(self, temp_config_dir, old_profile_yaml):
        """Test dry run migration."""
        migrator = ConfigMigrator(temp_config_dir)
        report = migrator.migrate(dry_run=True)

        assert report["dry_run"] is True
        assert "profile.yaml" in report["old_files"]
        assert len(report["validation"]["errors"]) == 0

        # Check no files were created
        assert not (temp_config_dir / "config.json").exists()
        assert not (temp_config_dir / "profile.yaml.bak").exists()

    def test_migrate_full(self, temp_config_dir, old_profile_yaml, old_config_env):
        """Test full migration."""
        migrator = ConfigMigrator(temp_config_dir)
        report = migrator.migrate(dry_run=False)

        # Check report
        assert "dry_run" not in report or report["dry_run"] is False
        assert "profile.yaml" in report["old_files"]
        assert "config.env" in report["old_files"]
        assert len(report["validation"]["errors"]) == 0

        # Check new files created
        assert (temp_config_dir / "config.json").exists()
        assert (temp_config_dir / ".env").exists()

        # Check backups created
        assert (temp_config_dir / "profile.yaml.bak").exists()
        assert (temp_config_dir / "config.env.bak").exists()

        # Verify new config content
        with open(temp_config_dir / "config.json") as f:
            new_config = json.load(f)

        assert "api" in new_config
        assert new_config["api"]["model"] == "gpt-4"
        assert "tools" in new_config

    def test_migrate_no_old_config(self, temp_config_dir):
        """Test migration fails when no old config exists."""
        migrator = ConfigMigrator(temp_config_dir)

        with pytest.raises(ConfigMigrationError, match="No old configuration files found"):
            migrator.migrate()

    def test_rollback(self, temp_config_dir, old_profile_yaml):
        """Test rollback migration."""
        migrator = ConfigMigrator(temp_config_dir)

        # First migrate
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
        """Test rollback fails when no backups exist."""
        migrator = ConfigMigrator(temp_config_dir)

        with pytest.raises(ConfigMigrationError, match="No backup files found"):
            migrator.rollback()

    def test_backup_files(self, temp_config_dir, old_profile_yaml):
        """Test backup file creation."""
        migrator = ConfigMigrator(temp_config_dir)

        old_files = {"profile.yaml": old_profile_yaml}
        migrator._backup_files(old_files)

        backup_path = temp_config_dir / "profile.yaml.bak"
        assert backup_path.exists()

        # Verify backup content matches original
        with open(old_profile_yaml) as f1, open(backup_path) as f2:
            assert f1.read() == f2.read()
