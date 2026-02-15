"""Model resolver for virtual model names (leon:*).

This module provides a ModelResolver class that:
- Resolves virtual model names (leon:mini/medium/large/max) to concrete models
- Merges global settings with model-specific overrides
- Returns complete config dict compatible with init_chat_model()
"""

from __future__ import annotations

from typing import Any

from config.schema import LeonSettings


class ModelResolver:
    """Resolver for virtual model names to concrete model configurations.

    Supports both virtual (leon:*) and concrete model names.
    Virtual models are resolved using settings.model_mapping.
    Global settings (temperature, max_tokens) are inherited if not overridden.
    """

    def __init__(self, settings: LeonSettings):
        """Initialize resolver with settings.

        Args:
            settings: Leon settings containing model_mapping and global API config
        """
        self.settings = settings

    def resolve(self, model_name: str) -> dict[str, Any]:
        """Resolve model name to complete config dict.

        Args:
            model_name: Model name (can be leon:* virtual name or concrete model)

        Returns:
            Config dict with keys: model, model_provider, api_key, base_url,
            temperature, max_tokens, model_kwargs

        Raises:
            ValueError: If virtual model name not found in mapping
        """
        # Resolve virtual model name
        actual_model, model_overrides = self.settings.resolve_model(model_name)

        # Build complete config
        return self._build_config(actual_model, model_overrides)

    def _build_config(self, model: str, overrides: dict[str, Any]) -> dict[str, Any]:
        """Build complete model config by merging global settings with overrides.

        Args:
            model: Actual model name
            overrides: Model-specific overrides (provider, temperature, max_tokens)

        Returns:
            Complete config dict compatible with init_chat_model()
        """
        config: dict[str, Any] = {
            "model": model,
        }

        # Add provider (override takes precedence)
        if "model_provider" in overrides:
            config["model_provider"] = overrides["model_provider"]
        elif self.settings.api.model_provider:
            config["model_provider"] = self.settings.api.model_provider

        # Add API credentials
        if self.settings.api.api_key:
            config["api_key"] = self.settings.api.api_key
        if self.settings.api.base_url:
            config["base_url"] = self.settings.api.base_url

        # Add temperature (override takes precedence)
        if "temperature" in overrides:
            config["temperature"] = overrides["temperature"]
        elif self.settings.api.temperature is not None:
            config["temperature"] = self.settings.api.temperature

        # Add max_tokens (override takes precedence)
        if "max_tokens" in overrides:
            config["max_tokens"] = overrides["max_tokens"]
        elif self.settings.api.max_tokens is not None:
            config["max_tokens"] = self.settings.api.max_tokens

        # Add extra model_kwargs
        if self.settings.api.model_kwargs:
            config["model_kwargs"] = self.settings.api.model_kwargs.copy()

        return config


# Global resolver instance (initialized on first import)
_resolver: ModelResolver | None = None


def get_resolver(settings: LeonSettings | None = None) -> ModelResolver:
    """Get or create global resolver instance.

    Args:
        settings: Optional settings to initialize resolver.
                 If None, uses existing resolver or raises error.

    Returns:
        Global ModelResolver instance

    Raises:
        RuntimeError: If resolver not initialized and settings not provided
    """
    global _resolver

    if settings is not None:
        _resolver = ModelResolver(settings)

    if _resolver is None:
        raise RuntimeError("ModelResolver not initialized. Call get_resolver(settings) first.")

    return _resolver


def resolve_model(model_name: str) -> dict[str, Any]:
    """Convenience function to resolve model using global resolver.

    Args:
        model_name: Model name (can be leon:* virtual name)

    Returns:
        Complete config dict compatible with init_chat_model()

    Raises:
        RuntimeError: If resolver not initialized
        ValueError: If virtual model name not found
    """
    return get_resolver().resolve(model_name)
