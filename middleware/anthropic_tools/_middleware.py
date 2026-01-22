"""Concrete middleware implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._base import FilesystemClaudeFileToolMiddleware, StateClaudeFileToolMiddleware
from ._constants import (
    MEMORY_SYSTEM_PROMPT,
    MEMORY_TOOL_NAME,
    MEMORY_TOOL_TYPE,
    TEXT_EDITOR_TOOL_NAME,
    TEXT_EDITOR_TOOL_TYPE,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class StateClaudeTextEditorMiddleware(StateClaudeFileToolMiddleware):
    """State-based text editor tool middleware.

    Provides Anthropic's `text_editor` tool using LangGraph state for storage.
    Files persist for the conversation thread.

    Example:
        ```python
        from langchain.agents import create_agent
        from langchain.agents.middleware import StateTextEditorToolMiddleware

        agent = create_agent(
            model=model,
            tools=[],
            middleware=[StateTextEditorToolMiddleware()],
        )
        ```
    """

    def __init__(
        self,
        *,
        allowed_path_prefixes: Sequence[str] | None = None,
    ) -> None:
        """Initialize the text editor middleware.

        Args:
            allowed_path_prefixes: Optional list of allowed path prefixes.

                If specified, only paths starting with these prefixes are allowed.
        """
        super().__init__(
            tool_type=TEXT_EDITOR_TOOL_TYPE,
            tool_name=TEXT_EDITOR_TOOL_NAME,
            state_key="text_editor_files",
            allowed_path_prefixes=allowed_path_prefixes,
        )


class StateClaudeMemoryMiddleware(StateClaudeFileToolMiddleware):
    """State-based memory tool middleware.

    Provides Anthropic's memory tool using LangGraph state for storage.
    Files persist for the conversation thread.

    Enforces `/memories` prefix and injects Anthropic's recommended system prompt.

    Example:
        ```python
        from langchain.agents import create_agent
        from langchain.agents.middleware import StateMemoryToolMiddleware

        agent = create_agent(
            model=model,
            tools=[],
            middleware=[StateMemoryToolMiddleware()],
        )
        ```
    """

    def __init__(
        self,
        *,
        allowed_path_prefixes: Sequence[str] | None = None,
        system_prompt: str = MEMORY_SYSTEM_PROMPT,
    ) -> None:
        """Initialize the memory middleware.

        Args:
            allowed_path_prefixes: Optional list of allowed path prefixes.

                Defaults to `['/memories']`.
            system_prompt: System prompt to inject.

                Defaults to Anthropic's recommended memory prompt.
        """
        super().__init__(
            tool_type=MEMORY_TOOL_TYPE,
            tool_name=MEMORY_TOOL_NAME,
            state_key="memory_files",
            allowed_path_prefixes=allowed_path_prefixes or ["/memories"],
            system_prompt=system_prompt,
        )


class FilesystemClaudeTextEditorMiddleware(FilesystemClaudeFileToolMiddleware):
    """Filesystem-based text editor tool middleware.

    Provides Anthropic's `text_editor` tool using local filesystem for storage.
    User handles persistence via volumes, git, or other mechanisms.

    Example:
        ```python
        from langchain.agents import create_agent
        from langchain.agents.middleware import FilesystemTextEditorToolMiddleware

        agent = create_agent(
            model=model,
            tools=[],
            middleware=[FilesystemTextEditorToolMiddleware(root_path="/workspace")],
        )
        ```
    """

    def __init__(
        self,
        *,
        root_path: str,
        allowed_prefixes: list[str] | None = None,
        max_file_size_mb: int = 10,
    ) -> None:
        """Initialize the text editor middleware.

        Args:
            root_path: Root directory for file operations.
            allowed_prefixes: Optional list of allowed virtual path prefixes.

                Defaults to `['/']`.
            max_file_size_mb: Maximum file size in MB

                Defaults to `10`.
        """
        super().__init__(
            tool_type=TEXT_EDITOR_TOOL_TYPE,
            tool_name=TEXT_EDITOR_TOOL_NAME,
            root_path=root_path,
            allowed_prefixes=allowed_prefixes,
            max_file_size_mb=max_file_size_mb,
        )


class FilesystemClaudeMemoryMiddleware(FilesystemClaudeFileToolMiddleware):
    """Filesystem-based memory tool middleware.

    Provides Anthropic's memory tool using local filesystem for storage.
    User handles persistence via volumes, git, or other mechanisms.

    Enforces `/memories` prefix and injects Anthropic's recommended system
    prompt.

    Example:
        ```python
        from langchain.agents import create_agent
        from langchain.agents.middleware import FilesystemMemoryToolMiddleware

        agent = create_agent(
            model=model,
            tools=[],
            middleware=[FilesystemMemoryToolMiddleware(root_path="/workspace")],
        )
        ```
    """

    def __init__(
        self,
        *,
        root_path: str,
        allowed_prefixes: list[str] | None = None,
        max_file_size_mb: int = 10,
        system_prompt: str = MEMORY_SYSTEM_PROMPT,
    ) -> None:
        """Initialize the memory middleware.

        Args:
            root_path: Root directory for file operations.
            allowed_prefixes: Optional list of allowed virtual path prefixes.

                Defaults to `['/memories']`.
            max_file_size_mb: Maximum file size in MB

                Defaults to `10`.
            system_prompt: System prompt to inject.

                Defaults to Anthropic's recommended memory prompt.
        """
        super().__init__(
            tool_type=MEMORY_TOOL_TYPE,
            tool_name=MEMORY_TOOL_NAME,
            root_path=root_path,
            allowed_prefixes=allowed_prefixes or ["/memories"],
            max_file_size_mb=max_file_size_mb,
            system_prompt=system_prompt,
        )
