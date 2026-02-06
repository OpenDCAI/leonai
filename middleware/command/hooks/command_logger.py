"""
命令日志 Hook - 记录所有执行的 bash 命令

这是一个示例插件，展示如何使用 hook 系统。
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from .base import BashHook, HookResult


class CommandLoggerHook(BashHook):
    """
    命令日志 Hook

    功能：
    - 记录所有执行的命令
    - 记录命令执行时间
    - 记录命令执行结果
    """

    priority = 50  # 中等优先级
    name = "CommandLogger"
    description = "Log all bash commands to file"
    enabled = True  # 可以通过配置禁用

    def __init__(self, workspace_root: Path | str | None = None, log_file: str = "bash_commands.log", **kwargs):
        super().__init__(workspace_root, **kwargs)

        # 日志文件路径
        if workspace_root:
            self.log_path = Path(workspace_root) / log_file
        else:
            self.log_path = Path(log_file)

        # 确保日志文件存在
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def check_command(self, command: str, context: dict[str, Any]) -> HookResult:
        """记录命令（不拦截）"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 记录命令
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] COMMAND: {command}\n")

        # 允许命令执行，继续后续 hooks
        return HookResult.allow_command(metadata={"logged_at": timestamp})

    def on_command_success(self, command: str, output: str, context: dict[str, Any]) -> None:
        """记录命令执行成功"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] SUCCESS: {command}\n")
            if output:
                # 只记录前 200 个字符
                output_preview = output[:200].replace("\n", " ")
                f.write(f"[{timestamp}] OUTPUT: {output_preview}\n")

    def on_command_error(self, command: str, error: str, context: dict[str, Any]) -> None:
        """记录命令执行失败"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] ERROR: {command}\n")
            if error:
                error_preview = error[:200].replace("\n", " ")
                f.write(f"[{timestamp}] ERROR_MSG: {error_preview}\n")
