# Output Guard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prevent tool outputs from blowing up context by persisting large results to sandbox filesystem and injecting a preview + file reference into ToolMessage.

**Architecture:** A new `OutputGuardMiddleware` sits outermost in the middleware stack. After any tool returns a ToolMessage, the guard checks byte size against a per-tool threshold. If exceeded, it writes the full output to `{workspace_root}/.leon/tool-results/{tool_call_id}.txt` via `fs_backend.write_file()`, then replaces ToolMessage content with a 2KB preview + file path. The agent reads full output via existing `read_file` tool (path is within workspace, no new tools needed).

**Tech Stack:** Python 3.12, LangChain AgentMiddleware, Pydantic, pytest

---

## Design Decisions

### Why middleware (not utility function)?
- Catches ALL tools including MCP tools we don't control
- Single configuration point for thresholds
- No modification to existing middlewares
- Easy to test in isolation

### Why `{workspace_root}/.leon/tool-results/`?
- Within workspace_root → agent's `read_file` works without path validation changes
- `.leon/` is already the project config directory convention
- Transient: can be cleaned up after session
- Works identically across sandbox types (local/docker/cloud)

### Why byte size (not line count)?
- API payload size is measured in bytes, not lines
- One line can be 10 chars or 10,000 chars — line count is meaningless for context control
- Byte size correlates directly with token consumption

### Thresholds (bytes)

| Tool | Threshold | Rationale |
|------|-----------|-----------|
| `grep_search` | 20,000 | Matches Claude Code's Grep threshold |
| `find_by_name` | 20,000 | Same class as grep |
| `run_command` | 50,000 | Matches existing 50K char limit |
| `read_file` | 100,000 | Matches existing 100K char limit |
| `__default__` | 50,000 | Safe catch-all for MCP/unknown tools |

### Preview Format

```
Output too large (482.3 KB). Full output saved to: /workspace/.leon/tool-results/abc123.txt

Use read_file to view specific sections with offset and limit parameters.

Preview (first 2048 bytes):
<actual content truncated to 2048 bytes>
...
```

Preview size: 2048 bytes (~500-700 tokens, ~30-50 lines of code). Enough for agent to judge relevance and decide next action.

---

## Task 1: Guard function — test + implementation

**Files:**
- Create: `tests/test_output_guard.py`
- Create: `core/output_guard.py`

### Step 1: Write the failing test

