"""Model resolver for virtual model names (leon:*).

Resolves virtual model names using ModelsConfig from models.json.
"""

from __future__ import annotations

from typing import Any

from config.models_schema import ModelsConfig


class ModelResolver:
    """Resolver for virtual model names to concrete model configurations."""

    def __init__(self, models_config: ModelsConfig):
        self.models_config = models_config

    def resolve(self, model_name: str) -> dict[str, Any]:
        """Resolve model name to complete config dict."""
        actual_model, model_overrides = self.models_config.resolve_model(model_name)
        return self._build_config(actual_model, model_overrides)

    def _build_config(self, model: str, overrides: dict[str, Any]) -> dict[str, Any]:
        """Build complete model config by merging global settings with overrides."""
        config: dict[str, Any] = {"model": model}

        # Provider (override takes precedence)
        if "model_provider" in overrides:
            config["model_provider"] = overrides["model_provider"]
        else:
            provider = self.models_config.get_model_provider()
            if provider:
                config["model_provider"] = provider

        # API credentials
        api_key = self.models_config.get_api_key()
        if api_key:
            config["api_key"] = api_key

        base_url = self.models_config.get_base_url()
        if base_url:
            config["base_url"] = base_url

        # Temperature / max_tokens from overrides
        if "temperature" in overrides:
            config["temperature"] = overrides["temperature"]
        if "max_tokens" in overrides:
            config["max_tokens"] = overrides["max_tokens"]

        return config


_resolver: ModelResolver | None = None


def get_resolver(models_config: ModelsConfig | None = None) -> ModelResolver:
    """Get or create global resolver instance."""
    global _resolver

    if models_config is not None:
        _resolver = ModelResolver(models_config)

    if _resolver is None:
        raise RuntimeError("ModelResolver not initialized. Call get_resolver(models_config) first.")

    return _resolver


def resolve_model(model_name: str) -> dict[str, Any]:
    """Convenience function to resolve model using global resolver."""
    return get_resolver().resolve(model_name)
