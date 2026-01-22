"""
Bash Hook 基类定义

所有 bash hook 插件都应该继承 BashHook 基类。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class HookResult:
    """Hook 执行结果"""

    # 是否允许命令执行
    allow: bool

    # 错误消息（如果 allow=False）
    error_message: str = ""

    # 是否继续执行后续 hooks（如果为 False，立即返回结果）
    continue_chain: bool = True

    # 额外的元数据
    metadata: dict[str, Any] | None = None

    @classmethod
    def allow_command(cls, metadata: dict[str, Any] | None = None) -> "HookResult":
        """创建一个允许命令执行的结果"""
        return cls(allow=True, continue_chain=True, metadata=metadata)

    @classmethod
    def block_command(
        cls,
        error_message: str,
        continue_chain: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> "HookResult":
        """创建一个拦截命令的结果"""
        return cls(
            allow=False,
            error_message=error_message,
            continue_chain=continue_chain,
            metadata=metadata,
        )


class BashHook(ABC):
    """
    Bash Hook 基类

    所有 bash hook 插件都应该继承这个类并实现 check_command 方法。

    Hook 的执行顺序由 priority 决定（数字越小越先执行）。
    """

    # Hook 优先级（数字越小越先执行）
    priority: int = 100

    # Hook 名称（用于日志和调试）
    name: str = "UnnamedHook"

    # Hook 描述
    description: str = ""

    # 是否启用（可以通过配置动态控制）
    enabled: bool = True

    def __init__(self, workspace_root: Path | str | None = None, **kwargs):
        """
        初始化 hook

        Args:
            workspace_root: 工作目录路径
            **kwargs: 其他配置参数
        """
        self.workspace_root = Path(workspace_root) if workspace_root else None
        self.config = kwargs

    @abstractmethod
    def check_command(self, command: str, context: dict[str, Any]) -> HookResult:
        """
        检查命令是否允许执行

        Args:
            command: 要执行的 bash 命令
            context: 上下文信息（包含 tool_call, request 等）

        Returns:
            HookResult: Hook 执行结果
        """
        pass

    def on_command_success(self, command: str, output: str, context: dict[str, Any]) -> None:
        """
        命令执行成功后的回调（可选）

        Args:
            command: 执行的命令
            output: 命令输出
            context: 上下文信息
        """
        pass

    def on_command_error(self, command: str, error: str, context: dict[str, Any]) -> None:
        """
        命令执行失败后的回调（可选）

        Args:
            command: 执行的命令
            error: 错误信息
            context: 上下文信息
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, priority={self.priority}, enabled={self.enabled})>"
