"""
Sandbox middleware for remote execution environments.

Provides same tool interface (read_file, write_file, run_command) as local
middleware, but executes in cloud sandbox. Provider is swapped at config time.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
    ToolCallRequest,
)
from langchain_core.messages import ToolMessage

from middleware.sandbox.manager import SandboxManager

# @@@ ContextVar for thread_id - works across async boundaries
_current_thread_id: ContextVar[str] = ContextVar("sandbox_thread_id", default="")


def set_current_thread_id(thread_id: str):
    """Set thread_id for current context (called by TUI before agent invoke)."""
    _current_thread_id.set(thread_id)


def get_current_thread_id() -> str | None:
    """Get thread_id for current context."""
    value = _current_thread_id.get()
    return value if value else None


class SandboxMiddleware(AgentMiddleware):
    """
    Sandbox middleware using provider/strategy pattern.

    Provides same tool interface as local middleware (read_file, write_file,
    run_command) but executes in remote sandbox via injected provider.

    Session lifecycle:
    - Lazy creation on first tool call
    - Auto-pause on thread switch / LEON exit
    - Auto-resume when thread is selected again
    """

    # Tool names - same as local tools (local tools disabled when sandbox enabled)
    TOOL_READ_FILE = "read_file"
    TOOL_WRITE_FILE = "write_file"
    TOOL_EDIT_FILE = "edit_file"
    TOOL_LIST_DIR = "list_dir"
    TOOL_EXECUTE = "run_command"

    def __init__(
        self,
        manager: SandboxManager,
        workspace_root: Path,
        enabled_tools: dict[str, bool] | None = None,
    ):
        """
        Initialize sandbox middleware.

        Args:
            manager: SandboxManager for session lifecycle
            workspace_root: Local workspace for upload/download validation
            enabled_tools: Which tools to expose (default: all)
        """
        self.manager = manager
        self.workspace_root = Path(workspace_root).resolve()
        self.enabled_tools = enabled_tools or {
            self.TOOL_READ_FILE: True,
            self.TOOL_WRITE_FILE: True,
            self.TOOL_EDIT_FILE: True,
            self.TOOL_LIST_DIR: True,
            self.TOOL_EXECUTE: True,
        }
        # Track read files for edit validation (no-read-no-write rule)
        self._read_files: set[str] = set()

        print(f"[SandboxMiddleware] Initialized with provider: {manager.provider.name}")

    def _get_session_id(self) -> str:
        """Get or create session for current thread."""
        thread_id = get_current_thread_id()
        if not thread_id:
            raise RuntimeError("No thread_id set. Call set_current_thread_id first.")

        info = self.manager.get_or_create_session(thread_id)
        return info.session_id

    # ==================== Tool Implementations ====================

    def _read_file_impl(self, file_path: str) -> str:
        session_id = self._get_session_id()
        try:
            content = self.manager.provider.read_file(session_id, file_path)
            self._read_files.add(file_path)
            # Format with line numbers like local read_file
            lines = content.split("\n")
            numbered = [f"{i+1:>6}\t{line}" for i, line in enumerate(lines)]
            return "\n".join(numbered)
        except Exception as e:
            return f"Error: {e}"

    def _write_file_impl(self, file_path: str, content: str) -> str:
        session_id = self._get_session_id()
        try:
            self.manager.provider.write_file(session_id, file_path, content)
            # Mark as read since we just wrote it
            self._read_files.add(file_path)
            lines = content.count("\n") + 1
            return f"File created: {file_path}\n   Lines: {lines}\n   Size: {len(content)} bytes"
        except Exception as e:
            return f"Error: {e}"

    def _edit_file_impl(self, file_path: str, old_string: str, new_string: str) -> str:
        if file_path not in self._read_files:
            return "File has not been read yet. Read it first before editing."

        if old_string == new_string:
            return "Error: old_string and new_string are identical (no-op edit)"

        session_id = self._get_session_id()
        try:
            content = self.manager.provider.read_file(session_id, file_path)

            if old_string not in content:
                return f"String not found in file\n   Looking for: {old_string[:100]}..."

            count = content.count(old_string)
            if count > 1:
                return f"String appears {count} times in file (not unique)"

            new_content = content.replace(old_string, new_string)
            self.manager.provider.write_file(session_id, file_path, new_content)
            return f"File edited: {file_path}\n   Replaced 1 occurrence"
        except Exception as e:
            return f"Error: {e}"

    def _list_dir_impl(self, directory_path: str) -> str:
        session_id = self._get_session_id()
        try:
            items = self.manager.provider.list_dir(session_id, directory_path)
            if not items:
                return f"{directory_path}: Empty directory"

            lines = [f"{directory_path}/"]
            for item in items:
                name = item.get("name", "?")
                item_type = item.get("type", "file")
                size = item.get("size", 0)
                if item_type == "directory":
                    lines.append(f"\t{name}/")
                else:
                    lines.append(f"\t{name} ({size} bytes)")
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    def _execute_impl(self, command: str, timeout_ms: int = 30000) -> str:
        session_id = self._get_session_id()
        result = self.manager.provider.execute(
            session_id, command, timeout_ms=timeout_ms
        )
        if result.error:
            return f"Error: {result.error}"
        return result.output or "(no output)"

    # ==================== Tool Schemas ====================

    def _get_tool_schemas(self) -> list[dict]:
        """Generate tool schemas based on enabled_tools config."""
        schemas = []

        if self.enabled_tools.get(self.TOOL_READ_FILE):
            schemas.append({
                "type": "function",
                "function": {
                    "name": self.TOOL_READ_FILE,
                    "description": "Read file in remote sandbox environment. Path must be absolute.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Absolute file path in sandbox",
                            },
                        },
                        "required": ["file_path"],
                    },
                },
            })

        if self.enabled_tools.get(self.TOOL_WRITE_FILE):
            schemas.append({
                "type": "function",
                "function": {
                    "name": self.TOOL_WRITE_FILE,
                    "description": "Create new file in remote sandbox environment.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Absolute file path in sandbox",
                            },
                            "content": {
                                "type": "string",
                                "description": "File content",
                            },
                        },
                        "required": ["file_path", "content"],
                    },
                },
            })

        if self.enabled_tools.get(self.TOOL_EDIT_FILE):
            schemas.append({
                "type": "function",
                "function": {
                    "name": self.TOOL_EDIT_FILE,
                    "description": "Edit file in remote sandbox using string replacement. Must read file first.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string"},
                            "old_string": {
                                "type": "string",
                                "description": "Exact string to replace (must be unique)",
                            },
                            "new_string": {
                                "type": "string",
                                "description": "Replacement string",
                            },
                        },
                        "required": ["file_path", "old_string", "new_string"],
                    },
                },
            })

        if self.enabled_tools.get(self.TOOL_LIST_DIR):
            schemas.append({
                "type": "function",
                "function": {
                    "name": self.TOOL_LIST_DIR,
                    "description": "List directory contents in remote sandbox.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "directory_path": {
                                "type": "string",
                                "description": "Absolute directory path in sandbox",
                            },
                        },
                        "required": ["directory_path"],
                    },
                },
            })

        if self.enabled_tools.get(self.TOOL_EXECUTE):
            schemas.append({
                "type": "function",
                "function": {
                    "name": self.TOOL_EXECUTE,
                    "description": "Execute shell command in remote sandbox environment.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Shell command to execute in sandbox",
                            },
                            "timeout_ms": {
                                "type": "integer",
                                "description": "Timeout in milliseconds (default 30000, max 50000)",
                                "default": 30000,
                            },
                        },
                        "required": ["command"],
                    },
                },
            })

        return schemas

    # ==================== Middleware Hooks ====================

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Inject sandbox tool schemas into model request."""
        tools = list(request.tools or [])
        tools.extend(self._get_tool_schemas())
        return handler(request.override(tools=tools))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Async: inject sandbox tool schemas."""
        tools = list(request.tools or [])
        tools.extend(self._get_tool_schemas())
        return await handler(request.override(tools=tools))

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any],
    ) -> Any:
        """Handle sandbox tool calls."""
        tool_call = request.tool_call
        tool_name = tool_call.get("name")
        args = tool_call.get("args", {})
        tool_call_id = tool_call.get("id", "")

        if tool_name == self.TOOL_READ_FILE:
            result = self._read_file_impl(file_path=args.get("file_path", ""))
            return ToolMessage(content=result, tool_call_id=tool_call_id)

        elif tool_name == self.TOOL_WRITE_FILE:
            result = self._write_file_impl(
                file_path=args.get("file_path", ""),
                content=args.get("content", ""),
            )
            return ToolMessage(content=result, tool_call_id=tool_call_id)

        elif tool_name == self.TOOL_EDIT_FILE:
            result = self._edit_file_impl(
                file_path=args.get("file_path", ""),
                old_string=args.get("old_string", ""),
                new_string=args.get("new_string", ""),
            )
            return ToolMessage(content=result, tool_call_id=tool_call_id)

        elif tool_name == self.TOOL_LIST_DIR:
            result = self._list_dir_impl(directory_path=args.get("directory_path", ""))
            return ToolMessage(content=result, tool_call_id=tool_call_id)

        elif tool_name == self.TOOL_EXECUTE:
            result = self._execute_impl(
                command=args.get("command", ""),
                timeout_ms=args.get("timeout_ms", 30000),
            )
            return ToolMessage(content=result, tool_call_id=tool_call_id)

        # Not our tool, pass through
        return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[Any]],
    ) -> Any:
        """Async: handle sandbox tool calls (wraps sync impl in thread)."""
        import asyncio

        tool_call = request.tool_call
        tool_name = tool_call.get("name")
        args = tool_call.get("args", {})
        tool_call_id = tool_call.get("id", "")

        # All provider calls are sync, wrap in thread
        if tool_name == self.TOOL_READ_FILE:
            result = await asyncio.to_thread(
                self._read_file_impl, file_path=args.get("file_path", "")
            )
            return ToolMessage(content=result, tool_call_id=tool_call_id)

        elif tool_name == self.TOOL_WRITE_FILE:
            result = await asyncio.to_thread(
                self._write_file_impl,
                file_path=args.get("file_path", ""),
                content=args.get("content", ""),
            )
            return ToolMessage(content=result, tool_call_id=tool_call_id)

        elif tool_name == self.TOOL_EDIT_FILE:
            result = await asyncio.to_thread(
                self._edit_file_impl,
                file_path=args.get("file_path", ""),
                old_string=args.get("old_string", ""),
                new_string=args.get("new_string", ""),
            )
            return ToolMessage(content=result, tool_call_id=tool_call_id)

        elif tool_name == self.TOOL_LIST_DIR:
            result = await asyncio.to_thread(
                self._list_dir_impl, directory_path=args.get("directory_path", "")
            )
            return ToolMessage(content=result, tool_call_id=tool_call_id)

        elif tool_name == self.TOOL_EXECUTE:
            result = await asyncio.to_thread(
                self._execute_impl,
                command=args.get("command", ""),
                timeout_ms=args.get("timeout_ms", 30000),
            )
            return ToolMessage(content=result, tool_call_id=tool_call_id)

        # Not our tool, pass through
        return await handler(request)
