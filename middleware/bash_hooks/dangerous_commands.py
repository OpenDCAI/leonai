"""
危险命令拦截 Hook - 禁止执行危险命令

扩展安全策略，拦截可能造成系统损坏的命令。
"""

import re
from pathlib import Path
from typing import Any

from .base import BashHook, HookResult


class DangerousCommandsHook(BashHook):
    """
    危险命令拦截 Hook

    功能：
    - 拦截删除命令（rm -rf, rmdir 等）
    - 拦截系统修改命令（chmod, chown 等）
    - 拦截网络命令（curl, wget 等）
    - 可配置的命令黑名单
    """

    priority = 5  # 高优先级，在路径安全检查之前
    name = "DangerousCommands"
    description = "Block dangerous commands that may harm the system"
    enabled = True

    # 默认危险命令列表
    DEFAULT_BLOCKED_COMMANDS = [
        r"\brm\s+-rf",  # rm -rf
        r"\brm\s+.*-.*r.*f",  # rm with -r and -f flags
        r"\brmdir\b",  # rmdir
        r"\bchmod\b",  # chmod
        r"\bchown\b",  # chown
        r"\bsudo\b",  # sudo
        r"\bsu\b",  # su
        r"\bkill\b",  # kill
        r"\bpkill\b",  # pkill
        r"\breboot\b",  # reboot
        r"\bshutdown\b",  # shutdown
        r"\bmkfs\b",  # mkfs (format disk)
        r"\bdd\b",  # dd (disk operations)
    ]

    # 可选的网络命令限制
    NETWORK_COMMANDS = [
        r"\bcurl\b",
        r"\bwget\b",
        r"\bscp\b",
        r"\bsftp\b",
        r"\brsync\b",
        r"\bssh\b",
    ]

    def __init__(
        self,
        workspace_root: Path | str | None = None,
        block_network: bool = False,
        custom_blocked: list[str] | None = None,
        **kwargs,
    ):
        """
        初始化危险命令 hook

        Args:
            workspace_root: 工作目录
            block_network: 是否拦截网络命令
            custom_blocked: 自定义拦截的命令模式（正则表达式）
            **kwargs: 其他配置参数
        """
        super().__init__(workspace_root, **kwargs)

        # 构建拦截列表
        self.blocked_patterns = self.DEFAULT_BLOCKED_COMMANDS.copy()

        if block_network:
            self.blocked_patterns.extend(self.NETWORK_COMMANDS)

        if custom_blocked:
            self.blocked_patterns.extend(custom_blocked)

        # 编译正则表达式
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.blocked_patterns]

        print(f"[DangerousCommands] Loaded {len(self.compiled_patterns)} blocked command patterns")

    def check_command(self, command: str, context: dict[str, Any]) -> HookResult:
        """检查命令是否危险"""
        command = command.strip()

        # 检查每个危险模式
        for pattern in self.compiled_patterns:
            if pattern.search(command):
                return HookResult.block_command(
                    error_message=(
                        f"❌ SECURITY ERROR: Dangerous command detected\n"
                        f"   Command: {command[:100]}\n"
                        f"   Reason: This command is blocked for security reasons\n"
                        f"   Pattern: {pattern.pattern}\n"
                        f"   💡 If you need to perform this operation, ask the user for permission."
                    )
                )

        # 命令安全，允许执行
        return HookResult.allow_command()


__all__ = ["DangerousCommandsHook"]
