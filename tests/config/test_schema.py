"""Comprehensive tests for config.schema module."""

import pytest
from pydantic import ValidationError

from config.schema import (
    APIConfig,
    CommandConfig,
    CompactionConfig,
    FileSystemConfig,
    LeonSettings,
    MCPConfig,
    MCPServerConfig,
    MemoryConfig,
    ModelSpec,
    PruningConfig,
    SearchConfig,
    SkillsConfig,
    ToolsConfig,
    WebConfig,
)


class TestModelSpec:
    """Tests for ModelSpec."""

    def test_basic_spec(self):
        spec = ModelSpec(model="gpt-4")
        assert spec.model == "gpt-4"
        assert spec.provider is None
        assert spec.temperature is None
        assert spec.max_tokens is None

    def test_full_spec(self):
        spec = ModelSpec(
            model="claude-opus-4-6",
            provider="anthropic",
            temperature=0.5,
            max_tokens=4096,
        )
        assert spec.model == "claude-opus-4-6"
        assert spec.provider == "anthropic"
        assert spec.temperature == 0.5
        assert spec.max_tokens == 4096

    def test_temperature_validation(self):
        with pytest.raises(ValidationError):
            ModelSpec(model="gpt-4", temperature=-0.1)
        with pytest.raises(ValidationError):
            ModelSpec(model="gpt-4", temperature=2.1)

    def test_max_tokens_validation(self):
        with pytest.raises(ValidationError):
            ModelSpec(model="gpt-4", max_tokens=0)
        with pytest.raises(ValidationError):
            ModelSpec(model="gpt-4", max_tokens=-1)

    def test_temperature_boundary(self):
        # Test boundary values
        spec = ModelSpec(model="gpt-4", temperature=0.0)
        assert spec.temperature == 0.0
        spec = ModelSpec(model="gpt-4", temperature=2.0)
        assert spec.temperature == 2.0


class TestAPIConfig:
    """Tests for APIConfig."""

    def test_default_config(self):
        config = APIConfig()
        assert config.model == "claude-sonnet-4-5-20250929"
        assert config.model_provider is None
        assert config.api_key is None
        assert config.base_url is None
        assert config.temperature is None
        assert config.max_tokens is None
        assert config.model_kwargs == {}
        assert config.context_limit == 100000
        assert config.enable_audit_log is True
        assert config.allowed_extensions is None
        assert config.block_dangerous_commands is True
        assert config.block_network_commands is False
        assert config.queue_mode == "steer"

    def test_base_url_normalization(self):
        # Should add /v1
        config = APIConfig(base_url="https://api.openai.com")
        assert config.base_url == "https://api.openai.com/v1"

        # Should not modify if already has /v1
        config = APIConfig(base_url="https://api.openai.com/v1")
        assert config.base_url == "https://api.openai.com/v1"

        # Should not modify if has /v1/ in middle
        config = APIConfig(base_url="https://api.openai.com/v1/engines")
        assert config.base_url == "https://api.openai.com/v1/engines"

        # Should strip trailing slash
        config = APIConfig(base_url="https://api.openai.com/")
        assert config.base_url == "https://api.openai.com/v1"

        # Should handle None
        config = APIConfig(base_url=None)
        assert config.base_url is None

    def test_custom_model_kwargs(self):
        config = APIConfig(model_kwargs={"top_p": 0.9, "frequency_penalty": 0.5})
        assert config.model_kwargs["top_p"] == 0.9
        assert config.model_kwargs["frequency_penalty"] == 0.5

    def test_queue_mode_values(self):
        for mode in ["steer", "followup", "collect", "steer_backlog", "interrupt"]:
            config = APIConfig(queue_mode=mode)
            assert config.queue_mode == mode


class TestMemoryConfig:
    """Tests for MemoryConfig."""

    def test_default_pruning(self):
        config = PruningConfig()
        assert config.enabled is True
        assert config.soft_trim_chars == 3000
        assert config.hard_clear_threshold == 10000
        assert config.protect_recent == 3
        assert config.trim_tool_results is True

    def test_custom_pruning(self):
        config = PruningConfig(
            enabled=False,
            soft_trim_chars=5000,
            hard_clear_threshold=20000,
            protect_recent=5,
            trim_tool_results=False,
        )
        assert config.enabled is False
        assert config.soft_trim_chars == 5000
        assert config.hard_clear_threshold == 20000
        assert config.protect_recent == 5
        assert config.trim_tool_results is False

    def test_default_compaction(self):
        config = CompactionConfig()
        assert config.enabled is True
        assert config.reserve_tokens == 16384
        assert config.keep_recent_tokens == 20000
        assert config.min_messages == 20

    def test_custom_compaction(self):
        config = CompactionConfig(
            enabled=False,
            reserve_tokens=8192,
            keep_recent_tokens=10000,
            min_messages=30,
        )
        assert config.enabled is False
        assert config.reserve_tokens == 8192
        assert config.keep_recent_tokens == 10000
        assert config.min_messages == 30

    def test_memory_config_nested(self):
        config = MemoryConfig(
            pruning={"protect_recent": 15},
            compaction={"reserve_tokens": 8192},
        )
        assert config.pruning.protect_recent == 15
        assert config.compaction.reserve_tokens == 8192