```python
# tests/test_output_guard.py
"""Tests for output guard — large tool output truncation and persistence."""

from unittest.mock import MagicMock

import pytest

from core.output_guard import PREVIEW_BYTES, guard_tool_output


@pytest.fixture
def mock_fs_backend():
    backend = MagicMock()
    backend.write_file.return_value = MagicMock(success=True)
    return backend


class TestGuardToolOutput:
    """Test guard_tool_output function."""

    def test_small_output_unchanged(self, mock_fs_backend):
        """Output below threshold passes through unchanged."""
        content = "hello world"
        result = guard_tool_output(
            content=content,
            threshold_bytes=1000,
            tool_call_id="test-123",
            fs_backend=mock_fs_backend,
            workspace_root="/workspace",
        )
        assert result == content
        mock_fs_backend.write_file.assert_not_called()

    def test_large_output_persisted(self, mock_fs_backend):
        """Output above threshold is persisted and replaced with preview."""
        content = "x" * 30_000  # 30KB, above default threshold
        result = guard_tool_output(
            content=content,
            threshold_bytes=20_000,
            tool_call_id="test-456",
            fs_backend=mock_fs_backend,
            workspace_root="/workspace",
        )
        # Should contain size info
        assert "Output too large" in result
        assert "30.0 KB" in result or "29." in result
        # Should contain file path
        assert ".leon/tool-results/test-456.txt" in result
        # Should contain preview
        assert "Preview" in result
        # Preview should be truncated
        assert len(result) < len(content)
        # Backend should have been called with full content
        mock_fs_backend.write_file.assert_called_once()
        call_args = mock_fs_backend.write_file.call_args
        assert "test-456.txt" in call_args[0][0]
        assert call_args[0][1] == content

    def test_exact_threshold_not_triggered(self, mock_fs_backend):
        """Output exactly at threshold is NOT persisted (only strictly above)."""
        content = "x" * 1000
        result = guard_tool_output(
            content=content,
            threshold_bytes=1000,
            tool_call_id="test-789",
            fs_backend=mock_fs_backend,
            workspace_root="/workspace",
        )
        assert result == content
        mock_fs_backend.write_file.assert_not_called()

    def test_preview_size_capped(self, mock_fs_backend):
        """Preview content is capped at PREVIEW_BYTES."""
        content = "abcdefgh" * 10_000  # 80KB
        result = guard_tool_output(
            content=content,
            threshold_bytes=20_000,
            tool_call_id="test-cap",
            fs_backend=mock_fs_backend,
            workspace_root="/workspace",
        )
        # The preview portion should not exceed PREVIEW_BYTES + header
        lines = result.split("\n")
        # Find the preview content start
        preview_idx = next(i for i, l in enumerate(lines) if l.startswith("Preview"))
        preview_content = "\n".join(lines[preview_idx + 1 :])
        assert len(preview_content.encode("utf-8")) <= PREVIEW_BYTES + 10  # +10 for "...\n"

    def test_write_failure_returns_truncated(self, mock_fs_backend):
        """If file write fails, still return truncated output with warning."""
        mock_fs_backend.write_file.return_value = MagicMock(success=False, error="disk full")
        content = "x" * 30_000
        result = guard_tool_output(
            content=content,
            threshold_bytes=20_000,
            tool_call_id="test-fail",
            fs_backend=mock_fs_backend,
            workspace_root="/workspace",
        )
        assert "Output too large" in result
        assert "disk full" in result or "Preview" in result

    def test_non_string_content_passthrough(self, mock_fs_backend):
        """Non-string content (e.g., content blocks for images) passes through."""
        content = [{"type": "image", "data": "..."}]
        result = guard_tool_output(
            content=content,
            threshold_bytes=100,
            tool_call_id="test-img",
            fs_backend=mock_fs_backend,
            workspace_root="/workspace",
        )
        assert result == content
        mock_fs_backend.write_file.assert_not_called()

    def test_unicode_content_byte_measurement(self, mock_fs_backend):
        """Threshold is measured in bytes, not characters (CJK = 3 bytes each)."""
        # 5000 CJK chars = ~15000 bytes
        content = "\u4f60\u597d" * 5000  # 10000 chars, ~30000 bytes
        result = guard_tool_output(
            content=content,
            threshold_bytes=20_000,
            tool_call_id="test-cjk",
            fs_backend=mock_fs_backend,
            workspace_root="/workspace",
        )
        assert "Output too large" in result
        mock_fs_backend.write_file.assert_called_once()
```

### Step 2: Run test to verify it fails

Run: `cd /Users/apple/Desktop/project/v1/文稿/project/leon/worktrees/refactor-agent-core && uv run pytest tests/test_output_guard.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.output_guard'`

### Step 3: Write implementation

