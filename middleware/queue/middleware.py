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
    # Fallback for environments without langchain
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

    Implements OpenClaw's "steer" queue mode behavior:
    - Check queue after each tool call
    - If steer message present, skip remaining tool calls with error message
    - Inject the steer message before next model call

    Flow:
    1. wrap_tool_call: After tool executes, check queue. If steer pending,
       mark that we need to inject and return skip message for remaining tools.
    2. before_model: If steer message pending, inject it into state.
    """

    def __init__(self):
        self._pending_steer: str | None = None

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage],
    ) -> ToolMessage:
        """
        Execute tool, then check for steer messages.
        If steer is pending, return skip message instead of executing.
        """
        queue_manager = get_queue_manager()

        # If we already have a pending steer, skip this tool call
        if self._pending_steer is not None:
            return ToolMessage(
                content="Skipped due to queued user message.",
                tool_call_id=request.tool_call.get("id", ""),
            )

        # Execute the tool
        result = handler(request)

        # After tool execution, check for steer messages
        steer_content = queue_manager.get_steer()
        if steer_content:
            self._pending_steer = steer_content

        return result

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage]],
    ) -> ToolMessage:
        """Async version of wrap_tool_call."""
        queue_manager = get_queue_manager()

        if self._pending_steer is not None:
            return ToolMessage(
                content="Skipped due to queued user message.",
                tool_call_id=request.tool_call.get("id", ""),
            )

        result = await handler(request)

        steer_content = queue_manager.get_steer()
        if steer_content:
            self._pending_steer = steer_content

        return result

    def before_model(
        self,
        state: Any,
        runtime: Any,
    ) -> dict[str, Any] | None:
        """
        Before model call, inject pending steer message if any.
        Returns state update dict to inject the message.
        """
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
        """Async version of before_model."""
        return self.before_model(state, runtime)
