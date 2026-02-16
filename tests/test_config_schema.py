"""Tests for config.schema module."""

import pytest
from pydantic import ValidationError

from config.schema import (
    APIConfig,
    LeonSettings,
    ModelSpec,
    ToolsConfig,
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


class TestAPIConfig:
    """Tests for APIConfig."""

    def test_default_config(self):
        config = APIConfig()
        assert config.model == "claude-sonnet-4-5-20250929"
        assert config.model_provider is None
        assert config.api_key is None
        assert config.base_url is None

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


class TestLeonSettings:
    """Tests for LeonSettings."""

    def test_default_settings(self, monkeypatch):
        # Set a dummy API key to pass validation
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
        # Clear all API key env vars
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"]:
            monkeypatch.delenv(key, raising=False)

        with pytest.raises(ValidationError, match="No API key found"):
            LeonSettings()

    def test_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
        settings = LeonSettings()
        assert settings.api.api_key == "test-anthropic-key"

    def test_env_var_nested(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("LEON__API__MODEL", "gpt-4")
        monkeypatch.setenv("LEON__API__TEMPERATURE", "0.7")

        settings = LeonSettings()
        assert settings.api.model == "gpt-4"
        assert settings.api.temperature == 0.7

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
        assert config.web.enabled is True  # Not disabled
