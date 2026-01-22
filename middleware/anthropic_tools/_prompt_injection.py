"""System prompt injection utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from langchain.agents.middleware.types import _ModelRequestOverrides
from langchain_core.messages import SystemMessage

if TYPE_CHECKING:
    from langchain.agents.middleware.types import ModelRequest


def inject_tool_and_prompt(
    request: ModelRequest,
    tool_type: str,
    tool_name: str,
    system_prompt: str | None = None,
) -> _ModelRequestOverrides:
    """Inject Anthropic tool descriptor and optional system prompt.

    Args:
        request: Original model request.
        tool_type: Tool type identifier.
        tool_name: Tool name.
        system_prompt: Optional system prompt to inject.

    Returns:
        Request overrides dict.
    """
    tools = [
        t
        for t in (request.tools or [])
        if getattr(t, "name", None) != tool_name
    ] + [{"type": tool_type, "name": tool_name}]

    overrides: _ModelRequestOverrides = {"tools": tools}

    if system_prompt:
        if request.system_message is not None:
            new_system_content = [
                *request.system_message.content_blocks,
                {"type": "text", "text": f"\n\n{system_prompt}"},
            ]
        else:
            new_system_content = [{"type": "text", "text": system_prompt}]
        new_system_message = SystemMessage(
            content=cast("list[str | dict[str, str]]", new_system_content)
        )
        overrides["system_message"] = new_system_message

    return overrides
