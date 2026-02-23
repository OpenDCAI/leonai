from decimal import Decimal

from core.monitor.cost import _parse_openrouter_model


def test_parse_openrouter_model_preserves_explicit_zero_cache_prices() -> None:
    model = {
        "id": "anthropic/claude-3.5-sonnet",
        "pricing": {
            "prompt": "0.000003",
            "completion": "0.000015",
            "input_cache_read": "0",
            "input_cache_write": "0",
        },
    }

    parsed = _parse_openrouter_model(model)
    assert parsed is not None
    _, costs = parsed
    assert costs["cache_read"] == Decimal("0")
    assert costs["cache_write"] == Decimal("0")


def test_parse_openrouter_model_infers_cache_prices_when_missing() -> None:
    model = {
        "id": "anthropic/claude-3.5-sonnet",
        "pricing": {
            "prompt": "0.000003",
            "completion": "0.000015",
        },
    }

    parsed = _parse_openrouter_model(model)
    assert parsed is not None
    _, costs = parsed
    assert costs["cache_read"] == Decimal("0.3")
    assert costs["cache_write"] == Decimal("3.75")