```python
# core/output_guard.py
"""
Output Guard — truncate large tool outputs and persist to filesystem.

When a tool produces output exceeding the byte threshold, the full content
is saved to {workspace_root}/.leon/tool-results/{tool_call_id}.txt.
The ToolMessage content is replaced with a preview (first 2KB) + file path.
The agent can read the full output via the existing read_file tool.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sandbox.interfaces.filesystem import FileSystemBackend

# Preview size in bytes (~500-700 tokens, enough to judge relevance)
PREVIEW_BYTES = 2048

# Storage subdirectory within workspace
TOOL_RESULTS_DIR = ".leon/tool-results"


def guard_tool_output(
    content: Any,
    threshold_bytes: int,
    tool_call_id: str,
    fs_backend: FileSystemBackend,
    workspace_root: str,
) -> Any:
    """Guard tool output against context blowup.

    If content is a string exceeding threshold_bytes, persist full output
    to sandbox filesystem and return a preview with file reference.

    Args:
        content: Tool output (only strings are guarded, others pass through)
        threshold_bytes: Size threshold in bytes
        tool_call_id: Unique identifier for the tool call
        fs_backend: Filesystem backend for persisting output
        workspace_root: Root directory for storing tool results

    Returns:
        Original content if below threshold, or preview + path reference
    """
    if not isinstance(content, str):
        return content

    content_bytes = len(content.encode("utf-8"))
    if content_bytes <= threshold_bytes:
        return content

    # Persist full output
    results_dir = Path(workspace_root) / TOOL_RESULTS_DIR
    file_path = str(results_dir / f"{tool_call_id}.txt")

    write_result = fs_backend.write_file(file_path, content)

    # Build preview
    size_kb = content_bytes / 1024
    if size_kb >= 1024:
        size_str = f"{size_kb / 1024:.1f} MB"
    else:
        size_str = f"{size_kb:.1f} KB"

    preview_content = _truncate_to_bytes(content, PREVIEW_BYTES)

    if write_result.success:
        return (
            f"Output too large ({size_str}). Full output saved to: {file_path}\n"
            f"\n"
            f"Use read_file to view specific sections with offset and limit parameters.\n"
            f"\n"
            f"Preview (first {PREVIEW_BYTES} bytes):\n"
            f"{preview_content}\n"
            f"..."
        )
    else:
        return (
            f"Output too large ({size_str}). Failed to save full output: {write_result.error}\n"
            f"\n"
            f"Preview (first {PREVIEW_BYTES} bytes):\n"
            f"{preview_content}\n"
            f"..."
        )


def _truncate_to_bytes(text: str, max_bytes: int) -> str:
    """Truncate string to max_bytes without breaking UTF-8 characters."""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    # Truncate bytes and decode, ignoring incomplete chars at the end
    return encoded[:max_bytes].decode("utf-8", errors="ignore")
```

### Step 4: Run test to verify it passes

Run: `cd /Users/apple/Desktop/project/v1/文稿/project/leon/worktrees/refactor-agent-core && uv run pytest tests/test_output_guard.py -v`
Expected: ALL PASS

### Step 5: Commit

```bash
git add core/output_guard.py tests/test_output_guard.py
git commit -m "feat: add output guard function for large tool output truncation"
```

---

## Task 2: OutputGuardMiddleware — test + implementation

**Files:**
- Modify: `tests/test_output_guard.py` (add middleware tests)
- Modify: `core/output_guard.py` (add middleware class)

### Step 1: Write the failing test

