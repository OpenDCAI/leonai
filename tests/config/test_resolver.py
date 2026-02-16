"""Tests for virtual model resolution in config.schema."""

import pytest
from pydantic import ValidationError

from config.schema import LeonSettings, ModelSpec


class TestModelResolution:
    """Tests for virtual model resolution."""

    def test_resolve_virtual_model_mini(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        settings = LeonSettings()

        model, kwargs = settings.resolve_model("leon:mini")

        assert model == "claude-haiku-4-5-20250929"
        assert kwargs["model_provider"] == "anthropic"
        assert "temperature" not in kwargs
        assert "max_tokens" not in kwargs

    def test_resolve_virtual_model_medium(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        settings = LeonSettings()

        model, kwargs = settings.resolve_model("leon:medium")

        assert model == "claude-sonnet-4-5-20250929"
        assert kwargs["model_provider"] == "anthropic"

    def test_resolve_virtual_model_large(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        settings = LeonSettings()

        model, kwargs = settings.resolve_model("leon:large")

        assert model == "claude-opus-4-6"
        assert kwargs["model_provider"] == "anthropic"

    def test_resolve_virtual_model_max(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        settings = LeonSettings()

        model, kwargs = settings.resolve_model("leon:max")

        assert model == "claude-opus-4-6"
        assert kwargs["model_provider"] == "anthropic"
        assert kwargs["temperature"] == 0.0

    def test_resolve_concrete_model(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        settings = LeonSettings()

        # Non-virtual models should pass through unchanged
        model, kwargs = settings.resolve_model("gpt-4")
        assert model == "gpt-4"
        assert kwargs == {}

        model, kwargs = settings.resolve_model("claude-opus-4-6")
        assert model == "claude-opus-4-6"
        assert kwargs == {}

        model, kwargs = settings.resolve_model("custom-model-name")
        assert model == "custom-model-name"
        assert kwargs == {}

    def test_resolve_unknown_virtual_model(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        settings = LeonSettings()

        with pytest.raises(ValueError) as exc_info:
            settings.resolve_model("leon:unknown")

        assert "Unknown virtual model" in str(exc_info.value)
        assert "leon:unknown" in str(exc_info.value)
        assert "leon:mini" in str(exc_info.value)  # Should list available models

    def test_resolve_model_with_custom_mapping(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Override default mapping
        settings = LeonSettings(
            model_mapping={
                "leon:custom": {
                    "model": "gpt-4-turbo",
                    "provider": "openai",
                    "temperature": 0.3,
                    "max_tokens": 8192,
                }
            }
        )

        model, kwargs = settings.resolve_model("leon:custom")

        assert model == "gpt-4-turbo"
        assert kwargs["model_provider"] == "openai"
        assert kwargs["temperature"] == 0.3
        assert kwargs["max_tokens"] == 8192

    def test_resolve_model_partial_spec(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Spec with only model and provider
        settings = LeonSettings(
            model_mapping={
                "leon:partial": {
                    "model": "gpt-3.5-turbo",
                    "provider": "openai",
                }
            }
        )

        model, kwargs = settings.resolve_model("leon:partial")

        assert model == "gpt-3.5-turbo"
        assert kwargs["model_provider"] == "openai"
        assert "temperature" not in kwargs
        assert "max_tokens" not in kwargs

    def test_resolve_model_no_provider(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Spec without provider
        settings = LeonSettings(
            model_mapping={
                "leon:noprovider": {
                    "model": "custom-model",
                    "temperature": 0.5,
                }
            }
        )

        model, kwargs = settings.resolve_model("leon:noprovider")

        assert model == "custom-model"
        assert "model_provider" not in kwargs
        assert kwargs["temperature"] == 0.5

    def test_model_spec_validation(self):
        # Valid spec
        spec = ModelSpec(model="gpt-4", provider="openai")
        assert spec.model == "gpt-4"
        assert spec.provider == "openai"

        # Temperature out of range
        with pytest.raises(ValidationError):
            ModelSpec(model="gpt-4", temperature=-0.1)

        with pytest.raises(ValidationError):
            ModelSpec(model="gpt-4", temperature=2.1)

        # Max tokens validation
        with pytest.raises(ValidationError):
            ModelSpec(model="gpt-4", max_tokens=0)

        with pytest.raises(ValidationError):
            ModelSpec(model="gpt-4", max_tokens=-100)

    def test_model_mapping_inheritance(self, monkeypatch):
        """Test that custom model mapping extends default mapping."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Add custom mapping while keeping defaults
        settings = LeonSettings(
            model_mapping={
                "leon:mini": {"model": "claude-haiku-4-5-20250929", "provider": "anthropic"},
                "leon:medium": {"model": "claude-sonnet-4-5-20250929", "provider": "anthropic"},
                "leon:large": {"model": "claude-opus-4-6", "provider": "anthropic"},
                "leon:max": {"model": "claude-opus-4-6", "provider": "anthropic", "temperature": 0.0},
                "leon:custom": {"model": "gpt-4", "provider": "openai"},
            }
        )

        # Default mappings should still work
        model, _ = settings.resolve_model("leon:mini")
        assert model == "claude-haiku-4-5-20250929"

        # Custom mapping should work
        model, kwargs = settings.resolve_model("leon:custom")
        assert model == "gpt-4"
        assert kwargs["model_provider"] == "openai"

    def test_resolve_model_case_sensitive(self, monkeypatch):
        """Test that model names are case-sensitive."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        settings = LeonSettings()

        # Should work
        model, _ = settings.resolve_model("leon:mini")
        assert model == "claude-haiku-4-5-20250929"

        # Wrong case should raise error (virtual models are case-sensitive)
        with pytest.raises(ValueError, match="Unknown virtual model: leon:Mini"):
            settings.resolve_model("leon:Mini")

        # Different prefix is not a virtual model, passes through
        model, kwargs = settings.resolve_model("LEON:mini")
        assert model == "LEON:mini"
        assert kwargs == {}

    def test_resolve_model_empty_kwargs(self, monkeypatch):
        """Test that empty kwargs dict is returned for concrete models."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        settings = LeonSettings()

        model, kwargs = settings.resolve_model("gpt-4")

        assert isinstance(kwargs, dict)
        assert len(kwargs) == 0

    def test_model_spec_all_fields(self):
        """Test ModelSpec with all fields populated."""
        spec = ModelSpec(
            model="claude-opus-4-6",
            provider="anthropic",
            temperature=0.7,
            max_tokens=4096,
        )

        assert spec.model == "claude-opus-4-6"
        assert spec.provider == "anthropic"
        assert spec.temperature == 0.7
        assert spec.max_tokens == 4096

    def test_model_spec_minimal(self):
        """Test ModelSpec with only required field."""
        spec = ModelSpec(model="gpt-4")

        assert spec.model == "gpt-4"
        assert spec.provider is None
        assert spec.temperature is None
        assert spec.max_tokens is None

    def test_resolve_model_with_colon_in_name(self, monkeypatch):
        """Test that only leon: prefix triggers virtual resolution."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        settings = LeonSettings()

        # Should not be treated as virtual model
        model, kwargs = settings.resolve_model("openai:gpt-4")
        assert model == "openai:gpt-4"
        assert kwargs == {}

        model, kwargs = settings.resolve_model("anthropic:claude-3")
        assert model == "anthropic:claude-3"
        assert kwargs == {}