class TestToolsConfig:
    """Tests for ToolsConfig."""

    def test_default_tools_config(self):
        config = ToolsConfig()

        assert config.filesystem.enabled is True
        assert config.filesystem.tools.read_file.enabled is True
        assert config.filesystem.tools.read_file.max_file_size == 10485760

        assert config.search.enabled is True
        assert config.search.max_results == 50

        assert config.web.enabled is True
        assert config.web.timeout == 15

        assert config.command.enabled is True
        assert config.command.tools.run_command.default_timeout == 120

    def test_disable_tools(self):
        config = ToolsConfig(
            filesystem={"enabled": False},
            search={"enabled": False},
        )

        assert config.filesystem.enabled is False
        assert config.search.enabled is False
        assert config.web.enabled is True

    def test_filesystem_config(self):
        config = FileSystemConfig(
            enabled=False,
            tools={
                "read_file": {"max_file_size": 5000000},
                "write_file": False,
            },
        )
        assert config.enabled is False
        assert config.tools.read_file.max_file_size == 5000000
        assert config.tools.write_file is False

    def test_search_config(self):
        config = SearchConfig(
            enabled=True,
            max_results=100,
            tools={"grep_search": {"max_file_size": 20000000}},
        )
        assert config.max_results == 100
        assert config.tools.grep_search.max_file_size == 20000000

    def test_web_config(self):
        config = WebConfig(
            timeout=30,
            tools={
                "web_search": {
                    "max_results": 10,
                    "tavily_api_key": "test-key",
                }
            },
        )
        assert config.timeout == 30
        assert config.tools.web_search.max_results == 10
        assert config.tools.web_search.tavily_api_key == "test-key"

    def test_command_config(self):
        config = CommandConfig(
            enabled=True,
            tools={"run_command": {"default_timeout": 300}},
        )
        assert config.tools.run_command.default_timeout == 300


class TestMCPConfig:
    """Tests for MCPConfig."""

    def test_default_mcp_config(self):
        config = MCPConfig()
        assert config.enabled is True
        assert config.servers == {}

    def test_mcp_server_config(self):
        server = MCPServerConfig(
            command="python",
            args=["-m", "mcp_server"],
            env={"API_KEY": "test"},
        )
        assert server.command == "python"
        assert server.args == ["-m", "mcp_server"]
        assert server.env == {"API_KEY": "test"}

    def test_mcp_with_servers(self):
        config = MCPConfig(
            servers={
                "test_server": {
                    "command": "node",
                    "args": ["server.js"],
                    "env": {"PORT": "3000"},
                }
            }
        )
        assert "test_server" in config.servers
        assert config.servers["test_server"].command == "node"


class TestSkillsConfig:
    """Tests for SkillsConfig."""

    def test_default_skills_config(self):
        config = SkillsConfig()
        assert config.enabled is True
        assert config.paths == ["./skills"]
        assert config.skills == {}

    def test_custom_skills_config(self, tmp_path):
        # Create test directories
        skill_dir1 = tmp_path / "custom_skills"
        skill_dir1.mkdir()
        skill_dir2 = tmp_path / "more_skills"
        skill_dir2.mkdir()

        config = SkillsConfig(
            enabled=False,
            paths=[str(skill_dir1), str(skill_dir2)],
            skills={"skill1": True, "skill2": False},
        )
        assert config.enabled is False
        assert len(config.paths) == 2
        assert config.skills["skill1"] is True
        assert config.skills["skill2"] is False


