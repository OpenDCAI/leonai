"""Steering Middleware - injects queued messages before model calls"""

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
    """
    Middleware that checks for steer messages after each tool call.

    Flow:
    1. After tool executes, check queue for steer messages
    2. If steer found, skip remaining tool calls
    3. Before next model call, inject steer message
    """

    def __init__(self):
        self._pending_steer: str | None = None

    def _handle_tool_call(
        self,
        request: ToolCallRequest,
        result: ToolMessage,
    ) -> ToolMessage:
        """Common logic for checking steer after tool execution"""
        if self._pending_steer is None:
            steer_content = get_queue_manager().get_steer()
            if steer_content:
                self._pending_steer = steer_content
        return result

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage],
    ) -> ToolMessage:
        """Execute tool and check for steer messages"""
        if self._pending_steer is not None:
            return ToolMessage(
                content="Skipped due to queued user message.",
                tool_call_id=request.tool_call.get("id", ""),
            )

        result = handler(request)
        return self._handle_tool_call(request, result)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage]],
    ) -> ToolMessage:
        """Async version of wrap_tool_call"""
        if self._pending_steer is not None:
            return ToolMessage(
                content="Skipped due to queued user message.",
                tool_call_id=request.tool_call.get("id", ""),
            )

        result = await handler(request)
        return self._handle_tool_call(request, result)

    def before_model(
        self,
        state: Any,
        runtime: Any,
    ) -> dict[str, Any] | None:
        """Inject pending steer message before model call"""
        if self._pending_steer is not None:
            steer_msg = HumanMessage(content=f"[STEER] {self._pending_steer}")
            self._pending_steer = None
            return {"messages": [steer_msg]}
        return None

    async def abefore_model(
        self,
        state: Any,
        runtime: Any,
    ) -> dict[str, Any] | None:
        """Async version of before_model"""
        return self.before_model(state, runtime)
