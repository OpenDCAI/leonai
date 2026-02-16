"""Comprehensive tests for config.loader module."""

import json
import os

import pytest

from config.loader import ConfigLoader, load_config
from config.schema import LeonSettings


@pytest.fixture
def temp_config_dirs(tmp_path, monkeypatch):
    """Create temporary config directories for testing."""
    # Set up directory structure
    system_defaults = tmp_path / "system_defaults"
    system_defaults.mkdir()
    (system_defaults / "agents").mkdir()

    user_config_dir = tmp_path / "user_config"
    user_config_dir.mkdir()

    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".leon").mkdir()

    # Mock the system defaults directory
    monkeypatch.setattr(
        "config.loader.Path.__truediv__",
        lambda self, other: system_defaults / other if "defaults" in str(self) else self / other,
    )

    # Set HOME to user_config_dir
    monkeypatch.setenv("HOME", str(user_config_dir))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    return {
        "system_defaults": system_defaults,
        "user_config": user_config_dir,
        "project_root": project_root,
    }


class TestConfigLoader:
    """Tests for ConfigLoader."""

    def test_init(self, tmp_path):
        loader = ConfigLoader(workspace_root=str(tmp_path))
        assert loader.workspace_root == tmp_path

    def test_init_no_workspace(self):
        loader = ConfigLoader()
        assert loader.workspace_root is None

    def test_load_system_defaults(self, tmp_path, monkeypatch):
        # Create system defaults
        defaults_dir = tmp_path / "defaults"
        defaults_dir.mkdir()
        agents_dir = defaults_dir / "agents"
        agents_dir.mkdir()

        default_config = {
            "api": {"model": "claude-sonnet-4-5-20250929"},
            "memory": {"pruning": {"protect_recent": 10}},
        }

        with open(agents_dir / "default.json", "w") as f:
            json.dump(default_config, f)

        # Mock the defaults directory path
        loader = ConfigLoader()
        loader._system_defaults_dir = defaults_dir

        result = loader._load_system_defaults()
        assert result["api"]["model"] == "claude-sonnet-4-5-20250929"
        assert result["memory"]["pruning"]["protect_recent"] == 10

    def test_load_system_defaults_missing(self, tmp_path):
        loader = ConfigLoader()
        loader._system_defaults_dir = tmp_path / "nonexistent"

        result = loader._load_system_defaults()
        assert result == {}

    def test_load_user_config(self, tmp_path, monkeypatch):
        # Create user config
        user_dir = tmp_path / ".leon"
        user_dir.mkdir()

        user_config = {
            "api": {"temperature": 0.7},
            "tools": {"filesystem": {"enabled": False}},
        }

        with open(user_dir / "config.json", "w") as f:
            json.dump(user_config, f)

        monkeypatch.setenv("HOME", str(tmp_path))

        loader = ConfigLoader()
        result = loader._load_user_config()
        assert result["api"]["temperature"] == 0.7
        assert result["tools"]["filesystem"]["enabled"] is False

    def test_load_user_config_missing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))

        loader = ConfigLoader()
        result = loader._load_user_config()
        assert result == {}

    def test_load_project_config(self, tmp_path):
        # Create project config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        leon_dir = project_dir / ".leon"
        leon_dir.mkdir()

        project_config = {
            "api": {"model": "gpt-4"},
            "system_prompt": "Project prompt",
        }

        with open(leon_dir / "config.json", "w") as f:
            json.dump(project_config, f)

        loader = ConfigLoader(workspace_root=str(project_dir))
        result = loader._load_project_config()
        assert result["api"]["model"] == "gpt-4"
        assert result["system_prompt"] == "Project prompt"

    def test_load_project_config_no_workspace(self):
        loader = ConfigLoader()
        result = loader._load_project_config()
        assert result == {}

    def test_load_project_config_missing(self, tmp_path):
        loader = ConfigLoader(workspace_root=str(tmp_path))
        result = loader._load_project_config()
        assert result == {}

    def test_deep_merge_simple(self):
        loader = ConfigLoader()

        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}

        result = loader._deep_merge(dict1, dict2)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested(self):
        loader = ConfigLoader()

        dict1 = {"api": {"model": "gpt-3", "temperature": 0.5}}
        dict2 = {"api": {"model": "gpt-4"}}

        result = loader._deep_merge(dict1, dict2)
        assert result["api"]["model"] == "gpt-4"
        assert result["api"]["temperature"] == 0.5

    def test_deep_merge_none_values(self):
        loader = ConfigLoader()

        dict1 = {"api": {"model": "gpt-4", "temperature": 0.5}}
        dict2 = {"api": {"temperature": None}}

        result = loader._deep_merge(dict1, dict2)
        # None values should not override
        assert result["api"]["temperature"] == 0.5

    def test_deep_merge_multiple(self):
        loader = ConfigLoader()

        dict1 = {"a": 1, "b": {"x": 1}}
        dict2 = {"b": {"y": 2}, "c": 3}
        dict3 = {"b": {"z": 3}, "d": 4}

        result = loader._deep_merge(dict1, dict2, dict3)
        assert result == {"a": 1, "b": {"x": 1, "y": 2, "z": 3}, "c": 3, "d": 4}

    def test_lookup_merge(self):
        loader = ConfigLoader()

        config1 = {"mcp": {"servers": {"server1": {}}}}
        config2 = {"mcp": {"servers": {"server2": {}}}}
        config3 = {"mcp": {"servers": {"server3": {}}}}

        # First found wins
        result = loader._lookup_merge("mcp", config1, config2, config3)
        assert "server1" in result["servers"]
        assert "server2" not in result["servers"]

    def test_lookup_merge_skip_none(self):
        loader = ConfigLoader()

        config1 = {"mcp": None}
        config2 = {"mcp": {"servers": {"server1": {}}}}

        result = loader._lookup_merge("mcp", config1, config2)
        assert "server1" in result["servers"]

    def test_lookup_merge_missing_key(self):
        loader = ConfigLoader()

        config1 = {"api": {}}
        config2 = {"tools": {}}

        result = loader._lookup_merge("mcp", config1, config2)
        assert result == {}

    def test_expand_env_vars_string(self):
        loader = ConfigLoader()

        os.environ["TEST_VAR"] = "test_value"
        result = loader._expand_env_vars("${TEST_VAR}")
        assert result == "test_value"

    def test_expand_env_vars_dict(self):
        loader = ConfigLoader()

        os.environ["API_KEY"] = "secret"
        obj = {"api": {"key": "${API_KEY}"}}
        result = loader._expand_env_vars(obj)
        assert result["api"]["key"] == "secret"

    def test_expand_env_vars_list(self):
        loader = ConfigLoader()

        os.environ["PATH1"] = "/path1"
        os.environ["PATH2"] = "/path2"
        obj = ["${PATH1}", "${PATH2}"]
        result = loader._expand_env_vars(obj)
        assert result == ["/path1", "/path2"]

    def test_expand_env_vars_tilde(self, tmp_path, monkeypatch):
        loader = ConfigLoader()

        monkeypatch.setenv("HOME", str(tmp_path))
        result = loader._expand_env_vars("~/test")
        assert result == str(tmp_path / "test")

    def test_expand_env_vars_nested(self):
        loader = ConfigLoader()

        os.environ["BASE"] = "/base"
        obj = {
            "paths": ["${BASE}/path1", "${BASE}/path2"],
            "config": {"root": "${BASE}"},
        }
        result = loader._expand_env_vars(obj)
        assert result["paths"] == ["/base/path1", "/base/path2"]
        assert result["config"]["root"] == "/base"

    def test_load_three_tier_merge(self, tmp_path, monkeypatch):
        # Set up three-tier config
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # System defaults
        system_dir = tmp_path / "system"
        system_dir.mkdir()
        (system_dir / "agents").mkdir()
        system_config = {"api": {"model": "claude-sonnet-4-5-20250929", "temperature": 0.5}}
        with open(system_dir / "agents" / "default.json", "w") as f:
            json.dump(system_config, f)

        # User config
        user_dir = tmp_path / ".leon"
        user_dir.mkdir()
        user_config = {"api": {"temperature": 0.7}, "memory": {"pruning": {"protect_recent": 15}}}
        with open(user_dir / "config.json", "w") as f:
            json.dump(user_config, f)

        # Project config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / ".leon").mkdir()
        project_config = {"api": {"model": "gpt-4"}}
        with open(project_dir / ".leon" / "config.json", "w") as f:
            json.dump(project_config, f)

        loader = ConfigLoader(workspace_root=str(project_dir))
        loader._system_defaults_dir = system_dir

        settings = loader.load()

        # Project overrides system
        assert settings.api.model == "gpt-4"
        # User overrides system
        assert settings.api.temperature == 0.7
        # User config preserved
        assert settings.memory.pruning.protect_recent == 15

    def test_load_cli_overrides(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        loader = ConfigLoader()
        loader._system_defaults_dir = tmp_path / "nonexistent"

        cli_overrides = {"api": {"model": "gpt-4-turbo", "temperature": 0.9}}

        settings = loader.load(cli_overrides=cli_overrides)
        assert settings.api.model == "gpt-4-turbo"
        assert settings.api.temperature == 0.9

    def test_load_validates_schema(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        # No API key set
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"]:
            monkeypatch.delenv(key, raising=False)

        loader = ConfigLoader()
        loader._system_defaults_dir = tmp_path / "nonexistent"

        with pytest.raises(Exception):  # Should raise validation error
            loader.load()

    def test_lookup_strategy_sandbox(self, tmp_path, monkeypatch):
        """Test lookup strategy for sandbox configs (first found wins)."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # User config with MCP
        user_dir = tmp_path / ".leon"
        user_dir.mkdir()
        user_config = {"mcp": {"servers": {"user_server": {"command": "user"}}}}
        with open(user_dir / "config.json", "w") as f:
            json.dump(user_config, f)

        # Project config with different MCP
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / ".leon").mkdir()
        project_config = {"mcp": {"servers": {"project_server": {"command": "project"}}}}
        with open(project_dir / ".leon" / "config.json", "w") as f:
            json.dump(project_config, f)

        loader = ConfigLoader(workspace_root=str(project_dir))
        loader._system_defaults_dir = tmp_path / "nonexistent"

        settings = loader.load()

        # Project should win (first found)
        assert "project_server" in settings.mcp.servers
        assert "user_server" not in settings.mcp.servers


class TestLoadConfigFunction:
    """Tests for load_config convenience function."""

    def test_load_config_basic(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        settings = load_config()
        assert isinstance(settings, LeonSettings)
        assert settings.api.api_key == "test-key"

    def test_load_config_with_workspace(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        settings = load_config(workspace_root=str(project_dir))
        assert isinstance(settings, LeonSettings)

    def test_load_config_with_overrides(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        cli_overrides = {"api": {"model": "custom-model"}}
        settings = load_config(cli_overrides=cli_overrides)
        assert settings.api.model == "custom-model"
