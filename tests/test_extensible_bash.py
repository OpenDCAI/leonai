#!/usr/bin/env python3
"""
测试 ExtensibleBashMiddleware 插件系统
"""

import os
from pathlib import Path

# Load .env
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key] = value

from middleware.bash_hooks import load_hooks
from middleware.extensible_bash import ExtensibleBashMiddleware


def test_hook_loading():
    """测试 hook 加载"""
    print("=" * 70)
    print("测试 1: Hook 加载")
    print("=" * 70)

    workspace = Path("/Users/apple/Desktop/project/v1/文稿/project/leon/workspace")

    # 加载 hooks
    hooks = load_hooks(workspace_root=workspace, strict_mode=True)

    print("\n加载的 hooks:")
    for hook in hooks:
        print(f"  - {hook.name} (priority={hook.priority}, enabled={hook.enabled})")
        print(f"    {hook.description}")

    print("\n")


def test_path_security_hook():
    """测试路径安全 hook"""
    print("=" * 70)
    print("测试 2: 路径安全 Hook")
    print("=" * 70)

    from middleware.bash_hooks.path_security import PathSecurityHook

    workspace = Path("/Users/apple/Desktop/project/v1/文稿/project/leon/workspace")
    hook = PathSecurityHook(workspace_root=workspace, strict_mode=True)

    test_cases = [
        ("ls -la", True),
        ("cd /tmp", False),
        ("cd ../", False),
        ("cat /etc/passwd", False),
    ]

    print("\n测试用例:")
    for command, expected_allow in test_cases:
        result = hook.check_command(command, {})
        status = "✅" if result.allow == expected_allow else "❌"
        action = "允许" if result.allow else "拦截"
        print(f"{status} {action:6s} | {command}")
        if not result.allow:
            print(f"         └─ {result.error_message.split(chr(10))[0]}")

    print("\n")


def test_middleware_integration():
    """测试 middleware 集成"""
    print("=" * 70)
    print("测试 3: Middleware 集成")
    print("=" * 70)

    workspace = Path("/Users/apple/Desktop/project/v1/文稿/project/leon/workspace")
    workspace.mkdir(parents=True, exist_ok=True)

    # 创建 middleware
    middleware = ExtensibleBashMiddleware(
        workspace_root=str(workspace),
        allow_system_python=True,
        hook_config={"strict_mode": True},
    )

    print("\nMiddleware 创建成功!")
    print(f"工作目录: {middleware.workspace_root}")
    print(f"已加载 {len(middleware.hooks)} 个 hooks")

    # 测试命令检查
    test_commands = [
        "ls -la",
        "cd /tmp",
        "pwd",
    ]

    print("\n测试命令检查:")
    for cmd in test_commands:
        is_allowed, error = middleware._check_command_with_hooks(cmd, {})
        status = "✅ 允许" if is_allowed else "❌ 拦截"
        print(f"{status} | {cmd}")
        if not is_allowed:
            print(f"         └─ {error.split(chr(10))[0]}")

    print("\n")


def test_add_custom_hook():
    """演示如何添加自定义 hook"""
    print("=" * 70)
    print("测试 4: 添加自定义 Hook")
    print("=" * 70)

    print("""
要添加新的 bash 功能，只需：

1. 在 middleware/bash_hooks/ 目录下创建新的 .py 文件
   例如: dangerous_commands.py

2. 继承 BashHook 基类:

```python
from .base import BashHook, HookResult

class DangerousCommandsHook(BashHook):
    priority = 20
    name = "DangerousCommands"
    description = "Block dangerous commands like rm -rf"

    def check_command(self, command: str, context):
        if "rm -rf" in command:
            return HookResult.block_command(
                "❌ 'rm -rf' is dangerous!"
            )
        return HookResult.allow_command()
```

3. 重启 agent，插件自动加载！

已有的插件示例：
  - path_security.py  - 路径安全检查
  - command_logger.py - 命令日志记录

你可以参考这些文件创建自己的插件。
    """)


if __name__ == "__main__":
    print("\n🔧 ExtensibleBashMiddleware 插件系统测试\n")

    test_hook_loading()
    test_path_security_hook()
    test_middleware_integration()
    test_add_custom_hook()

    print("=" * 70)
    print("✅ 测试完成")
    print("=" * 70)
