#!/usr/bin/env python3
"""
Leon CLI - Textual TUI 模式

使用 Textual 框架构建的现代化终端界面
"""

import os
import sys
import uuid
from pathlib import Path

from agent import create_leon_agent
from tui.app import run_tui
from tui.config import ConfigManager, interactive_config, show_config


def main():
    """主函数"""
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "config":
            if len(sys.argv) > 2 and sys.argv[2] == "show":
                show_config()
            else:
                interactive_config()
            return
        elif cmd in ["-h", "--help"]:
            print("Leon AI - 你的 AI 编程助手\n")
            print("用法:")
            print("  leonai              启动 Leon")
            print("  leonai config       配置 API key 和其他设置")
            print("  leonai config show  显示当前配置")
            return
    
    config_manager = ConfigManager()
    config_manager.load_to_env()
    
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ 错误: 未设置 API key")
        print("\n请先运行配置向导：")
        print("  leonai config")
        print("\n或手动设置环境变量：")
        print("  export OPENAI_API_KEY='your-key'")
        sys.exit(1)

    current_dir = Path.cwd()
    
    print("🚀 初始化 Leon Agent...")
    agent = create_leon_agent(workspace_root=current_dir)
    print(f"✅ Agent 已就绪")
    print(f"📁 工作目录: {agent.workspace_root}\n")

    thread_id = f"tui-{uuid.uuid4().hex[:8]}"

    try:
        run_tui(agent, agent.workspace_root, thread_id)
    except KeyboardInterrupt:
        print("\n\n👋 再见！")
    finally:
        print("\n🧹 已退出")


if __name__ == "__main__":
    main()
