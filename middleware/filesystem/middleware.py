"""
FileSystem Middleware - File operations

Tools (pure Middleware implementation):
- read_file: Read file (with chunking support)
- write_file: Create new file
- edit_file: Edit file (str_replace mode)
- multi_edit: Batch edit
- list_dir: List directory

All paths must be absolute. Workspace restrictions via hooks.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
    ToolCallRequest,
)
from langchain_core.messages import ToolMessage

from middleware.filesystem.backend import FileSystemBackend
from middleware.filesystem.read import ReadLimits, ReadResult
from middleware.filesystem.read import read_file as read_file_dispatch

if TYPE_CHECKING:
    from tui.operations import FileOperationRecorder


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
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        allowed_extensions: list[str] | None = None,
        hooks: list[Any] | None = None,
        enabled_tools: dict[str, bool] | None = None,
        operation_recorder: "FileOperationRecorder | None" = None,
        backend: FileSystemBackend | None = None,
        verbose: bool = True,
    ):
        """
        初始化文件系统 middleware

        Args:
            workspace_root: 工作目录（所有操作限制在此目录内）
            max_file_size: 最大文件大小（字节）
            allowed_extensions: 允许的文件扩展名（None 表示全部允许）
            hooks: 文件操作 hooks（用于安全检查和审计）
            operation_recorder: 文件操作记录器（用于时间旅行）
            backend: FileSystemBackend (default: LocalBackend)
            verbose: 是否输出详细日志
        """
        # @@@ Don't resolve workspace_root for sandbox — macOS firmlinks break it
        if backend and hasattr(backend, '_is_sandbox'):
            self.workspace_root = Path(workspace_root)
        else:
            self.workspace_root = Path(workspace_root).resolve()
        self.max_file_size = max_file_size
        self.allowed_extensions = allowed_extensions
        self.hooks = hooks or []
        self.enabled_tools = enabled_tools or {
            'read_file': True, 'write_file': True, 'edit_file': True,
            'multi_edit': True, 'list_dir': True
        }
        # path → mtime at read time (None means mtime unavailable, e.g. sandbox)
        self._read_files: dict[Path, float | None] = {}
        self.operation_recorder = operation_recorder
        self.verbose = verbose

        # Backend: default to LocalBackend
        if backend is None:
            from middleware.filesystem.local_backend import LocalBackend
            self.backend = LocalBackend()
        else:
            self.backend = backend

        # 确保 workspace 存在（only for local backend）
        if not hasattr(self.backend, '_is_sandbox'):
            self.workspace_root.mkdir(parents=True, exist_ok=True)

        if self.verbose:
            backend_name = type(self.backend).__name__
            print(f"[FileSystemMiddleware] Initialized with workspace: {self.workspace_root} (backend: {backend_name})")
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
            return False, f"Path must be absolute: {path}", None

        try:
            # @@@ Don't resolve() for sandbox — paths don't exist locally
            # macOS resolves /home → /System/Volumes/Data/home which breaks validation
            if hasattr(self.backend, '_is_sandbox'):
                resolved = Path(path)
            else:
                resolved = Path(path).resolve()
        except Exception as e:
            return False, f"Invalid path: {path} ({e})", None

        # 必须在 workspace 内
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError:
            return (
                False,
                f"Path outside workspace\n"
                f"   Workspace: {self.workspace_root}\n"
                f"   Attempted: {resolved}",
                None,
            )

        # 检查文件扩展名
        if self.allowed_extensions and resolved.suffix:
            if resolved.suffix.lstrip(".") not in self.allowed_extensions:
                return (
                    False,
                    f"File type not allowed: {resolved.suffix}\n"
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

    def _record_operation(
        self,
        operation_type: str,
        file_path: str,
        before_content: str | None,
        after_content: str,
        changes: list[dict] | None = None,
    ) -> None:
        """Record a file operation for time travel"""
        if not self.operation_recorder:
            return

        from tui.operations import current_checkpoint_id, current_thread_id

        thread_id = current_thread_id.get()
        checkpoint_id = current_checkpoint_id.get()

        if not thread_id or not checkpoint_id:
            return

        try:
            self.operation_recorder.record(
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
                operation_type=operation_type,
                file_path=file_path,
                before_content=before_content,
                after_content=after_content,
                changes=changes,
            )
        except Exception as e:
            print(f"[FileSystemMiddleware] Failed to record operation: {e}")

    def _read_file_impl(self, file_path: str, offset: int = 0, limit: int | None = None) -> ReadResult:
        """实现 read_file - 本地用 read dispatcher，sandbox 用 backend.read_file"""
        is_valid, error, resolved = self._validate_path(file_path, "read")
        if not is_valid:
            return ReadResult(
                file_path=file_path,
                file_type=None,  # type: ignore[arg-type]
                error=error,
            )

        # Check file size via backend
        file_size = self.backend.file_size(str(resolved))
        if file_size is not None and file_size > self.max_file_size:
            return ReadResult(
                file_path=file_path,
                file_type=None,  # type: ignore[arg-type]
                error=f"File too large: {file_size} bytes (max: {self.max_file_size})",
            )

        # Local backend: use rich read dispatcher (PDF/PPTX/notebook/image)
        from middleware.filesystem.local_backend import LocalBackend
        if isinstance(self.backend, LocalBackend):
            limits = ReadLimits(
                max_lines=1000,
                max_chars=100_000,
                max_line_length=2000,
            )
            result = read_file_dispatch(
                path=resolved,
                limits=limits,
                offset=offset if offset > 0 else None,
                limit=limit,
            )
            if not result.error:
                self._read_files[resolved] = self.backend.file_mtime(str(resolved))
            return result

        # Sandbox backend: basic text read + manual line numbering
        try:
            raw = self.backend.read_file(str(resolved))
            lines = raw.content.split("\n")
            # Apply offset/limit
            start = max(0, offset - 1) if offset > 0 else 0
            end = start + limit if limit else len(lines)
            selected = lines[start:end]
            numbered = [f"{start + i + 1:>6}\t{line}" for i, line in enumerate(selected)]
            content = "\n".join(numbered)

            self._read_files[resolved] = self.backend.file_mtime(str(resolved))

            return ReadResult(
                file_path=file_path,
                file_type=None,  # type: ignore[arg-type]
                content=content,
                total_lines=len(lines),
                lines_read=len(selected),
                start_line=start + 1,
                total_size=raw.size or len(raw.content),
            )
        except Exception as e:
            return ReadResult(
                file_path=file_path,
                file_type=None,  # type: ignore[arg-type]
                error=str(e),
            )

    def _make_read_tool_message(self, result: ReadResult, tool_call_id: str) -> ToolMessage:
        """Create ToolMessage from ReadResult, using content_blocks for images."""
        if result.content_blocks:
            image_desc = f"Image file: {result.file_path}\nSize: {result.total_size:,} bytes\nReturned as image content block for vision model."
            return ToolMessage(
                content=image_desc,
                content_blocks=result.content_blocks,
                tool_call_id=tool_call_id,
            )
        return ToolMessage(content=result.format_output(), tool_call_id=tool_call_id)

    def _write_file_impl(self, file_path: str, content: str) -> str:
        """实现 write_file"""
        is_valid, error, resolved = self._validate_path(file_path, "write")
        if not is_valid:
            return error

        if self.backend.file_exists(str(resolved)):
            return f"File already exists: {file_path}\nUse edit_file to modify existing files"

        try:
            result = self.backend.write_file(str(resolved), content)
            if not result.success:
                return f"Error writing file: {result.error}"

            # Mark as read since we just wrote it (AI knows the content)
            self._read_files[resolved] = self.backend.file_mtime(str(resolved))

            # Record operation for time travel
            self._record_operation(
                operation_type="write",
                file_path=file_path,
                before_content=None,
                after_content=content,
            )

            lines = content.count("\n") + 1
            return f"File created: {file_path}\n   Lines: {lines}\n   Size: {len(content)} bytes"

        except Exception as e:
            return f"Error writing file: {e}"

    def _edit_file_impl(self, file_path: str, old_string: str, new_string: str) -> str:
        """实现 edit_file (str_replace 模式)"""
        is_valid, error, resolved = self._validate_path(file_path, "edit")
        if not is_valid:
            return error

        if not self.backend.file_exists(str(resolved)):
            return f"File not found: {file_path}"

        # No read no write enforcement
        if resolved not in self._read_files:
            return "File has not been read yet. Read it first before writing to it."

        # Staleness detection: skip if mtime unavailable (sandbox)
        stored_mtime = self._read_files[resolved]
        if stored_mtime is not None:
            current_mtime = self.backend.file_mtime(str(resolved))
            if current_mtime is not None and current_mtime != stored_mtime:
                return "File has been modified since last read. Read it again before editing."

        # 禁止 no-op 编辑
        if old_string == new_string:
            return "Error: old_string and new_string are identical (no-op edit)"

        try:
            # 读取文件
            raw = self.backend.read_file(str(resolved))
            content = raw.content

            # 检查 old_string 是否存在
            if old_string not in content:
                return f"String not found in file\n   Looking for: {old_string[:100]}..."

            # 检查是否唯一
            count = content.count(old_string)
            if count > 1:
                return (
                    f"String appears {count} times in file (not unique)\n"
                    f"   Use multi_edit or provide more context to make it unique"
                )

            # 执行替换
            new_content = content.replace(old_string, new_string)

            # 写回文件
            result = self.backend.write_file(str(resolved), new_content)
            if not result.success:
                return f"Error editing file: {result.error}"

            # Update mtime after successful edit
            self._read_files[resolved] = self.backend.file_mtime(str(resolved))

            # Record operation for time travel
            self._record_operation(
                operation_type="edit",
                file_path=file_path,
                before_content=content,
                after_content=new_content,
                changes=[{"old_string": old_string, "new_string": new_string}],
            )

            return f"File edited: {file_path}\n   Replaced 1 occurrence"

        except Exception as e:
            return f"Error editing file: {e}"

    def _multi_edit_impl(self, file_path: str, edits: list[dict[str, str]]) -> str:
        """实现 multi_edit"""
        is_valid, error, resolved = self._validate_path(file_path, "edit")
        if not is_valid:
            return error

        if not self.backend.file_exists(str(resolved)):
            return f"File not found: {file_path}"

        # No read no write enforcement
        if resolved not in self._read_files:
            return "File has not been read yet. Read it first before writing to it."

        # Staleness detection: skip if mtime unavailable (sandbox)
        stored_mtime = self._read_files[resolved]
        if stored_mtime is not None:
            current_mtime = self.backend.file_mtime(str(resolved))
            if current_mtime is not None and current_mtime != stored_mtime:
                return "File has been modified since last read. Read it again before editing."

        try:
            # 读取文件
            raw = self.backend.read_file(str(resolved))
            content = raw.content
            original_content = content

            # 验证所有编辑
            for i, edit in enumerate(edits):
                old_str = edit.get("old_string", "")
                if old_str not in content:
                    return f"Edit {i + 1}: String not found\n   Looking for: {old_str[:100]}..."

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
            result = self.backend.write_file(str(resolved), content)
            if not result.success:
                return f"Error in multi_edit: {result.error}"

            # Update mtime after successful edit
            self._read_files[resolved] = self.backend.file_mtime(str(resolved))

            # Record operation for time travel
            self._record_operation(
                operation_type="multi_edit",
                file_path=file_path,
                before_content=original_content,
                after_content=content,
                changes=edits,
            )

            return f"File edited: {file_path}\n   Applied {len(edits)} edits"

        except Exception as e:
            return f"Error in multi_edit: {e}"

    def _list_dir_impl(self, directory_path: str) -> str:
        """实现 list_dir"""
        is_valid, error, resolved = self._validate_path(directory_path, "list")
        if not is_valid:
            return error

        if not self.backend.file_exists(str(resolved)):
            return f"Directory not found: {directory_path}"

        if not self.backend.is_dir(str(resolved)):
            return f"Not a directory: {directory_path}"

        try:
            result = self.backend.list_dir(str(resolved))
            if result.error:
                return f"Error listing directory: {result.error}"

            if not result.entries:
                return f"{directory_path}: Empty directory"

            items = []
            for entry in result.entries:
                if entry.is_dir:
                    count_str = f" ({entry.children_count} items)" if entry.children_count is not None else ""
                    items.append(f"\t{entry.name}/{count_str}")
                else:
                    items.append(f"\t{entry.name} ({entry.size} bytes)")

            return f"{directory_path}/\n" + "\n".join(items)

        except Exception as e:
            return f"Error listing directory: {e}"

    def _get_tool_schemas(self) -> list[dict]:
        """获取文件系统工具 schema（sync/async 共享）"""
        return [
            {
                "type": "function",
                "function": {
                    "name": self.TOOL_READ_FILE,
                    "description": "Read file content (text/code/images/PDF/PPTX/Notebook). Images return as content_blocks. Path must be absolute.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Absolute file path (e.g., /path/to/file). Do NOT use '.' or '..'"},
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
                            "file_path": {"type": "string", "description": "Absolute file path (e.g., /path/to/file). Do NOT use '.' or '..'"},
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
                    "description": (
                        "Edit existing file using exact string replacement (diff-style). "
                        "MUST use read_file before editing. "
                        "old_string must match file content exactly (including whitespace/indentation). "
                        "old_string must be unique in file. "
                        "old_string and new_string must be different (no-op edits forbidden)."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Absolute file path (e.g., /path/to/file). Do NOT use '.' or '..'"},
                            "old_string": {"type": "string", "description": "Exact string to replace (must be unique and match exactly)"},
                            "new_string": {"type": "string", "description": "Replacement string (must differ from old_string)"},
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
                            "file_path": {"type": "string", "description": "Absolute file path (e.g., /path/to/file). Do NOT use '.' or '..'"},
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
                            "directory_path": {"type": "string", "description": "Absolute directory path (e.g., /path/to/dir). Do NOT use '.' or '..'"},
                        },
                        "required": ["directory_path"],
                    },
                },
            },
        ]

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """注入文件系统工具定义"""
        tools = list(request.tools or [])
        tools.extend(self._get_tool_schemas())
        return handler(request.override(tools=tools))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """异步：注入文件系统工具定义"""
        tools = list(request.tools or [])
        tools.extend(self._get_tool_schemas())
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
            return self._make_read_tool_message(result, tool_call.get("id", ""))

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
            return self._make_read_tool_message(result, tool_call.get("id", ""))

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
