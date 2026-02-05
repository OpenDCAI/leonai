"""
文件权限控制 Hook - 实现权限分级

支持文件类型限制等安全策略。
"""

from pathlib import Path
from typing import Any

from .base import HookResult


class FilePermissionHook:
    """
    文件权限控制 Hook

    功能：
    - 文件类型限制：只允许特定扩展名
    - 路径黑名单：禁止访问特定路径
    """

    def __init__(
        self,
        workspace_root: Path | str | None = None,
        allowed_extensions: list[str] | None = None,
        blocked_paths: list[str] | None = None,
        **kwargs,
    ):
        """
        初始化权限控制 hook

        Args:
            workspace_root: 工作目录
            allowed_extensions: 允许的文件扩展名（None 表示全部允许）
            blocked_paths: 禁止访问的路径列表
            **kwargs: 其他配置参数
        """
        self.workspace_root = Path(workspace_root) if workspace_root else None
        self.allowed_extensions = allowed_extensions
        self.blocked_paths = [Path(p) for p in (blocked_paths or [])]
        self.config = kwargs

    def check_file_operation(self, file_path: str, operation: str) -> HookResult:
        """
        检查文件操作权限

        Args:
            file_path: 文件路径
            operation: 操作类型（read/write/edit/list）

        Returns:
            HookResult: 权限检查结果
        """
        path = Path(file_path)

        # 文件类型检查
        if self.allowed_extensions and path.suffix:
            ext = path.suffix.lstrip(".")
            if ext not in self.allowed_extensions:
                return HookResult.block_command(
                    error_message=(
                        f"❌ PERMISSION DENIED: File type not allowed\n"
                        f"   File: {file_path}\n"
                        f"   Extension: {path.suffix}\n"
                        f"   Allowed: {', '.join(self.allowed_extensions)}"
                    )
                )

        # 路径黑名单检查
        for blocked in self.blocked_paths:
            try:
                path.resolve().relative_to(blocked.resolve())
                return HookResult.block_command(
                    error_message=(
                        f"❌ PERMISSION DENIED: Access to this path is blocked\n"
                        f"   File: {file_path}\n"
                        f"   Blocked path: {blocked}"
                    )
                )
            except ValueError:
                continue

        # 允许操作
        return HookResult.allow_command()


__all__ = ["FilePermissionHook"]
