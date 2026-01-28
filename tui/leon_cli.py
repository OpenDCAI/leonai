#!/usr/bin/env python3
"""
Leon CLI - Textual TUI 模式

使用 Textual 框架构建的现代化终端界面
"""

import argparse
import os
import sys
import uuid
from pathlib import Path

from agent import create_leon_agent
from tui.app import run_tui
from tui.config import ConfigManager, interactive_config, show_config


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Leon AI - 你的 AI 编程助手", add_help=False)
    parser.add_argument("--profile", type=str, help="Profile 配置文件路径")
    parser.add_argument("--workspace", type=str, help="工作目录")
    parser.add_argument("-h", "--help", action="store_true", help="显示帮助信息")
    parser.add_argument("command", nargs="?", help="命令 (config)")
    parser.add_argument("subcommand", nargs="?", help="子命令 (show)")

    args = parser.parse_args()

    if args.help:
        print("Leon AI - 你的 AI 编程助手\n")
        print("用法:")
        print("  leonai                    启动 Leon")
        print("  leonai --profile <path>   使用指定 profile 启动")
        print("  leonai --workspace <dir>  指定工作目录")
        print("  leonai config             配置 API key 和其他设置")
        print("  leonai config show        显示当前配置")
        return

    if args.command == "config":
        if args.subcommand == "show":
            show_config()
        else:
            interactive_config()
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

    workspace = Path(args.workspace) if args.workspace else Path.cwd()

    print("🚀 初始化 Leon Agent...")
    try:
        agent = create_leon_agent(profile=args.profile, workspace_root=workspace)
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        sys.exit(1)

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
