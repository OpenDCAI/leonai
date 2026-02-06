"""Test script for new TUI features"""

from pathlib import Path

from agent import create_leon_agent
from tui.app import run_tui


def main():
    """Run TUI with test agent"""
    workspace = Path(__file__).parent / "workspace"
    workspace.mkdir(exist_ok=True)

    print("🚀 启动 Leon TUI - 测试新功能")
    print("\n新功能列表:")
    print("1. ✅ 对话历史导航 (Ctrl+↑/↓)")
    print("2. ✅ 增强思考状态 (显示工具执行)")
    print("3. ✅ 消息计数统计")
    print("4. ✅ 复制最后消息 (Ctrl+Y)")
    print("5. ✅ 导出对话 (Ctrl+E)")
    print("\n测试建议:")
    print("- 发送多条消息，然后用 Ctrl+↑ 浏览历史")
    print("- 观察工具调用时的思考状态变化")
    print("- 使用 Ctrl+Y 复制 AI 回复")
    print("- 使用 Ctrl+E 导出对话到 workspace/")
    print("- 检查状态栏的消息计数\n")

    agent = create_leon_agent(workspace_root=workspace)

    try:
        run_tui(agent, workspace, thread_id="test-features")
    except KeyboardInterrupt:
        print("\n👋 退出 TUI")
    finally:
        print(f"\n📁 工作目录: {workspace}")


if __name__ == "__main__":
    main()
