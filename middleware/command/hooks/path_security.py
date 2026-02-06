"""
路径安全检查 Hook

确保所有 bash 命令只能在工作目录内执行。
"""

import re
from pathlib import Path
from typing import Any

from .base import BashHook, HookResult


class PathSecurityHook(BashHook):
    """
    路径安全检查 Hook

    功能：
    - 禁止 cd 到工作目录外的绝对路径
    - 禁止使用 ../ 向上遍历目录
    - 禁止访问工作目录外的绝对路径
    """

    priority = 10  # 高优先级，最先执行
    name = "PathSecurity"
    description = "Restrict bash commands to workspace directory only"

    def __init__(self, workspace_root: Path | str | None = None, strict_mode: bool = True, **kwargs):
        super().__init__(workspace_root, **kwargs)

        if workspace_root is None:
            raise ValueError("PathSecurityHook requires workspace_root")

        self.strict_mode = strict_mode

    def check_command(self, command: str, context: dict[str, Any]) -> HookResult:
        """检查命令是否安全"""
        command = command.strip()

        # 检查是否试图 cd 到绝对路径
        cd_absolute = re.search(r"\bcd\s+(/[^\s;|&]*)", command)
        if cd_absolute:
            target_path = Path(cd_absolute.group(1)).resolve()
            if not self._is_within_workspace(target_path):
                return HookResult.block_command(
                    error_message=(
                        f"❌ SECURITY ERROR: Cannot cd to '{cd_absolute.group(1)}'\n"
                        f"   Reason: Path is outside workspace\n"
                        f"   Workspace: {self.workspace_root}\n"
                        f"   Attempted: {target_path}\n"
                        f"   💡 You can only execute commands within the workspace directory."
                    )
                )

        # 检查是否使用 ../ 向上遍历
        if self.strict_mode and ".." in command:
            if re.search(r"\.\./|/\.\.|cd\s+\.\.", command):
                return HookResult.block_command(
                    error_message=(
                        f"❌ SECURITY ERROR: Path traversal detected in command\n"
                        f"   Command: {command[:100]}\n"
                        f"   Reason: '../' is not allowed (may escape workspace)\n"
                        f"   Workspace: {self.workspace_root}\n"
                        f"   💡 Use relative paths within workspace or ask user for permission."
                    )
                )

        # 检查绝对路径访问
        absolute_paths = re.findall(r"\s(/[^\s;|&]+)", command)
        for abs_path in absolute_paths:
            # 跳过常见的系统命令
            if abs_path.startswith(("/bin/", "/usr/", "/etc/bash", "/dev/", "/tmp/")):
                continue

            try:
                resolved = Path(abs_path).resolve()
                if not self._is_within_workspace(resolved):
                    return HookResult.block_command(
                        error_message=(
                            f"❌ SECURITY ERROR: Cannot access '{abs_path}'\n"
                            f"   Reason: Path is outside workspace\n"
                            f"   Workspace: {self.workspace_root}\n"
                            f"   Attempted: {resolved}\n"
                            f"   💡 You can only access files within the workspace directory."
                        )
                    )
            except Exception:
                # 如果路径无法解析，可能是命令参数，允许通过
                pass

        # 命令安全，允许执行
        return HookResult.allow_command()

    def _is_within_workspace(self, path: Path) -> bool:
        """检查路径是否在工作目录内"""
        try:
            path.resolve().relative_to(self.workspace_root)
            return True
        except ValueError:
            return False
