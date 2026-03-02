"""
Search Middleware - Grep + Glob tools aligned to Claude Code design.

Tools:
- Grep: Content search using regex (ripgrep preferred, Python fallback)
- Glob: File pattern matching sorted by modification time (Python Path.glob)

Design:
- Parameter names mirror rg CLI flags for Grep
- DEFAULT_EXCLUDES applied automatically (node_modules, .git, etc.)
- output_mode controls Grep output format (files_with_matches | content | count)
- head_limit / offset for pagination of results
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

# Directories excluded by default from both Grep and Glob searches.
DEFAULT_EXCLUDES: list[str] = [
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
]


class SearchMiddleware(AgentMiddleware):
    """Search middleware providing Grep and Glob tools.

    - Grep: regex content search (ripgrep with Python fallback)
    - Glob: file pattern matching sorted by mtime descending
    """

    TOOL_GREP = "Grep"
    TOOL_GLOB = "Glob"

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        max_file_size: int = 10 * 1024 * 1024,
        verbose: bool = True,
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.max_file_size = max_file_size
        self.verbose = verbose

        self.has_ripgrep = shutil.which("rg") is not None

        if self.verbose:
            print(f"[SearchMiddleware] workspace: {self.workspace_root}")
            print(f"[SearchMiddleware] ripgrep: {self.has_ripgrep}")

    # ------------------------------------------------------------------
    # Path validation
    # ------------------------------------------------------------------

    def _validate_path(self, path: str | None) -> tuple[bool, str, Path]:
        """Validate and resolve a search path.

        If *path* is ``None`` or empty, defaults to ``workspace_root``.
        Returns ``(ok, error_message, resolved_path)``.
        """
        if not path:
            return True, "", self.workspace_root

        if not Path(path).is_absolute():
            return False, f"Path must be absolute: {path}", self.workspace_root

        try:
            resolved = Path(path).resolve()
        except Exception as e:
            return False, f"Invalid path: {path} ({e})", self.workspace_root

        try:
            resolved.relative_to(self.workspace_root)
        except ValueError:
            return (
                False,
                f"Path outside workspace\n  Workspace: {self.workspace_root}\n  Attempted: {resolved}",
                self.workspace_root,
            )

        return True, "", resolved

    # ------------------------------------------------------------------
    # Grep implementation
    # ------------------------------------------------------------------

    def _grep_impl(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
        type: str | None = None,
        case_insensitive: bool = False,
        after_context: int | None = None,
        before_context: int | None = None,
        context: int | None = None,
        output_mode: str = "files_with_matches",
        head_limit: int | None = None,
        offset: int | None = None,
        multiline: bool = False,
    ) -> str:
        ok, error, resolved = self._validate_path(path)
        if not ok:
            return error

        if not resolved.exists():
            return f"Path not found: {path or self.workspace_root}"

        if self.has_ripgrep:
            try:
                return self._ripgrep_search(
                    resolved,
                    pattern,
                    glob=glob,
                    type_filter=type,
                    case_insensitive=case_insensitive,
                    after_context=after_context,
                    before_context=before_context,
                    context=context,
                    output_mode=output_mode,
                    head_limit=head_limit,
                    offset=offset,
                    multiline=multiline,
                )
            except Exception as e:
                if self.verbose:
                    print(f"[SearchMiddleware] ripgrep failed, fallback to Python: {e}")

        return self._python_grep(
            resolved,
            pattern,
            glob=glob,
            case_insensitive=case_insensitive,
            output_mode=output_mode,
            head_limit=head_limit,
            offset=offset,
        )

    def _ripgrep_search(
        self,
        path: Path,
        pattern: str,
        *,
        glob: str | None,
        type_filter: str | None,
        case_insensitive: bool,
        after_context: int | None,
        before_context: int | None,
        context: int | None,
        output_mode: str,
        head_limit: int | None,
        offset: int | None,
        multiline: bool,
    ) -> str:
        cmd: list[str] = ["rg", pattern, str(path)]

        # Default excludes
        for excl in DEFAULT_EXCLUDES:
            cmd.extend(["--glob", f"!{excl}"])

        # File glob filter
        if glob:
            cmd.extend(["--glob", glob])

        # File type filter
        if type_filter:
            cmd.extend(["--type", type_filter])

        # Case insensitivity
        if case_insensitive:
            cmd.append("-i")

        # Multiline
        if multiline:
            cmd.extend(["-U", "--multiline-dotall"])

        # Output mode
        if output_mode == "files_with_matches":
            cmd.append("--files-with-matches")
        elif output_mode == "count":
            cmd.append("--count")
        elif output_mode == "content":
            cmd.extend(["--line-number", "--no-heading"])
            if context is not None:
                cmd.extend(["-C", str(context)])
            else:
                if after_context is not None:
                    cmd.extend(["-A", str(after_context)])
                if before_context is not None:
                    cmd.extend(["-B", str(before_context)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.workspace_root),
            )
        except subprocess.TimeoutExpired:
            return "Search timeout (30s)"

        if result.returncode not in (0, 1):
            return f"ripgrep error: {result.stderr.strip()}"

        output = result.stdout.strip()
        if not output:
            return "No matches found"

        return self._paginate(output, head_limit, offset)

    def _python_grep(
        self,
        path: Path,
        pattern: str,
        *,
        glob: str | None,
        case_insensitive: bool,
        output_mode: str,
        head_limit: int | None,
        offset: int | None,
    ) -> str:
        """Pure-Python fallback for grep search."""
        flags = re.IGNORECASE if case_insensitive else 0
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return f"Invalid regex: {e}"

        files = self._collect_files(path, glob)
        lines: list[str] = []

        for fp in files:
            try:
                text = fp.read_text(encoding="utf-8", errors="ignore")
            except (PermissionError, OSError):
                continue

            if output_mode == "files_with_matches":
                if regex.search(text):
                    lines.append(str(fp))
            elif output_mode == "count":
                cnt = len(regex.findall(text))
                if cnt:
                    lines.append(f"{fp}:{cnt}")
            else:  # content
                for i, line in enumerate(text.splitlines(), 1):
                    if regex.search(line):
                        lines.append(f"{fp}:{i}:{line}")

        if not lines:
            return "No matches found"

        return self._paginate("\n".join(lines), head_limit, offset)

    # ------------------------------------------------------------------
    # Glob implementation
    # ------------------------------------------------------------------

    def _glob_impl(self, pattern: str, path: str | None = None) -> str:
        ok, error, resolved = self._validate_path(path)
        if not ok:
            return error

        if not resolved.exists():
            return f"Path not found: {path or self.workspace_root}"

        if not resolved.is_dir():
            return f"Not a directory: {resolved}"

        matches: list[tuple[float, str]] = []
        for p in resolved.glob(pattern):
            if not p.is_file():
                continue
            if self._is_excluded(p):
                continue
            try:
                mtime = p.stat().st_mtime
            except OSError:
                mtime = 0.0
            matches.append((mtime, str(p)))

        if not matches:
            return "No files found"

        # Sort by mtime descending (newest first)
        matches.sort(key=lambda x: x[0], reverse=True)
        return "\n".join(filepath for _, filepath in matches)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_excluded(p: Path) -> bool:
        """Return True if any path component is in DEFAULT_EXCLUDES."""
        parts = p.parts
        return any(part in DEFAULT_EXCLUDES for part in parts)

    def _collect_files(self, path: Path, glob_pattern: str | None) -> list[Path]:
        """Collect files under *path*, applying glob and exclude filters."""
        if path.is_file():
            return [path]

        files: list[Path] = []
        for fp in path.rglob(glob_pattern or "*"):
            if not fp.is_file():
                continue
            if self._is_excluded(fp):
                continue
            if fp.stat().st_size > self.max_file_size:
                continue
            files.append(fp)
        return files

    @staticmethod
    def _paginate(output: str, head_limit: int | None, offset: int | None) -> str:
        """Apply offset and head_limit to line-based output."""
        lines = output.split("\n")
        start = offset or 0
        if start:
            lines = lines[start:]
        if head_limit and head_limit > 0:
            lines = lines[:head_limit]
        return "\n".join(lines) if lines else "No matches found"

    # ------------------------------------------------------------------
    # Tool schemas
    # ------------------------------------------------------------------

    def _get_tool_schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": self.TOOL_GREP,
                    "description": "Search file contents using regex patterns. Use this instead of running grep/rg via run_command.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "Regex pattern to search for",
                            },
                            "path": {
                                "type": "string",
                                "description": "File or directory (absolute). Defaults to workspace.",
                            },
                            "glob": {
                                "type": "string",
                                "description": "Filter files by glob (e.g., '*.py')",
                            },
                            "type": {
                                "type": "string",
                                "description": "Filter by file type (e.g., 'py', 'js')",
                            },
                            "case_insensitive": {
                                "type": "boolean",
                                "description": "Case insensitive search",
                            },
                            "after_context": {
                                "type": "integer",
                                "description": "Lines to show after each match",
                            },
                            "before_context": {
                                "type": "integer",
                                "description": "Lines to show before each match",
                            },
                            "context": {
                                "type": "integer",
                                "description": "Context lines before and after each match",
                            },
                            "output_mode": {
                                "type": "string",
                                "enum": ["content", "files_with_matches", "count"],
                                "description": "Output format. Default: files_with_matches",
                            },
                            "head_limit": {
                                "type": "integer",
                                "description": "Limit to first N entries",
                            },
                            "offset": {
                                "type": "integer",
                                "description": "Skip first N entries",
                            },
                            "multiline": {
                                "type": "boolean",
                                "description": "Allow pattern to span multiple lines",
                            },
                        },
                        "required": ["pattern"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": self.TOOL_GLOB,
                    "description": "Find files by glob pattern. Returns paths sorted by modification time.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "Glob pattern (e.g., '**/*.py')",
                            },
                            "path": {
                                "type": "string",
                                "description": "Directory to search (absolute). Defaults to workspace.",
                            },
                        },
                        "required": ["pattern"],
                    },
                },
            },
        ]

    # ------------------------------------------------------------------
    # Middleware interface
    # ------------------------------------------------------------------

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        tools = list(request.tools or [])
        tools.extend(self._get_tool_schemas())
        return handler(request.override(tools=tools))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        tools = list(request.tools or [])
        tools.extend(self._get_tool_schemas())
        return await handler(request.override(tools=tools))

    def _handle_tool(self, tool_call: dict) -> ToolMessage | None:
        """Dispatch a tool call. Returns ToolMessage if handled, else None."""
        name = tool_call.get("name")
        args = tool_call.get("args", {})
        call_id = tool_call.get("id", "")

        if name == self.TOOL_GREP:
            result = self._grep_impl(
                pattern=args.get("pattern", ""),
                path=args.get("path"),
                glob=args.get("glob"),
                type=args.get("type"),
                case_insensitive=args.get("case_insensitive", False),
                after_context=args.get("after_context"),
                before_context=args.get("before_context"),
                context=args.get("context"),
                output_mode=args.get("output_mode", "files_with_matches"),
                head_limit=args.get("head_limit"),
                offset=args.get("offset"),
                multiline=args.get("multiline", False),
            )
            return ToolMessage(content=result, tool_call_id=call_id)

        if name == self.TOOL_GLOB:
            result = self._glob_impl(
                pattern=args.get("pattern", ""),
                path=args.get("path"),
            )
            return ToolMessage(content=result, tool_call_id=call_id)

        return None

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any],
    ) -> Any:
        msg = self._handle_tool(request.tool_call)
        if msg is not None:
            return msg
        return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[Any]],
    ) -> Any:
        msg = self._handle_tool(request.tool_call)
        if msg is not None:
            return msg
        return await handler(request)


__all__ = ["SearchMiddleware", "DEFAULT_EXCLUDES"]