class TestLeonSettings:
    """Tests for LeonSettings."""

    def test_default_settings(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        settings = LeonSettings()

        assert settings.api.model == "claude-sonnet-4-5-20250929"
        assert settings.api.api_key == "test-key"
        assert settings.memory.pruning.enabled is True
        assert settings.tools.filesystem.enabled is True
        assert settings.mcp.enabled is True
        assert settings.skills.enabled is True

    def test_model_mapping(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        settings = LeonSettings()

        assert "leon:mini" in settings.model_mapping
        assert "leon:medium" in settings.model_mapping
        assert "leon:large" in settings.model_mapping
        assert "leon:max" in settings.model_mapping

        assert settings.model_mapping["leon:mini"].model == "claude-haiku-4-5-20250929"
        assert settings.model_mapping["leon:medium"].model == "claude-sonnet-4-5-20250929"
        assert settings.model_mapping["leon:large"].model == "claude-opus-4-6"
        assert settings.model_mapping["leon:max"].model == "claude-opus-4-6"
        assert settings.model_mapping["leon:max"].temperature == 0.0

    def test_resolve_model_virtual(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        settings = LeonSettings()

        model, kwargs = settings.resolve_model("leon:mini")
        assert model == "claude-haiku-4-5-20250929"
        assert kwargs["model_provider"] == "anthropic"

        model, kwargs = settings.resolve_model("leon:max")
        assert model == "claude-opus-4-6"
        assert kwargs["temperature"] == 0.0
        assert kwargs["model_provider"] == "anthropic"

    def test_resolve_model_direct(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        settings = LeonSettings()

        model, kwargs = settings.resolve_model("gpt-4")
        assert model == "gpt-4"
        assert kwargs == {}

    def test_resolve_model_unknown(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        settings = LeonSettings()

        with pytest.raises(ValueError, match="Unknown virtual model"):
            settings.resolve_model("leon:unknown")

    def test_api_key_validation_missing(self, monkeypatch):
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"]:
            monkeypatch.delenv(key, raising=False)

        with pytest.raises(ValidationError, match="No API key found"):
            LeonSettings()

    def test_api_key_from_env_openai(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
        settings = LeonSettings()
        assert settings.api.api_key == "test-openai-key"

    def test_api_key_from_env_anthropic(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
        settings = LeonSettings()
        assert settings.api.api_key == "test-anthropic-key"

    def test_api_key_from_env_openrouter(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
        settings = LeonSettings()
        assert settings.api.api_key == "test-openrouter-key"

    def test_api_key_priority(self, monkeypatch):
        # Explicit api_key should override env vars
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        settings = LeonSettings(api={"api_key": "explicit-key"})
        assert settings.api.api_key == "explicit-key"

    def test_env_var_nested(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("LEON__API__MODEL", "gpt-4")
        monkeypatch.setenv("LEON__API__TEMPERATURE", "0.7")
        monkeypatch.setenv("LEON__MEMORY__PRUNING__PROTECT_RECENT", "20")

        settings = LeonSettings()
        assert settings.api.model == "gpt-4"
        assert settings.api.temperature == 0.7
        assert settings.memory.pruning.protect_recent == 20

    def test_workspace_root_validation(self, monkeypatch, tmp_path):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Valid directory
        settings = LeonSettings(workspace_root=str(tmp_path))
        assert settings.workspace_root == str(tmp_path)

        # Non-existent directory
        with pytest.raises(ValidationError, match="does not exist"):
            LeonSettings(workspace_root="/nonexistent/path")

        # File instead of directory
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")
        with pytest.raises(ValidationError, match="not a directory"):
            LeonSettings(workspace_root=str(file_path))

    def test_workspace_root_expansion(self, monkeypatch, tmp_path):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("HOME", str(tmp_path))

        # Create a test directory
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        # Test ~ expansion
        settings = LeonSettings(workspace_root="~/test")
        assert settings.workspace_root == str(test_dir)

    def test_custom_system_prompt(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        settings = LeonSettings(system_prompt="Custom prompt")
        assert settings.system_prompt == "Custom prompt"

    def test_nested_config_groups(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        settings = LeonSettings(
            api={"model": "gpt-4", "temperature": 0.5},
            memory={"pruning": {"protect_recent": 15}},
            tools={"filesystem": {"enabled": False}},
        )
        assert settings.api.model == "gpt-4"
        assert settings.api.temperature == 0.5
        assert settings.memory.pruning.protect_recent == 15
        assert settings.tools.filesystem.enabled is False

    def test_custom_model_mapping(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        settings = LeonSettings(
            model_mapping={
                "leon:custom": {
                    "model": "gpt-4-turbo",
                    "provider": "openai",
                    "temperature": 0.3,
                }
            }
        )
        assert "leon:custom" in settings.model_mapping
        model, kwargs = settings.resolve_model("leon:custom")
        assert model == "gpt-4-turbo"
        assert kwargs["model_provider"] == "openai"
        assert kwargs["temperature"] == 0.3