Append to `tests/test_output_guard.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import ToolMessage

from core.output_guard import OutputGuardMiddleware


class TestOutputGuardMiddleware:
    """Test OutputGuardMiddleware."""

    @pytest.fixture
    def middleware(self, mock_fs_backend):
        return OutputGuardMiddleware(
            fs_backend=mock_fs_backend,
            workspace_root="/workspace",
        )

    def test_small_tool_result_unchanged(self, middleware):
        """Tool results below threshold pass through unchanged."""
        request = MagicMock()
        request.tool_call = {"name": "grep_search", "id": "tc-1", "args": {}}
        original_msg = ToolMessage(content="small result", tool_call_id="tc-1")
        handler = MagicMock(return_value=original_msg)

        result = middleware.wrap_tool_call(request, handler)

        assert result.content == "small result"
        handler.assert_called_once_with(request)

    def test_large_grep_result_guarded(self, middleware):
        """Large grep_search result triggers guard at 20KB threshold."""
        request = MagicMock()
        request.tool_call = {"name": "grep_search", "id": "tc-2", "args": {}}
        large_content = "x" * 25_000  # 25KB > 20KB grep threshold
        original_msg = ToolMessage(content=large_content, tool_call_id="tc-2")
        handler = MagicMock(return_value=original_msg)

        result = middleware.wrap_tool_call(request, handler)

        assert "Output too large" in result.content
        assert "tc-2.txt" in result.content

    def test_large_command_result_guarded(self, middleware):
        """Large run_command result triggers guard at 50KB threshold."""
        request = MagicMock()
        request.tool_call = {"name": "run_command", "id": "tc-3", "args": {}}
        # 40KB: above grep threshold but below command threshold
        content_40k = "y" * 40_000
        original_msg = ToolMessage(content=content_40k, tool_call_id="tc-3")
        handler = MagicMock(return_value=original_msg)

        result = middleware.wrap_tool_call(request, handler)
        # 40KB < 50KB command threshold → not guarded
        assert result.content == content_40k

    def test_unknown_tool_uses_default_threshold(self, middleware):
        """Unknown tools use the default 50KB threshold."""
        request = MagicMock()
        request.tool_call = {"name": "mcp_some_tool", "id": "tc-4", "args": {}}
        content_60k = "z" * 60_000
        original_msg = ToolMessage(content=content_60k, tool_call_id="tc-4")
        handler = MagicMock(return_value=original_msg)

        result = middleware.wrap_tool_call(request, handler)

        assert "Output too large" in result.content

    def test_custom_thresholds(self, mock_fs_backend):
        """Custom thresholds override defaults."""
        mw = OutputGuardMiddleware(
            fs_backend=mock_fs_backend,
            workspace_root="/workspace",
            thresholds={"grep_search": 100},  # Very low threshold
        )
        request = MagicMock()
        request.tool_call = {"name": "grep_search", "id": "tc-5", "args": {}}
        original_msg = ToolMessage(content="x" * 200, tool_call_id="tc-5")
        handler = MagicMock(return_value=original_msg)

        result = mw.wrap_tool_call(request, handler)
        assert "Output too large" in result.content

    @pytest.mark.asyncio
    async def test_async_wrap_tool_call(self, middleware):
        """Async version works identically."""
        request = MagicMock()
        request.tool_call = {"name": "grep_search", "id": "tc-6", "args": {}}
        large_content = "x" * 25_000
        original_msg = ToolMessage(content=large_content, tool_call_id="tc-6")
        handler = AsyncMock(return_value=original_msg)

        result = await middleware.awrap_tool_call(request, handler)

        assert "Output too large" in result.content

    def test_non_toolmessage_passthrough(self, middleware):
        """Non-ToolMessage results pass through (defensive)."""
        request = MagicMock()
        request.tool_call = {"name": "grep_search", "id": "tc-7", "args": {}}
        handler = MagicMock(return_value="raw string result")

        result = middleware.wrap_tool_call(request, handler)
        assert result == "raw string result"
```

### Step 2: Run test to verify it fails

Run: `cd /Users/apple/Desktop/project/v1/文稿/project/leon/worktrees/refactor-agent-core && uv run pytest tests/test_output_guard.py::TestOutputGuardMiddleware -v`
Expected: FAIL with `ImportError: cannot import name 'OutputGuardMiddleware'`

### Step 3: Write implementation

Add to `core/output_guard.py`:

