"""Steering Middleware - injects queued messages before model calls (non-preemptive)

Tool calls are never skipped. All pending steer messages are drained and
injected as HumanMessage(metadata={"source": "system"}) before the next LLM call.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.messages import HumanMessage, ToolMessage

try:
    from langchain.agents.middleware.types import (
        AgentMiddleware,
        ModelCallResult,
        ModelRequest,
        ModelResponse,
        ToolCallRequest,
    )
except ImportError:

    class AgentMiddleware:
        pass

    ModelRequest = Any
    ModelResponse = Any
    ModelCallResult = Any
    ToolCallRequest = Any

from .manager import get_queue_manager


class SteeringMiddleware(AgentMiddleware):
    """Non-preemptive steering: let all tool calls finish, inject before next LLM call.

    Flow:
    1. Tool calls execute normally (no skipping)
    2. Before next model call, drain ALL pending steer messages
    3. Inject as HumanMessage with metadata source="system"
    """

    def _get_thread_id(self) -> str | None:
        try:
            from langgraph.config import get_config

            return get_config().get("configurable", {}).get("thread_id")
        except Exception:
            return None

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage],
    ) -> ToolMessage:
        """Pure passthrough — never skip tool calls."""
        return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage]],
    ) -> ToolMessage:
        """Async pure passthrough — never skip tool calls."""
        return await handler(request)

    def before_model(
        self,
        state: Any,
        runtime: Any,
    ) -> dict[str, Any] | None:
        """Drain all pending steer messages and inject before model call."""
        thread_id = self._get_thread_id()
        if not thread_id:
            return None

        items = get_queue_manager().drain_steer(thread_id)
        if not items:
            return None

        messages = [
            HumanMessage(content=item, metadata={"source": "system"})
            for item in items
        ]
        return {"messages": messages}

    async def abefore_model(
        self,
        state: Any,
        runtime: Any,
    ) -> dict[str, Any] | None:
        """Async version of before_model."""
        return self.before_model(state, runtime)
