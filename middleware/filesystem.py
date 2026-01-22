"""
FileSystem Middleware - 完全模仿 Cascade 的文件操作

提供以下工具（纯 Middleware 实现）：
- read_file: 读取文件（支持分段）
- write_file: 创建新文件
- edit_file: 编辑文件（str_replace 模式）
- multi_edit: 批量编辑
- list_dir: 列出目录

所有路径必须使用绝对路径，workspace 限制通过 hooks 实现。
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
    ToolCallRequest,
)
from langchain_core.messages import ToolMessage


class FileSystemMiddleware(AgentMiddleware):
    """
    文件系统 Middleware - 纯 Middleware 实现所有文件操作

    特点：
    - 所有工具都在 middleware 层实现，不暴露为独立 Tool
    - 强制使用绝对路径
    - 支持 workspace 限制（通过 hooks）
    - 完整的审计日志
    """

    # 工具名称常量
    TOOL_READ_FILE = "read_file"
    TOOL_WRITE_FILE = "write_file"
    TOOL_EDIT_FILE = "edit_file"
    TOOL_MULTI_EDIT = "multi_edit"
    TOOL_LIST_DIR = "list_dir"

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        read_only: bool = False,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        allowed_extensions: list[str] | None = None,
        hooks: list[Any] | None = None,
    ):
        """
        初始化文件系统 middleware

        Args:
            workspace_root: 工作目录（所有操作限制在此目录内）
            read_only: 只读模式（禁止写入和编辑）
            max_file_size: 最大文件大小（字节）
            allowed_extensions: 允许的文件扩展名（None 表示全部允许）
            hooks: 文件操作 hooks（用于安全检查和审计）
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.read_only = read_only
        self.max_file_size = max_file_size
        self.allowed_extensions = allowed_extensions
        self.hooks = hooks or []

        # 确保 workspace 存在
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        print(f"[FileSystemMiddleware] Initialized with workspace: {self.workspace_root}")
        print(f"[FileSystemMiddleware] Read-only mode: {self.read_only}")
        if self.hooks:
            print(f"[FileSystemMiddleware] Loaded {len(self.hooks)} hooks")

    def _validate_path(self, path: str, operation: str) -> tuple[bool, str, Path | None]:
        """
        验证路径

        Returns:
            (is_valid, error_message, resolved_path)
        """
        # 必须是绝对路径
        if not Path(path).is_absolute():
            return False, f"❌ Path must be absolute: {path}", None

        try:
            resolved = Path(path).resolve()
        except Exception as e:
            return False, f"❌ Invalid path: {path} ({e})", None

        # 必须在 workspace 内
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError:
            return (
                False,
                f"❌ Path outside workspace\n"
                f"   Workspace: {self.workspace_root}\n"
                f"   Attempted: {resolved}",
                None,
            )

        # 检查文件扩展名
        if self.allowed_extensions and resolved.suffix:
            if resolved.suffix.lstrip(".") not in self.allowed_extensions:
                return (
                    False,
                    f"❌ File type not allowed: {resolved.suffix}\n"
                    f"   Allowed: {', '.join(self.allowed_extensions)}",
                    None,
                )

        # 运行 hooks
        for hook in self.hooks:
            if hasattr(hook, "check_file_operation"):
                result = hook.check_file_operation(str(resolved), operation)
                if not result.allow:
                    return False, result.error_message, None

        return True, "", resolved

    def _read_file_impl(self, file_path: str, offset: int = 0, limit: int | None = None) -> str:
        """实现 read_file"""
        is_valid, error, resolved = self._validate_path(file_path, "read")
        if not is_valid:
            return error

        if not resolved.exists():
            return f"❌ File not found: {file_path}"

        if not resolved.is_file():
            return f"❌ Not a file: {file_path}"

        # 检查文件大小
        if resolved.stat().st_size > self.max_file_size:
            return f"❌ File too large: {resolved.stat().st_size} bytes (max: {self.max_file_size})"

        try:
            with open(resolved, "r", encoding="utf-8") as f:
                lines = f.readlines()

            total_lines = len(lines)

            # 处理分段读取
            if offset > 0:
                if offset > total_lines:
                    return f"❌ Offset {offset} exceeds file length {total_lines}"
                lines = lines[offset - 1 :]  # offset 是 1-indexed

            if limit:
                lines = lines[:limit]

            # 格式化输出（带行号，cat -n 风格）
            start_line = offset if offset > 0 else 1
            formatted_lines = []
            for i, line in enumerate(lines, start=start_line):
                formatted_lines.append(f"{i:6d}\t{line.rstrip()}")

            result = "\n".join(formatted_lines)

            # 添加元信息
            header = f"File: {file_path}\n"
            header += f"Lines: {start_line}-{start_line + len(lines) - 1} of {total_lines}\n"
            header += "-" * 80 + "\n"

            return header + result

        except UnicodeDecodeError:
            return f"❌ Cannot read file (not UTF-8): {file_path}"
        except Exception as e:
            return f"❌ Error reading file: {e}"

    def _write_file_impl(self, file_path: str, content: str) -> str:
        """实现 write_file"""
        if self.read_only:
            return "❌ Write operation not allowed in read-only mode"

        is_valid, error, resolved = self._validate_path(file_path, "write")
        if not is_valid:
            return error

        if resolved.exists():
            return f"❌ File already exists: {file_path}\nUse edit_file to modify existing files"

        try:
            # 创建父目录
            resolved.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            with open(resolved, "w", encoding="utf-8") as f:
                f.write(content)

            lines = content.count("\n") + 1
            return f"✅ File created: {file_path}\n   Lines: {lines}\n   Size: {len(content)} bytes"

        except Exception as e:
            return f"❌ Error writing file: {e}"

    def _edit_file_impl(self, file_path: str, old_string: str, new_string: str) -> str:
        """实现 edit_file (str_replace 模式)"""
        if self.read_only:
            return "❌ Edit operation not allowed in read-only mode"

        is_valid, error, resolved = self._validate_path(file_path, "edit")
        if not is_valid:
            return error

        if not resolved.exists():
            return f"❌ File not found: {file_path}"

        try:
            # 读取文件
            with open(resolved, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查 old_string 是否存在
            if old_string not in content:
                return f"❌ String not found in file\n   Looking for: {old_string[:100]}..."

            # 检查是否唯一
            count = content.count(old_string)
            if count > 1:
                return (
                    f"❌ String appears {count} times in file (not unique)\n"
                    f"   Use multi_edit or provide more context to make it unique"
                )

            # 执行替换
            new_content = content.replace(old_string, new_string)

            # 写回文件
            with open(resolved, "w", encoding="utf-8") as f:
                f.write(new_content)

            return f"✅ File edited: {file_path}\n   Replaced 1 occurrence"

        except Exception as e:
            return f"❌ Error editing file: {e}"

    def _multi_edit_impl(self, file_path: str, edits: list[dict[str, str]]) -> str:
        """实现 multi_edit"""
        if self.read_only:
            return "❌ Edit operation not allowed in read-only mode"

        is_valid, error, resolved = self._validate_path(file_path, "edit")
        if not is_valid:
            return error

        if not resolved.exists():
            return f"❌ File not found: {file_path}"

        try:
            # 读取文件
            with open(resolved, "r", encoding="utf-8") as f:
                content = f.read()

            # 验证所有编辑
            for i, edit in enumerate(edits):
                old_str = edit.get("old_string", "")
                if old_str not in content:
                    return f"❌ Edit {i + 1}: String not found\n   Looking for: {old_str[:100]}..."

            # 顺序执行所有编辑
            for edit in edits:
                old_str = edit.get("old_string", "")
                new_str = edit.get("new_string", "")
                replace_all = edit.get("replace_all", False)

                if replace_all:
                    content = content.replace(old_str, new_str)
                else:
                    # 只替换第一次出现
                    content = content.replace(old_str, new_str, 1)

            # 写回文件
            with open(resolved, "w", encoding="utf-8") as f:
                f.write(content)

            return f"✅ File edited: {file_path}\n   Applied {len(edits)} edits"

        except Exception as e:
            return f"❌ Error in multi_edit: {e}"

    def _list_dir_impl(self, directory_path: str) -> str:
        """实现 list_dir"""
        is_valid, error, resolved = self._validate_path(directory_path, "list")
        if not is_valid:
            return error

        if not resolved.exists():
            return f"❌ Directory not found: {directory_path}"

        if not resolved.is_dir():
            return f"❌ Not a directory: {directory_path}"

        try:
            items = []
            for item in sorted(resolved.iterdir()):
                if item.is_file():
                    size = item.stat().st_size
                    items.append(f"  {item.name} ({size} bytes)")
                elif item.is_dir():
                    count = sum(1 for _ in item.iterdir())
                    items.append(f"  {item.name}/ ({count} items)")

            if not items:
                return f"Directory: {directory_path}\n(empty)"

            return f"Directory: {directory_path}\n" + "\n".join(items)

        except Exception as e:
            return f"❌ Error listing directory: {e}"

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """注入文件系统工具定义"""
        tools = list(request.tools or [])

        # 添加文件系统工具
        tools.extend(
            [
                {
                    "type": "function",
                    "function": {
                        "name": self.TOOL_READ_FILE,
                        "description": "Read file content. Path must be absolute.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string", "description": "Absolute file path"},
                                "offset": {"type": "integer", "description": "Start line (1-indexed, optional)"},
                                "limit": {"type": "integer", "description": "Number of lines to read (optional)"},
                            },
                            "required": ["file_path"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": self.TOOL_WRITE_FILE,
                        "description": "Create new file. Path must be absolute. Fails if file exists.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string", "description": "Absolute file path"},
                                "content": {"type": "string", "description": "File content"},
                            },
                            "required": ["file_path", "content"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": self.TOOL_EDIT_FILE,
                        "description": "Edit existing file using string replacement. old_string must be unique.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string", "description": "Absolute file path"},
                                "old_string": {"type": "string", "description": "String to replace (must be unique)"},
                                "new_string": {"type": "string", "description": "Replacement string"},
                            },
                            "required": ["file_path", "old_string", "new_string"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": self.TOOL_MULTI_EDIT,
                        "description": "Apply multiple edits to a file sequentially.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string", "description": "Absolute file path"},
                                "edits": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "old_string": {"type": "string"},
                                            "new_string": {"type": "string"},
                                            "replace_all": {"type": "boolean"},
                                        },
                                        "required": ["old_string", "new_string"],
                                    },
                                },
                            },
                            "required": ["file_path", "edits"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": self.TOOL_LIST_DIR,
                        "description": "List directory contents. Path must be absolute.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "directory_path": {"type": "string", "description": "Absolute directory path"},
                            },
                            "required": ["directory_path"],
                        },
                    },
                },
            ]
        )

        return handler(request.override(tools=tools))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """异步：注入文件系统工具定义"""
        tools = list(request.tools or [])

        # 添加文件系统工具（同步版本）
        tools.extend(
            [
                {
                    "type": "function",
                    "function": {
                        "name": self.TOOL_READ_FILE,
                        "description": "Read file content. Path must be absolute.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string", "description": "Absolute file path"},
                                "offset": {"type": "integer", "description": "Start line (1-indexed, optional)"},
                                "limit": {"type": "integer", "description": "Number of lines to read (optional)"},
                            },
                            "required": ["file_path"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": self.TOOL_WRITE_FILE,
                        "description": "Create new file. Path must be absolute. Fails if file exists.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string", "description": "Absolute file path"},
                                "content": {"type": "string", "description": "File content"},
                            },
                            "required": ["file_path", "content"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": self.TOOL_EDIT_FILE,
                        "description": "Edit existing file using string replacement. old_string must be unique.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string", "description": "Absolute file path"},
                                "old_string": {"type": "string", "description": "String to replace (must be unique)"},
                                "new_string": {"type": "string", "description": "Replacement string"},
                            },
                            "required": ["file_path", "old_string", "new_string"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": self.TOOL_MULTI_EDIT,
                        "description": "Apply multiple edits to a file sequentially.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string", "description": "Absolute file path"},
                                "edits": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "old_string": {"type": "string"},
                                            "new_string": {"type": "string"},
                                            "replace_all": {"type": "boolean"},
                                        },
                                        "required": ["old_string", "new_string"],
                                    },
                                },
                            },
                            "required": ["file_path", "edits"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": self.TOOL_LIST_DIR,
                        "description": "List directory contents. Path must be absolute.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "directory_path": {"type": "string", "description": "Absolute directory path"},
                            },
                            "required": ["directory_path"],
                        },
                    },
                },
            ]
        )

        return await handler(request.override(tools=tools))

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any],
    ) -> Any:
        """拦截并处理文件系统工具调用"""
        tool_call = request.tool_call
        tool_name = tool_call.get("name")
        args = tool_call.get("args", {})

        # 处理文件系统工具
        if tool_name == self.TOOL_READ_FILE:
            result = self._read_file_impl(
                file_path=args.get("file_path", ""),
                offset=args.get("offset", 0),
                limit=args.get("limit"),
            )
            return ToolMessage(content=result, tool_call_id=tool_call.get("id", ""))

        elif tool_name == self.TOOL_WRITE_FILE:
            result = self._write_file_impl(
                file_path=args.get("file_path", ""), content=args.get("content", "")
            )
            return ToolMessage(content=result, tool_call_id=tool_call.get("id", ""))

        elif tool_name == self.TOOL_EDIT_FILE:
            result = self._edit_file_impl(
                file_path=args.get("file_path", ""),
                old_string=args.get("old_string", ""),
                new_string=args.get("new_string", ""),
            )
            return ToolMessage(content=result, tool_call_id=tool_call.get("id", ""))

        elif tool_name == self.TOOL_MULTI_EDIT:
            result = self._multi_edit_impl(
                file_path=args.get("file_path", ""), edits=args.get("edits", [])
            )
            return ToolMessage(content=result, tool_call_id=tool_call.get("id", ""))

        elif tool_name == self.TOOL_LIST_DIR:
            result = self._list_dir_impl(directory_path=args.get("directory_path", ""))
            return ToolMessage(content=result, tool_call_id=tool_call.get("id", ""))

        # 非文件系统工具，传递给下一个 handler
        return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[Any]],
    ) -> Any:
        """异步：拦截并处理文件系统工具调用"""
        tool_call = request.tool_call
        tool_name = tool_call.get("name")
        args = tool_call.get("args", {})

        # 处理文件系统工具（同步实现）
        if tool_name == self.TOOL_READ_FILE:
            result = self._read_file_impl(
                file_path=args.get("file_path", ""),
                offset=args.get("offset", 0),
                limit=args.get("limit"),
            )
            return ToolMessage(content=result, tool_call_id=tool_call.get("id", ""))

        elif tool_name == self.TOOL_WRITE_FILE:
            result = self._write_file_impl(
                file_path=args.get("file_path", ""), content=args.get("content", "")
            )
            return ToolMessage(content=result, tool_call_id=tool_call.get("id", ""))

        elif tool_name == self.TOOL_EDIT_FILE:
            result = self._edit_file_impl(
                file_path=args.get("file_path", ""),
                old_string=args.get("old_string", ""),
                new_string=args.get("new_string", ""),
            )
            return ToolMessage(content=result, tool_call_id=tool_call.get("id", ""))

        elif tool_name == self.TOOL_MULTI_EDIT:
            result = self._multi_edit_impl(
                file_path=args.get("file_path", ""), edits=args.get("edits", [])
            )
            return ToolMessage(content=result, tool_call_id=tool_call.get("id", ""))

        elif tool_name == self.TOOL_LIST_DIR:
            result = self._list_dir_impl(directory_path=args.get("directory_path", ""))
            return ToolMessage(content=result, tool_call_id=tool_call.get("id", ""))

        # 非文件系统工具，传递给下一个 handler
        return await handler(request)


__all__ = ["FileSystemMiddleware"]