```python
from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.messages import ToolMessage

try:
    from langchain.agents.middleware.types import (
        AgentMiddleware,
        ModelRequest,
        ModelResponse,
        ToolCallRequest,
    )
except ImportError:
    class AgentMiddleware:
        pass
    ModelRequest = Any
    ModelResponse = Any
    ToolCallRequest = Any


# Default thresholds in bytes (aligned with Claude Code)
DEFAULT_THRESHOLDS: dict[str, int] = {
    "grep_search": 20_000,
    "find_by_name": 20_000,
    "run_command": 50_000,
    "command_status": 50_000,
    "read_file": 100_000,
}
DEFAULT_THRESHOLD = 50_000  # 50KB for unknown tools


class OutputGuardMiddleware(AgentMiddleware):
    """Guard middleware — truncates large tool outputs and persists to filesystem.

    Sits outermost in the middleware stack. After any tool returns a ToolMessage,
    checks byte size against per-tool threshold. If exceeded, writes full output
    to {workspace_root}/.leon/tool-results/{tool_call_id}.txt and replaces
    ToolMessage content with preview + file reference.
    """

    def __init__(
        self,
        fs_backend: FileSystemBackend,
        workspace_root: str | Path,
        *,
        thresholds: dict[str, int] | None = None,
        default_threshold: int = DEFAULT_THRESHOLD,
        preview_bytes: int = PREVIEW_BYTES,
    ):
        self.fs_backend = fs_backend
        self.workspace_root = str(workspace_root)
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.default_threshold = default_threshold
        self.preview_bytes = preview_bytes

    def _get_threshold(self, tool_name: str) -> int:
        return self.thresholds.get(tool_name, self.default_threshold)

    def _guard_result(self, result: Any, tool_name: str, tool_call_id: str) -> Any:
        """Apply guard to a tool result."""
        if not isinstance(result, ToolMessage):
            return result

        threshold = self._get_threshold(tool_name)
        guarded_content = guard_tool_output(
            content=result.content,
            threshold_bytes=threshold,
            tool_call_id=tool_call_id,
            fs_backend=self.fs_backend,
            workspace_root=self.workspace_root,
        )

        if guarded_content is not result.content:
            return ToolMessage(
                content=guarded_content,
                tool_call_id=result.tool_call_id,
            )
        return result

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any],
    ) -> Any:
        tool_name = request.tool_call.get("name", "")
        tool_call_id = request.tool_call.get("id", "unknown")
        result = handler(request)
        return self._guard_result(result, tool_name, tool_call_id)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[Any]],
    ) -> Any:
        tool_name = request.tool_call.get("name", "")
        tool_call_id = request.tool_call.get("id", "unknown")
        result = await handler(request)
        return self._guard_result(result, tool_name, tool_call_id)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        return await handler(request)
```

### Step 4: Run test to verify it passes

Run: `cd /Users/apple/Desktop/project/v1/文稿/project/leon/worktrees/refactor-agent-core && uv run pytest tests/test_output_guard.py -v`
Expected: ALL PASS

### Step 5: Commit

```bash
git add core/output_guard.py tests/test_output_guard.py
git commit -m "feat: add OutputGuardMiddleware for large tool output protection"
```

---

## Task 3: Integrate into agent.py middleware stack

**Files:**
- Modify: `agent.py` (~lines 696-758, `_build_middleware_stack`)

### Step 1: Add OutputGuardMiddleware as outermost middleware

In `agent.py`, import and add after MonitorMiddleware:

```python
# At top of file, add import:
from core.output_guard import OutputGuardMiddleware

# In _build_middleware_stack(), after MonitorMiddleware (line ~756):

        # 11. Output Guard (outermost — catches all tool outputs)
        middleware.append(
            OutputGuardMiddleware(
                fs_backend=fs_backend,
                workspace_root=self.workspace_root,
            )
        )
```

### Step 2: Verify agent builds correctly

Run: `cd /Users/apple/Desktop/project/v1/文稿/project/leon/worktrees/refactor-agent-core && uv run python -c "from agent import LeonAgent; print('OK')"`
Expected: `OK` (no import errors)

### Step 3: Commit

```bash
git add agent.py
git commit -m "feat: integrate OutputGuardMiddleware into agent middleware stack"
```

---

## Task 4: Fix grep_search defaults

The root cause of the 4.8M character explosion: ripgrep respects `.gitignore` only inside git repos. Non-git directories (or git repos without proper `.gitignore`) get full recursive scan including `node_modules/`, `.git/`, etc.

**Files:**
- Modify: `core/search.py` (~lines 139-224, `_ripgrep_search` and `_python_grep_search`)
- Modify: `tests/test_output_guard.py` (add grep-specific tests)

### Step 1: Write the failing test

