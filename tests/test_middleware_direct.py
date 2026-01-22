#!/usr/bin/env python3
"""
直接测试 SafeBashMiddleware 的路径验证逻辑
"""

from pathlib import Path

from middleware.safe_bash import SafeBashMiddleware


def test_command_validation():
    """测试命令验证逻辑"""
    print("=" * 70)
    print("直接测试 SafeBashMiddleware 路径验证")
    print("=" * 70)

    # 创建 middleware 实例
    workspace = Path("/Users/apple/Desktop/project/v1/文稿/project/leon/workspace")
    middleware = SafeBashMiddleware(
        workspace_root=str(workspace),
        strict_mode=True,
    )

    print(f"\n工作目录: {middleware.workspace_root}")
    print(f"严格模式: {middleware.strict_mode}\n")

    # 测试用例
    test_cases = [
        # (命令, 预期是否安全)
        ("ls -la", True),
        ("pwd", True),
        ("echo 'hello'", True),
        ("cd /tmp", False),
        ("cd ../", False),
        ("cd ../../", False),
        ("cat /etc/passwd", False),
        ("ls /Users/apple/Desktop", False),
        ("mkdir test && cd test", True),
        ("cat ../../../etc/passwd", False),
    ]

    print("测试结果:")
    print("-" * 70)

    for command, expected_safe in test_cases:
        is_safe, error_msg = middleware._is_safe_command(command)

        status = "✅" if is_safe == expected_safe else "❌"
        result = "安全" if is_safe else "拦截"

        print(f"{status} {result:6s} | {command:40s}")

        if not is_safe and error_msg:
            # 只显示错误消息的第一行
            first_line = error_msg.split('\n')[0]
            print(f"         └─ {first_line}")

    print("-" * 70)
    print("\n测试完成！")


if __name__ == "__main__":
    test_command_validation()
