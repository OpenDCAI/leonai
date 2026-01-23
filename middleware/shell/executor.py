"""
Shell Executor - 基于插件系统的 Shell 中间件

通过 hook 插件系统扩展 shell 功能，添加新功能只需在 hooks/ 目录下创建新的 .py 文件。
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from langchain.agents.middleware.shell_tool import ShellToolMiddleware
from langchain.agents.middleware.types import (
    ModelRequest,
    ModelResponse,
    ToolCallRequest,
)

from .hooks import BashHook, HookResult, load_hooks

BASH_TOOL_TYPE = "bash_20250124"
BASH_TOOL_NAME = "bash"


class ShellMiddleware(ShellToolMiddleware):
    """
    可扩展的 Shell Middleware - 基于插件系统

    特点：
    - 自动加载 hooks/ 目录下的所有插件
    - 插件按 priority 顺序执行
    - 任何插件返回 block 即停止执行
    - 支持命令前后的回调 hooks

    添加新功能：
    1. 在 middleware/shell/hooks/ 目录下创建新的 .py 文件
    2. 继承 BashHook 基类
    3. 实现 check_command 方法
    4. 重启 agent，插件自动加载
    """

    def __init__(
        self,
        workspace_root: str | None = None,
        *,
        startup_commands: tuple[str, ...] | list[str] | str | None = None,
        shutdown_commands: tuple[str, ...] | list[str] | str | None = None,
        allow_system_python: bool = True,
        env: dict[str, Any] | None = None,
        hooks_dir: str | Path | None = None,
        hook_config: dict[str, Any] | None = None,
    ) -> None:
        """
        初始化可扩展 Shell middleware

        Args:
            workspace_root: 工作目录
            startup_commands: 启动时执行的命令
            shutdown_commands: 关闭时执行的命令
            allow_system_python: 是否允许使用系统 Python
            env: 环境变量
            hooks_dir: hooks 目录路径（默认为 hooks/）
            hook_config: 传递给 hooks 的配置参数
        """
        if workspace_root is None:
            raise ValueError("workspace_root must be specified for ShellMiddleware")

        self.workspace_root = Path(workspace_root).resolve()

        # 如果允许系统 Python，设置 PATH
        if allow_system_python and env is None:
            env = {"PATH": os.environ.get("PATH", "")}

        # 默认启动命令
        if startup_commands is None:
            startup_commands = [
                f"echo '🔧 Shell workspace initialized at: {self.workspace_root}'",
            ]

            if allow_system_python:
                startup_commands.append("which python3 && python3 --version || echo 'Python not found'")

        super().__init__(
            workspace_root=str(self.workspace_root),
            startup_commands=startup_commands,
            shutdown_commands=shutdown_commands,
            execution_policy=None,
            redaction_rules=None,
            tool_description=(
                f"Execute bash commands within workspace: {self.workspace_root}\n"
                "Commands are validated by security hooks before execution."
            ),
            tool_name=BASH_TOOL_NAME,
            shell_command=("/bin/bash",),
            env=env,
        )

        # 加载所有 hooks
        hook_config = hook_config or {}
        self.hooks: list[BashHook] = load_hooks(
            hooks_dir=hooks_dir,
            workspace_root=self.workspace_root,
            **hook_config,
        )

        print(f"[Shell] Loaded {len(self.hooks)} hooks: {[h.name for h in self.hooks]}")

    def _check_command_with_hooks(
        self,
        command: str,
        context: dict[str, Any],
    ) -> tuple[bool, str]:
        """
        使用所有 hooks 检查命令

        Returns:
            (is_allowed, error_message)
        """
        for hook in self.hooks:
            if not hook.enabled:
                continue

            try:
                result: HookResult = hook.check_command(command, context)

                # 如果 hook 拦截了命令
                if not result.allow:
                    return False, result.error_message

                # 如果 hook 要求停止后续检查
                if not result.continue_chain:
                    break

            except Exception as e:
                print(f"[Shell] Hook {hook.name} error: {e}")
                # 继续执行其他 hooks
                continue

        # 所有 hooks 都通过
        return True, ""

    def _notify_hooks_success(
        self,
        command: str,
        output: str,
        context: dict[str, Any],
    ) -> None:
        """通知所有 hooks 命令执行成功"""
        for hook in self.hooks:
            if not hook.enabled:
                continue

            try:
                hook.on_command_success(command, output, context)
            except Exception as e:
                print(f"[Shell] Hook {hook.name} on_command_success error: {e}")

    def _notify_hooks_error(
        self,
        command: str,
        error: str,
        context: dict[str, Any],
    ) -> None:
        """通知所有 hooks 命令执行失败"""
        for hook in self.hooks:
            if not hook.enabled:
                continue

            try:
                hook.on_command_error(command, error, context)
            except Exception as e:
                print(f"[Shell] Hook {hook.name} on_command_error error: {e}")

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any],
    ) -> Any:
        """拦截并验证 bash 命令"""
        from langchain.agents.middleware.types import ToolMessage

        tool_call = request.tool_call

        if tool_call.get("name") == BASH_TOOL_NAME:
            command = tool_call.get("args", {}).get("command", "")

            # 构建上下文
            context = {
                "tool_call": tool_call,
                "request": request,
            }

            # 使用 hooks 检查命令
            is_allowed, error_msg = self._check_command_with_hooks(command, context)

            if not is_allowed:
                # 通知 hooks 命令被拦截
                self._notify_hooks_error(command, error_msg, context)

                # 返回错误消息
                return ToolMessage(
                    content=error_msg,
                    tool_call_id=tool_call.get("id", ""),
                    status="error",
                )

            # 执行命令
            result = handler(request)

            # 通知 hooks 命令执行成功
            if hasattr(result, "content"):
                self._notify_hooks_success(command, result.content, context)

            return result

        # 非 bash 命令，直接执行
        return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[Any]],
    ) -> Any:
        """异步：拦截并验证 bash 命令"""
        from langchain.agents.middleware.types import ToolMessage

        tool_call = request.tool_call

        if tool_call.get("name") == BASH_TOOL_NAME:
            command = tool_call.get("args", {}).get("command", "")

            # 构建上下文
            context = {
                "tool_call": tool_call,
                "request": request,
            }

            # 使用 hooks 检查命令
            is_allowed, error_msg = self._check_command_with_hooks(command, context)

            if not is_allowed:
                # 通知 hooks 命令被拦截
                self._notify_hooks_error(command, error_msg, context)

                # 返回错误消息
                return ToolMessage(
                    content=error_msg,
                    tool_call_id=tool_call.get("id", ""),
                    status="error",
                )

            # 执行命令
            result = await handler(request)

            # 通知 hooks 命令执行成功
            if hasattr(result, "content"):
                self._notify_hooks_success(command, result.content, context)

            return result

        # 非 bash 命令，直接执行
        return await handler(request)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """替换为 Claude 的 bash 工具描述符"""
        filtered = [
            t for t in request.tools if getattr(t, "name", None) != BASH_TOOL_NAME
        ]
        tools = [*filtered, {"type": BASH_TOOL_TYPE, "name": BASH_TOOL_NAME}]
        return handler(request.override(tools=tools))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """异步：替换为 Claude 的 bash 工具描述符"""
        filtered = [
            t for t in request.tools if getattr(t, "name", None) != BASH_TOOL_NAME
        ]
        tools = [*filtered, {"type": BASH_TOOL_TYPE, "name": BASH_TOOL_NAME}]
        return await handler(request.override(tools=tools))


__all__ = ["ShellMiddleware"]
