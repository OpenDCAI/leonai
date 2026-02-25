"""Tests for model config enrichment (alias + context_limit)."""

import pytest
from pydantic import ValidationError

from config.models_schema import ActiveModel, ModelSpec, ModelsConfig
from core.monitor.cost import fetch_openrouter_pricing, get_model_context_limit
from core.monitor.middleware import MonitorMiddleware

# Ensure OpenRouter cache is populated (same as MonitorMiddleware.__init__)
fetch_openrouter_pricing()
SONNET_LIMIT = get_model_context_limit("claude-sonnet-4.5")
DEFAULT_LIMIT = 128000


class TestModelSpecFields:
    """ModelSpec 和 ActiveModel 支持 alias + context_limit 字段"""

    def test_model_spec_accepts_alias_and_context_limit(self):
        spec = ModelSpec(model="Alice", alias="claude-sonnet-4.5", context_limit=32768)
        assert spec.alias == "claude-sonnet-4.5"
        assert spec.context_limit == 32768

    def test_model_spec_defaults_none(self):
        spec = ModelSpec(model="Alice")
        assert spec.alias is None
        assert spec.context_limit is None

    def test_active_model_accepts_alias_and_context_limit(self):
        active = ActiveModel(model="Alice", alias="claude-sonnet-4.5", context_limit=32768)
        assert active.alias == "claude-sonnet-4.5"
        assert active.context_limit == 32768

    def test_context_limit_rejects_zero_or_negative(self):
        with pytest.raises(ValidationError):
            ModelSpec(model="x", context_limit=0)
        with pytest.raises(ValidationError):
            ModelSpec(model="x", context_limit=-1)


class TestResolveModelOverrides:
    """resolve_model 把 alias/context_limit 放入 overrides"""

    def test_virtual_model_passes_alias(self):
        config = ModelsConfig(mapping={
            "leon:custom": ModelSpec(model="Alice", alias="claude-sonnet-4.5")
        })
        name, overrides = config.resolve_model("leon:custom")
        assert name == "Alice"
        assert overrides["alias"] == "claude-sonnet-4.5"

    def test_virtual_model_passes_context_limit(self):
        config = ModelsConfig(mapping={
            "leon:custom": ModelSpec(model="Alice", context_limit=32768)
        })
        name, overrides = config.resolve_model("leon:custom")
        assert overrides["context_limit"] == 32768

    def test_non_virtual_model_passes_active_overrides(self):
        config = ModelsConfig(active=ActiveModel(
            model="Alice", alias="claude-sonnet-4.5", context_limit=32768
        ))
        name, overrides = config.resolve_model("Alice")
        assert name == "Alice"
        assert overrides["alias"] == "claude-sonnet-4.5"
        assert overrides["context_limit"] == 32768

    def test_non_virtual_no_active_returns_empty(self):
        config = ModelsConfig()
        name, overrides = config.resolve_model("Alice")
        assert name == "Alice"
        assert overrides == {}

    def test_non_virtual_active_no_alias_no_context_returns_empty(self):
        config = ModelsConfig(active=ActiveModel(model="Alice"))
        name, overrides = config.resolve_model("Alice")
        assert overrides == {}


class TestMonitorUpdateModel:
    """update_model 用 alias 查找 pricing 和 context_limit"""

    def test_update_model_with_alias(self):
        mw = MonitorMiddleware(model_name="claude-sonnet-4.5")
        mw.update_model("Alice", overrides={"alias": "claude-sonnet-4.5"})
        assert mw._context_monitor.context_limit == SONNET_LIMIT

    def test_update_model_with_explicit_context_limit(self):
        mw = MonitorMiddleware(model_name="claude-sonnet-4.5")
        mw.update_model("Alice", overrides={
            "alias": "claude-sonnet-4.5",
            "context_limit": 32768,
        })
        assert mw._context_monitor.context_limit == 32768

    def test_update_model_no_overrides_uses_model_name(self):
        mw = MonitorMiddleware(model_name="claude-sonnet-4.5")
        mw.update_model("claude-sonnet-4.5")
        assert mw._context_monitor.context_limit == SONNET_LIMIT

    def test_update_model_unknown_no_alias_gets_default(self):
        mw = MonitorMiddleware(model_name="claude-sonnet-4.5")
        mw.update_model("totally-unknown-model")
        assert mw._context_monitor.context_limit == DEFAULT_LIMIT

    def test_update_model_alias_affects_cost_calculator(self):
        mw = MonitorMiddleware(model_name="claude-sonnet-4.5")
        mw.update_model("Alice", overrides={"alias": "claude-sonnet-4.5"})
        assert mw._token_monitor.cost_calculator.costs != {}


class TestThreeLevelPriority:
    """Level 1 用户配置 > Level 2 OpenRouter > Level 3 Bundled"""

    def test_user_context_limit_overrides_lookup(self):
        mw = MonitorMiddleware(model_name="claude-sonnet-4.5")
        mw.update_model("Alice", overrides={
            "alias": "claude-sonnet-4.5",
            "context_limit": 32768,
        })
        assert mw._context_monitor.context_limit == 32768

    def test_alias_lookup_overrides_default(self):
        mw = MonitorMiddleware(model_name="gpt-4o")
        mw.update_model("MyModel", overrides={"alias": "claude-sonnet-4.5"})
        assert mw._context_monitor.context_limit == SONNET_LIMIT

    def test_no_alias_no_user_config_falls_to_default(self):
        mw = MonitorMiddleware(model_name="gpt-4o")
        mw.update_model("totally-unknown")
        assert mw._context_monitor.context_limit == DEFAULT_LIMIT
