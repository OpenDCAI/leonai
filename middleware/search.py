"""
Search Middleware - Code search functionality

Tools (pure Middleware implementation):
- grep_search: Content search (ripgrep preferred, Python fallback)
- find_by_name: Filename search (fd preferred, Python fallback)

Features:
- PascalCase parameter naming (SearchPath, Query, Includes, MatchPerLine)
- Absolute path requirement
- Concise output format
- System tools preferred, Python fallback
"""

from __future__ import annotations

import re
import shutil
import subprocess
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


class SearchMiddleware(AgentMiddleware):
    """
    Search Middleware

    Features:
    - Prefers ripgrep/fd system tools (best performance)
    - Fallback to Python implementation (cross-platform)
    - PascalCase parameter naming
    - Absolute path enforcement
    - Concise output format
    """

    TOOL_GREP_SEARCH = "grep_search"
    TOOL_FIND_BY_NAME = "find_by_name"

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        max_results: int = 50,  # Default limit
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        prefer_system_tools: bool = True,
        enabled_tools: dict[str, bool] | None = None,
        verbose: bool = True,
    ):
        """
        Initialize search middleware

        Args:
            workspace_root: Working directory (search restricted to this directory)
            max_results: Maximum results (default 50)
            max_file_size: Maximum file size (bytes)
            prefer_system_tools: Whether to prefer system tools (ripgrep/fd)
            verbose: Whether to output detailed logs
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.max_results = max_results
        self.max_file_size = max_file_size
        self.prefer_system_tools = prefer_system_tools
        self.enabled_tools = enabled_tools or {"grep_search": True, "find_by_name": True}
        self.verbose = verbose

        # 检查系统工具可用性
        self.has_ripgrep = shutil.which("rg") is not None
        self.has_fd = shutil.which("fd") is not None

        if self.verbose:
            print(f"[SearchMiddleware] Initialized with workspace: {self.workspace_root}")
            if self.prefer_system_tools:
                print(f"[SearchMiddleware] ripgrep available: {self.has_ripgrep}")
                print(f"[SearchMiddleware] fd available: {self.has_fd}")

    def _validate_path(self, path: str) -> tuple[bool, str, Path | None]:
        """验证搜索路径"""
        if not Path(path).is_absolute():
            return False, f"Path must be absolute: {path}", None

        try:
            resolved = Path(path).resolve()
        except Exception as e:
            return False, f"Invalid path: {path} ({e})", None

        # 必须在 workspace 内
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError:
            return (
                False,
                f"Path outside workspace\n   Workspace: {self.workspace_root}\n   Attempted: {resolved}",
                None,
            )

        return True, "", resolved

    def _grep_search_impl(
        self,
        SearchPath: str,
        Query: str,
        CaseSensitive: bool = False,
        FixedStrings: bool = False,
        Includes: list[str] | None = None,
        MatchPerLine: bool = False,
    ) -> str:
        """
        Implement grep_search

        Prefers ripgrep, fallback to Python implementation
        PascalCase parameter naming
        """
        is_valid, error, resolved = self._validate_path(SearchPath)
        if not is_valid:
            return error

        if not resolved.exists():
            return f"Path not found: {SearchPath}"

        # 尝试使用 ripgrep（性能最佳）
        if self.prefer_system_tools and self.has_ripgrep:
            try:
                return self._ripgrep_search(resolved, Query, CaseSensitive, FixedStrings, Includes, MatchPerLine)
            except Exception as e:
                print(f"[SearchMiddleware] ripgrep failed, fallback to Python: {e}")

        # Fallback 到 Python 实现
        return self._python_grep_search(resolved, Query, CaseSensitive, FixedStrings, Includes, MatchPerLine)

    def _ripgrep_search(
        self,
        path: Path,
        query: str,
        case_sensitive: bool,
        fixed_strings: bool,
        includes: list[str] | None,
        match_per_line: bool,
    ) -> str:
        """Use ripgrep for search"""
        cmd = ["rg", query, str(path)]

        # 大小写敏感
        if not case_sensitive:
            cmd.append("-i")

        # 字面匹配
        if fixed_strings:
            cmd.append("-F")

        # 文件过滤
        if includes:
            for pattern in includes:
                cmd.extend(["-g", pattern])

        # 输出格式
        if match_per_line:
            cmd.extend(["--line-number", "--no-heading", "-C", "2"])  # 前后各 2 行上下文
        else:
            cmd.extend(["--files-with-matches"])

        # 限制结果数
        cmd.extend(["--max-count", str(self.max_results)])

        # 执行命令
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.workspace_root),
            )

            if result.returncode == 0:
                # 成功找到匹配
                output = result.stdout.strip()
                if not output:
                    return "No matches found"

                # 处理 ripgrep 输出
                lines = []
                for line in output.split("\n"):
                    if not line:
                        continue

                    if match_per_line:
                        # ripgrep -C 输出格式：
                        # 行号:匹配内容（匹配行）
                        # 行号-上下文内容（上下文行）
                        # -- （分隔符，忽略）
                        if line == "--":
                            continue

                        # 直接使用 ripgrep 的格式（已经是 行号:内容 或 行号-内容）
                        lines.append(line)
                    else:
                        # 只返回文件名
                        try:
                            file_path = Path(line)
                            rel_path = file_path.relative_to(self.workspace_root)
                            lines.append(str(rel_path))
                        except ValueError:
                            lines.append(line)

                return "\n".join(lines) if lines else "No matches found"

            elif result.returncode == 1:
                # 没有找到匹配
                return "No matches found"
            else:
                # 错误
                raise RuntimeError(f"ripgrep error: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("Search timeout (30s)")

    def _python_grep_search(
        self,
        path: Path,
        query: str,
        case_sensitive: bool,
        fixed_strings: bool,
        includes: list[str] | None,
        match_per_line: bool,
    ) -> str:
        """Python 实现的 grep 搜索（fallback）"""
        # 编译正则表达式
        try:
            if fixed_strings:
                pattern = re.escape(query)
            else:
                pattern = query

            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)
        except re.error as e:
            return f"Invalid regex pattern: {e}"

        # 收集要搜索的文件
        files_to_search = []
        if path.is_file():
            files_to_search.append(path)
        else:
            for file_path in path.rglob("*"):
                if not file_path.is_file():
                    continue

                if file_path.stat().st_size > self.max_file_size:
                    continue

                if includes:
                    match = False
                    for pattern in includes:
                        if file_path.match(pattern):
                            match = True
                            break
                    if not match:
                        continue

                files_to_search.append(file_path)

        # 搜索文件
        results = []
        count = 0

        for file_path in files_to_search:
            if count >= self.max_results:
                break

            try:
                with open(file_path, encoding="utf-8") as f:
                    lines = f.readlines()

                match_line_nums = []
                for line_num, line in enumerate(lines, start=1):
                    if regex.search(line):
                        match_line_nums.append(line_num)

                if match_line_nums:
                    if match_per_line:
                        # Show matching line + context
                        context_lines = 2  # 前后各 2 行
                        displayed_lines = set()

                        for match_line in match_line_nums:
                            # 计算上下文范围
                            start = max(1, match_line - context_lines)
                            end = min(len(lines), match_line + context_lines)

                            for line_num in range(start, end + 1):
                                if line_num not in displayed_lines:
                                    displayed_lines.add(line_num)
                                    line_content = lines[line_num - 1].rstrip()

                                    # 匹配行用 :，上下文行用 -
                                    marker = ":" if line_num in match_line_nums else "-"
                                    results.append(f"{line_num}{marker}{line_content}")

                            count += 1
                            if count >= self.max_results:
                                break
                    else:
                        # 只返回文件名
                        rel_path = file_path.relative_to(self.workspace_root)
                        results.append(str(rel_path))
                        count += 1

            except (UnicodeDecodeError, PermissionError):
                continue

        return "\n".join(results) if results else "No matches found"

    def _find_by_name_impl(
        self,
        SearchDirectory: str,
        Pattern: str,
        Extensions: list[str] | None = None,
        Type: str = "any",
        MaxDepth: int | None = None,
        FullPath: bool = False,
    ) -> str:
        """
        Implement find_by_name

        Prefers fd, fallback to Python implementation
        PascalCase parameter naming
        """
        is_valid, error, resolved = self._validate_path(SearchDirectory)
        if not is_valid:
            return error

        if not resolved.exists():
            return f"Directory not found: {SearchDirectory}"

        if not resolved.is_dir():
            return f"Not a directory: {SearchDirectory}"

        # 尝试使用 fd（性能最佳）
        if self.prefer_system_tools and self.has_fd:
            try:
                return self._fd_search(resolved, Pattern, Extensions, Type, MaxDepth, FullPath)
            except Exception as e:
                print(f"[SearchMiddleware] fd failed, fallback to Python: {e}")

        # Fallback 到 Python 实现
        return self._python_find_search(resolved, Pattern, Extensions, Type, MaxDepth, FullPath)

    def _fd_search(
        self,
        path: Path,
        pattern: str,
        extensions: list[str] | None,
        type_filter: str,
        max_depth: int | None,
        full_path: bool,
    ) -> str:
        """Use fd for filename search"""
        cmd = ["fd", pattern, str(path)]

        # 类型过滤
        if type_filter == "file":
            cmd.append("--type=f")
        elif type_filter == "directory":
            cmd.append("--type=d")

        # 扩展名过滤
        if extensions:
            for ext in extensions:
                cmd.extend(["--extension", ext])

        # 最大深度
        if max_depth:
            cmd.extend(["--max-depth", str(max_depth)])

        # 全路径匹配
        if full_path:
            cmd.append("--full-path")

        # 限制结果数
        cmd.extend(["--max-results", str(self.max_results)])

        # 执行命令
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=str(self.workspace_root))

            if result.returncode == 0:
                output = result.stdout.strip()
                if not output:
                    return "No files found"

                # 收集绝对路径
                lines = []
                for line in output.split("\n"):
                    if line:
                        file_path = Path(line)
                        if not file_path.is_absolute():
                            file_path = (self.workspace_root / line).resolve()
                        lines.append(str(file_path))

                if not lines:
                    return "No files found"
                return f"Found {len(lines)} results\n" + "\n".join(lines)
            else:
                raise RuntimeError(f"fd error: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("Search timeout (30s)")

    def _python_find_search(
        self,
        path: Path,
        pattern: str,
        extensions: list[str] | None,
        type_filter: str,
        max_depth: int | None,
        full_path: bool,
    ) -> str:
        """Python 实现的文件名搜索（fallback）"""
        results = []
        count = 0

        def search_recursive(current_path: Path, depth: int = 0):
            nonlocal count
            if max_depth and depth > max_depth:
                return

            if count >= self.max_results:
                return

            try:
                for item in sorted(current_path.iterdir()):
                    if count >= self.max_results:
                        break

                    # 类型过滤
                    if type_filter == "file" and not item.is_file():
                        continue
                    if type_filter == "directory" and not item.is_dir():
                        continue

                    # 扩展名过滤
                    if extensions and item.is_file():
                        if item.suffix.lstrip(".") not in extensions:
                            continue

                    # 名称匹配
                    match_target = str(item) if full_path else item.name
                    if item.match(pattern):
                        results.append(str(item))
                        count += 1

                    # 递归搜索子目录
                    if item.is_dir():
                        search_recursive(item, depth + 1)

            except PermissionError:
                pass

        search_recursive(path)

        if not results:
            return "No files found"
        return f"Found {len(results)} results\n" + "\n".join(results)

    def _get_tool_schemas(self) -> list[dict]:
        """获取搜索工具 schema（sync/async 共享）"""
        return [
            {
                "type": "function",
                "function": {
                    "name": self.TOOL_GREP_SEARCH,
                    "description": "Search file contents using regex. Path must be absolute.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "SearchPath": {
                                "type": "string",
                                "description": "Absolute path to file or directory",
                            },
                            "Query": {"type": "string", "description": "Search pattern (regex by default)"},
                            "CaseSensitive": {"type": "boolean", "description": "Case sensitive search"},
                            "FixedStrings": {
                                "type": "boolean",
                                "description": "Treat query as literal string",
                            },
                            "Includes": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Glob patterns to filter files (e.g., '*.py')",
                            },
                            "MatchPerLine": {
                                "type": "boolean",
                                "description": "Show line-by-line matches",
                            },
                        },
                        "required": ["SearchPath", "Query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": self.TOOL_FIND_BY_NAME,
                    "description": "Find files by name pattern. Path must be absolute.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "SearchDirectory": {
                                "type": "string",
                                "description": "Absolute directory path",
                            },
                            "Pattern": {"type": "string", "description": "Glob pattern (e.g., '*.py')"},
                            "Extensions": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "File extensions to include",
                            },
                            "Type": {
                                "type": "string",
                                "enum": ["file", "directory", "any"],
                                "description": "Filter by type",
                            },
                            "MaxDepth": {"type": "integer", "description": "Maximum search depth"},
                            "FullPath": {"type": "boolean", "description": "Match against full path"},
                        },
                        "required": ["SearchDirectory", "Pattern"],
                    },
                },
            },
        ]

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """注入搜索工具定义"""
        tools = list(request.tools or [])
        tools.extend(self._get_tool_schemas())
        return handler(request.override(tools=tools))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """异步：注入搜索工具定义"""
        tools = list(request.tools or [])
        tools.extend(self._get_tool_schemas())
        return await handler(request.override(tools=tools))

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any],
    ) -> Any:
        """拦截并处理搜索工具调用"""
        tool_call = request.tool_call
        tool_name = tool_call.get("name")
        args = tool_call.get("args", {})

        if tool_name == self.TOOL_GREP_SEARCH:
            result = self._grep_search_impl(
                SearchPath=args.get("SearchPath", ""),
                Query=args.get("Query", ""),
                CaseSensitive=args.get("CaseSensitive", False),
                FixedStrings=args.get("FixedStrings", False),
                Includes=args.get("Includes"),
                MatchPerLine=args.get("MatchPerLine", False),
            )
            return ToolMessage(content=result, tool_call_id=tool_call.get("id", ""))

        elif tool_name == self.TOOL_FIND_BY_NAME:
            result = self._find_by_name_impl(
                SearchDirectory=args.get("SearchDirectory", ""),
                Pattern=args.get("Pattern", ""),
                Extensions=args.get("Extensions"),
                Type=args.get("Type", "any"),
                MaxDepth=args.get("MaxDepth"),
                FullPath=args.get("FullPath", False),
            )
            return ToolMessage(content=result, tool_call_id=tool_call.get("id", ""))

        return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[Any]],
    ) -> Any:
        """异步：拦截并处理搜索工具调用"""
        tool_call = request.tool_call
        tool_name = tool_call.get("name")
        args = tool_call.get("args", {})

        if tool_name == self.TOOL_GREP_SEARCH:
            result = self._grep_search_impl(
                SearchPath=args.get("SearchPath", ""),
                Query=args.get("Query", ""),
                CaseSensitive=args.get("CaseSensitive", False),
                FixedStrings=args.get("FixedStrings", False),
                Includes=args.get("Includes"),
                MatchPerLine=args.get("MatchPerLine", False),
            )
            return ToolMessage(content=result, tool_call_id=tool_call.get("id", ""))

        elif tool_name == self.TOOL_FIND_BY_NAME:
            result = self._find_by_name_impl(
                SearchDirectory=args.get("SearchDirectory", ""),
                Pattern=args.get("Pattern", ""),
                Extensions=args.get("Extensions"),
                Type=args.get("Type", "any"),
                MaxDepth=args.get("MaxDepth"),
                FullPath=args.get("FullPath", False),
            )
            return ToolMessage(content=result, tool_call_id=tool_call.get("id", ""))

        return await handler(request)


__all__ = ["SearchMiddleware"]