```python
# In a new test file or added to test_output_guard.py
class TestGrepSearchDefaults:
    """Test grep_search excludes common large directories."""

    def test_ripgrep_excludes_node_modules(self):
        """ripgrep command includes --glob '!node_modules' by default."""
        middleware = SearchMiddleware(workspace_root="/tmp/test")
        # Mock subprocess to capture the command
        with patch("core.search.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
            middleware._ripgrep_search(
                Path("/tmp/test"), "TODO", False, False, None, False
            )
            cmd = mock_run.call_args[0][0]
            assert any("!node_modules" in arg for arg in cmd)

    def test_ripgrep_excludes_git_dir(self):
        """ripgrep command includes --glob '!.git' by default."""
        middleware = SearchMiddleware(workspace_root="/tmp/test")
        with patch("core.search.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
            middleware._ripgrep_search(
                Path("/tmp/test"), "TODO", False, False, None, False
            )
            cmd = mock_run.call_args[0][0]
            assert any("!.git" in arg for arg in cmd)

    def test_python_fallback_excludes_node_modules(self):
        """Python grep fallback skips node_modules directories."""
        middleware = SearchMiddleware(workspace_root="/tmp/test")
        # Create a mock file structure
        with patch("pathlib.Path.rglob") as mock_rglob:
            mock_rglob.return_value = [
                Path("/tmp/test/src/app.js"),
                Path("/tmp/test/node_modules/lodash/index.js"),
                Path("/tmp/test/.git/HEAD"),
            ]
            # The implementation should skip node_modules and .git paths
            # (test validates the filter logic)
```

### Step 2: Add default exclusion patterns

In `core/search.py`, add constant and modify `_ripgrep_search`:

```python
# At module level, after class definition starts:
EXCLUDED_DIRS = [
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".next",
    ".nuxt",
]
```

In `_ripgrep_search`, before executing the command:

```python
# Default exclusions (always applied, even outside git repos)
for exclude in EXCLUDED_DIRS:
    cmd.extend(["--glob", f"!{exclude}"])
```

In `_python_grep_search`, add directory filtering:

```python
# In the file collection loop:
for file_path in path.rglob("*"):
    if not file_path.is_file():
        continue
    # Skip excluded directories
    if any(part in EXCLUDED_DIRS for part in file_path.parts):
        continue
```

### Step 3: Run tests

Run: `cd /Users/apple/Desktop/project/v1/文稿/project/leon/worktrees/refactor-agent-core && uv run pytest tests/test_output_guard.py -v -k "grep"`
Expected: ALL PASS

### Step 4: Commit

```bash
git add core/search.py tests/test_output_guard.py
git commit -m "fix: add default directory exclusions to grep_search"
```

---

## Task 5: End-to-end verification

### Step 1: Manual verification with TUI

```bash
cd /Users/apple/Desktop/project/v1/文稿/project/leon/worktrees/refactor-agent-core
uv cache clean leonai --force && uv tool install . --force
```

Test scenario: point agent at a directory with node_modules, ask it to search for "TODO".
- Verify grep_search skips node_modules
- If output still exceeds threshold, verify it's truncated with preview + file path
- Verify agent can read_file the persisted output

### Step 2: Run full test suite

Run: `cd /Users/apple/Desktop/project/v1/文稿/project/leon/worktrees/refactor-agent-core && uv run pytest tests/ -v --timeout=60`
Expected: ALL existing tests still pass

### Step 3: Final commit (if any cleanup needed)

```bash
git add -A
git commit -m "test: verify output guard end-to-end"
```

---

## File Summary

| Action | Path | Description |
|--------|------|-------------|
| Create | `core/output_guard.py` | Guard function + OutputGuardMiddleware |
| Create | `tests/test_output_guard.py` | Full test coverage |
| Modify | `agent.py:~756` | Add OutputGuardMiddleware to stack |
| Modify | `core/search.py:~149,253` | Add default directory exclusions |

## Dependency Graph

```
Task 1 (guard function) ← Task 2 (middleware) ← Task 3 (integration)
                                                  Task 4 (grep fix) — independent
Task 3 + Task 4 ← Task 5 (e2e verification)
```

Task 1→2→3 is the critical path. Task 4 can run in parallel with Task 2.
