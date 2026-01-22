"""Base middleware classes for Anthropic tools."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain.agents.middleware.types import AgentMiddleware
from langchain.tools import ToolRuntime, tool
from langgraph.types import Command

from . import _filesystem_handlers as fs_handlers
from . import _state_handlers as state_handlers
from ._prompt_injection import inject_tool_and_prompt
from ._types import AnthropicToolsState

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

    from langchain.agents.middleware.types import ModelRequest, ModelResponse


class StateClaudeFileToolMiddleware(AgentMiddleware):
    """Base class for state-based file tool middleware."""

    state_schema = AnthropicToolsState

    def __init__(
        self,
        *,
        tool_type: str,
        tool_name: str,
        state_key: str,
        allowed_path_prefixes: Sequence[str] | None = None,
        system_prompt: str | None = None,
    ) -> None:
        """Initialize.

        Args:
            tool_type: Tool type identifier.
            tool_name: Tool name.
            state_key: State key for file storage.
            allowed_path_prefixes: Optional list of allowed path prefixes.
            system_prompt: Optional system prompt to inject.
        """
        self.tool_type = tool_type
        self.tool_name = tool_name
        self.state_key = state_key
        self.allowed_prefixes = allowed_path_prefixes
        self.system_prompt = system_prompt

        @tool(tool_name)
        def file_tool(
            runtime: ToolRuntime[None, AnthropicToolsState],
            command: str,
            path: str,
            file_text: str | None = None,
            old_str: str | None = None,
            new_str: str | None = None,
            insert_line: int | None = None,
            new_path: str | None = None,
            view_range: list[int] | None = None,
        ) -> Command | str:
            """Execute file operations on virtual file system."""
            args: dict[str, Any] = {"path": path}
            if file_text is not None:
                args["file_text"] = file_text
            if old_str is not None:
                args["old_str"] = old_str
            if new_str is not None:
                args["new_str"] = new_str
            if insert_line is not None:
                args["insert_line"] = insert_line
            if new_path is not None:
                args["new_path"] = new_path
            if view_range is not None:
                args["view_range"] = view_range

            handler_kwargs = {
                "args": args,
                "state": runtime.state,
                "tool_call_id": runtime.tool_call_id,
                "tool_name": self.tool_name,
                "state_key": self.state_key,
                "allowed_prefixes": self.allowed_prefixes,
            }

            try:
                if command == "view":
                    return state_handlers.handle_view(**handler_kwargs)
                if command == "create":
                    return state_handlers.handle_create(**handler_kwargs)
                if command == "str_replace":
                    return state_handlers.handle_str_replace(**handler_kwargs)
                if command == "insert":
                    return state_handlers.handle_insert(**handler_kwargs)
                if command == "delete":
                    return state_handlers.handle_delete(**handler_kwargs)
                if command == "rename":
                    return state_handlers.handle_rename(**handler_kwargs)
                return f"Unknown command: {command}"
            except (ValueError, FileNotFoundError) as e:
                return str(e)

        self.tools = [file_tool]

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Inject Anthropic tool descriptor and optional system prompt."""
        overrides = inject_tool_and_prompt(
            request, self.tool_type, self.tool_name, self.system_prompt
        )
        return handler(request.override(**overrides))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Inject Anthropic tool descriptor and optional system prompt."""
        overrides = inject_tool_and_prompt(
            request, self.tool_type, self.tool_name, self.system_prompt
        )
        return await handler(request.override(**overrides))


class FilesystemClaudeFileToolMiddleware(AgentMiddleware):
    """Base class for filesystem-based file tool middleware."""

    def __init__(
        self,
        *,
        tool_type: str,
        tool_name: str,
        root_path: str,
        allowed_prefixes: list[str] | None = None,
        max_file_size_mb: int = 10,
        system_prompt: str | None = None,
    ) -> None:
        """Initialize.

        Args:
            tool_type: Tool type identifier.
            tool_name: Tool name.
            root_path: Root directory for file operations.
            allowed_prefixes: Optional list of allowed virtual path prefixes.
            max_file_size_mb: Maximum file size in MB.
            system_prompt: Optional system prompt to inject.
        """
        self.tool_type = tool_type
        self.tool_name = tool_name
        self.root_path = Path(root_path).resolve()
        self.allowed_prefixes = allowed_prefixes or ["/"]
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.system_prompt = system_prompt

        self.root_path.mkdir(parents=True, exist_ok=True)

        @tool(tool_name)
        def file_tool(
            runtime: ToolRuntime,
            command: str,
            path: str,
            file_text: str | None = None,
            old_str: str | None = None,
            new_str: str | None = None,
            insert_line: int | None = None,
            new_path: str | None = None,
            view_range: list[int] | None = None,
        ) -> Command | str:
            """Execute file operations on filesystem."""
            args: dict[str, Any] = {"path": path}
            if file_text is not None:
                args["file_text"] = file_text
            if old_str is not None:
                args["old_str"] = old_str
            if new_str is not None:
                args["new_str"] = new_str
            if insert_line is not None:
                args["insert_line"] = insert_line
            if new_path is not None:
                args["new_path"] = new_path
            if view_range is not None:
                args["view_range"] = view_range

            handler_kwargs = {
                "args": args,
                "tool_call_id": runtime.tool_call_id,
                "tool_name": self.tool_name,
                "root_path": self.root_path,
                "allowed_prefixes": self.allowed_prefixes,
            }

            try:
                if command == "view":
                    return fs_handlers.handle_view(
                        **handler_kwargs, max_file_size_bytes=self.max_file_size_bytes
                    )
                if command == "create":
                    return fs_handlers.handle_create(**handler_kwargs)
                if command == "str_replace":
                    return fs_handlers.handle_str_replace(**handler_kwargs)
                if command == "insert":
                    return fs_handlers.handle_insert(**handler_kwargs)
                if command == "delete":
                    return fs_handlers.handle_delete(**handler_kwargs)
                if command == "rename":
                    return fs_handlers.handle_rename(**handler_kwargs)
                return f"Unknown command: {command}"
            except (ValueError, FileNotFoundError, PermissionError) as e:
                return str(e)

        self.tools = [file_tool]

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Inject Anthropic tool descriptor and optional system prompt."""
        overrides = inject_tool_and_prompt(
            request, self.tool_type, self.tool_name, self.system_prompt
        )
        return handler(request.override(**overrides))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Inject Anthropic tool descriptor and optional system prompt."""
        overrides = inject_tool_and_prompt(
            request, self.tool_type, self.tool_name, self.system_prompt
        )
        return await handler(request.override(**overrides))
