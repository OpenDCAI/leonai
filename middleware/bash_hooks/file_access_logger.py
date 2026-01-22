"""
文件访问日志 Hook - 记录所有文件操作

用于 FileSystemMiddleware 的审计日志。
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from .base import BashHook, HookResult


class FileAccessLoggerHook:
    """
    文件访问日志 Hook

    功能：
    - 记录所有文件读取、写入、编辑操作
    - 记录操作时间和结果
    - 用于审计和调试
    """

    def __init__(self, workspace_root: Path | str | None = None, log_file: str = "file_access.log", **kwargs):
        """
        初始化文件访问日志 hook

        Args:
            workspace_root: 工作目录
            log_file: 日志文件名
            **kwargs: 其他配置参数
        """
        self.workspace_root = Path(workspace_root) if workspace_root else None
        self.config = kwargs

        # 日志文件路径
        if workspace_root:
            self.log_path = Path(workspace_root) / log_file
        else:
            self.log_path = Path(log_file)

        # 确保日志文件存在
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def check_file_operation(self, file_path: str, operation: str) -> HookResult:
        """
        记录文件操作（不拦截）

        Args:
            file_path: 文件路径
            operation: 操作类型（read/write/edit/list）

        Returns:
            HookResult: 始终允许操作
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 记录操作
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {operation.upper()}: {file_path}\n")

        # 允许操作继续
        return HookResult.allow_command(metadata={"logged_at": timestamp})

    def log_operation_result(self, file_path: str, operation: str, success: bool, message: str = ""):
        """
        记录操作结果

        Args:
            file_path: 文件路径
            operation: 操作类型
            success: 是否成功
            message: 额外信息
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "SUCCESS" if success else "FAILED"

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {status}: {operation.upper()} {file_path}\n")
            if message:
                f.write(f"[{timestamp}] MESSAGE: {message[:200]}\n")


__all__ = ["FileAccessLoggerHook"]
