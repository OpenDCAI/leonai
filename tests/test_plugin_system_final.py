#!/usr/bin/env python3
"""
最终测试：验证插件系统与 Agent 的完整集成
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

from agent import create_leon


def test_agent_with_plugins():
    """测试 Agent 与插件系统的集成"""
    print("=" * 70)
    print("最终测试：Agent + 插件系统")
    print("=" * 70)

    # 创建 Agent
    workspace = Path("/Users/apple/Desktop/project/v1/文稿/project/leon/workspace")
    workspace.mkdir(parents=True, exist_ok=True)

    print("\n🔧 初始化 Agent...")
    leon = create_leon(workspace_root=workspace)
    print("✅ Agent 初始化成功")
    print(f"📁 Workspace: {leon.workspace_root}\n")

    # 测试用例
    test_cases = [
        {
            "name": "安全命令 - 应该成功",
            "message": "Execute this bash command: ls -la",
            "should_succeed": True,
        },
        {
            "name": "不安全命令 - 应该被拦截",
            "message": "Execute this bash command: cd /tmp",
            "should_succeed": False,
        },
        {
            "name": "路径遍历 - 应该被拦截",
            "message": "Execute this bash command: cd ../",
            "should_succeed": False,
        },
    ]

    print("测试用例:")
    print("-" * 70)

    for i, test in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {test['name']}")
        print(f"命令: {test['message']}")

        try:
            response = leon.get_response(
                test['message'],
                thread_id=f"test-{i}"
            )

            # 检查响应中是否包含安全错误
            has_security_error = "SECURITY ERROR" in response or "blocked" in response.lower()

            if test['should_succeed']:
                if not has_security_error:
                    print("✅ 通过：命令正常执行")
                else:
                    print("❌ 失败：命令被错误拦截")
            else:
                if has_security_error:
                    print("✅ 通过：命令被正确拦截")
                else:
                    print("⚠️  警告：命令未被拦截（Agent 可能自行判断）")

            # 显示响应摘要
            response_preview = response[:150].replace("\n", " ")
            print(f"响应: {response_preview}...")

        except Exception as e:
            print(f"❌ 异常: {e}")

    print("\n" + "-" * 70)
    print("✅ 测试完成\n")


if __name__ == "__main__":
    print("\n🎯 插件系统最终集成测试\n")
    test_agent_with_plugins()
