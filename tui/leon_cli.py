#!/usr/bin/env python3
"""
Leon CLI - Textual TUI 模式

使用 Textual 框架构建的现代化终端界面
"""

import os
import sys
import uuid
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载 .env
env_file = project_root / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key] = value

from agent import create_leon_agent
from tui.app import run_tui


def main():
    """主函数"""
    # 检查 API key
    if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        print("❌ 错误: 未设置 API key")
        print("\n请设置环境变量：")
        print("  export ANTHROPIC_API_KEY='your-key'")
        print("  或")
        print("  export OPENAI_API_KEY='your-key'  # 如果使用代理")
        return

    # 创建 agent
    print("🚀 初始化 Leon Agent...")
    agent = create_leon_agent()
    print(f"✅ Agent 已就绪")
    print(f"📁 工作目录: {agent.workspace_root}\n")

    # 生成 thread ID
    thread_id = f"tui-{uuid.uuid4().hex[:8]}"

    try:
        # 运行 TUI
        run_tui(agent, agent.workspace_root, thread_id)
    except KeyboardInterrupt:
        print("\n\n👋 再见！")
    finally:
        # 清理
        agent.cleanup()
        print("\n🧹 工作目录已清理")


if __name__ == "__main__":
    main()
