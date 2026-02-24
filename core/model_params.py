"""Model parameter normalization for provider/model-specific compatibility."""

from __future__ import annotations

from typing import Any


def normalize_model_kwargs(model_name: str, model_kwargs: dict[str, Any]) -> dict[str, Any]:
    """Return model kwargs normalized for the target model/provider behavior."""
    kwargs = dict(model_kwargs)
    provider = str(kwargs.get("model_provider") or "").strip().lower()
    name = (model_name or "").strip().lower()

    # @@@openai-gpt5-token-param - OpenAI GPT-5 chat completions reject max_tokens and require max_completion_tokens.
    if provider == "openai" and _is_openai_gpt5(name):
        if "max_completion_tokens" not in kwargs and "max_tokens" in kwargs:
            kwargs["max_completion_tokens"] = kwargs["max_tokens"]
        kwargs.pop("max_tokens", None)

    return kwargs


def _is_openai_gpt5(model_name: str) -> bool:
    bare_name = model_name.split("/")[-1]
    return bare_name.startswith("gpt-5")


# ---------------------------------------------------------------------------
# @@@langchain-anthropic-streaming-usage-regression
# langchain-anthropic >= 1.0 dropped usage extraction from message_start,
# assuming message_delta carries complete info. But Anthropic API only puts
# input_tokens (+ cache tokens) in message_start and output_tokens in
# message_delta. This patch restores the v0.2.4 behavior.
# Upstream issue: https://github.com/langchain-ai/langchain/issues/XXXXX
# Remove this once upstream is fixed.
# ---------------------------------------------------------------------------

_patched = False


def patch_anthropic_streaming_usage() -> None:
    """Restore input-token extraction from message_start in streaming."""
    global _patched
    if _patched:
        return

    try:
        import langchain_anthropic.chat_models as mod
    except ImportError:
        return

    original = mod._make_message_chunk_from_anthropic_event

    def _patched_make_chunk(
        event: Any,
        *,
        stream_usage: bool = True,
        coerce_content_to_string: bool = True,
        block_start_event: Any = None,
    ) -> tuple:
        msg, block = original(
            event,
            stream_usage=stream_usage,
            coerce_content_to_string=coerce_content_to_string,
            block_start_event=block_start_event,
        )
        # Inject usage from message_start (where Anthropic reports input_tokens)
        if (
            stream_usage
            and event.type == "message_start"
            and msg is not None
            and not msg.usage_metadata
            and hasattr(event.message, "usage")
        ):
            msg.usage_metadata = mod._create_usage_metadata(event.message.usage)
        return msg, block

    mod._make_message_chunk_from_anthropic_event = _patched_make_chunk
    _patched = True
