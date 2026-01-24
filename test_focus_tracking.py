#!/usr/bin/env python3
"""
自动化测试：追踪焦点在 AI 生成时的变化
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from textual.pilot import Pilot
from tui.app import LeonApp
from agent import create_leon_agent


async def test_focus_tracking():
    """追踪焦点变化"""
    print("🧪 开始追踪焦点变化...")
    
    # 创建 agent
    agent = create_leon_agent()
    app = LeonApp(agent, agent.workspace_root, "test-thread")
    
    async with app.run_test() as pilot:
        # 等待 app 挂载
        await pilot.pause(0.5)
        
        # 获取组件
        chat_input = app.query_one("#chat-input")
        chat_container = app.query_one("#chat-container")
        
        print(f"\n📊 初始状态:")
        print(f"  - 当前焦点: {app.focused}")
        print(f"  - 输入框有焦点: {chat_input.has_focus}")
        print(f"  - 滚动容器有焦点: {chat_container.has_focus}")
        print(f"  - 输入框可聚焦: {chat_input.can_focus}")
        print(f"  - 滚动容器可聚焦: {chat_container.can_focus}")
        
        # 模拟发送消息
        print(f"\n📤 发送测试消息...")
        await pilot.click("#chat-input")
        await pilot.press("h", "i")
        
        print(f"\n📊 输入后:")
        print(f"  - 当前焦点: {app.focused}")
        print(f"  - 输入框有焦点: {chat_input.has_focus}")
        
        await pilot.press("enter")
        
        # 立即检查焦点（消息提交后）
        await pilot.pause(0.05)
        print(f"\n📊 消息提交后 (50ms):")
        print(f"  - 当前焦点: {app.focused}")
        print(f"  - 输入框有焦点: {chat_input.has_focus}")
        print(f"  - 滚动容器有焦点: {chat_container.has_focus}")
        
        if not chat_input.has_focus:
            print(f"  ⚠️  输入框失去焦点！")
            print(f"  - 焦点转移到: {app.focused}")
        
        # 等待 AI 开始生成
        await pilot.pause(0.5)
        print(f"\n📊 AI 生成中 (500ms):")
        print(f"  - 当前焦点: {app.focused}")
        print(f"  - 输入框有焦点: {chat_input.has_focus}")
        print(f"  - 滚动容器有焦点: {chat_container.has_focus}")
        
        # 尝试在生成时输入
        print(f"\n🧪 尝试在生成时输入...")
        await pilot.press("t", "e", "s", "t")
        await pilot.pause(0.1)
        
        # 检查输入框内容
        text_area = chat_input.query_one("ChatTextArea")
        print(f"  - 输入框内容: '{text_area.text}'")
        if text_area.text:
            print(f"  ✅ 可以输入")
        else:
            print(f"  ❌ 无法输入（焦点问题）")
        
        # 等待 AI 完成
        for i in range(10):
            await pilot.pause(0.5)
            if chat_input.has_focus:
                print(f"\n📊 AI 完成后 ({(i+1)*500}ms):")
                print(f"  - 输入框恢复焦点")
                break
        
        # 最终状态
        print(f"\n📊 最终状态:")
        print(f"  - 当前焦点: {app.focused}")
        print(f"  - 输入框有焦点: {chat_input.has_focus}")
        print(f"  - 输入框内容: '{text_area.text}'")
        
        # 总结
        print(f"\n" + "="*60)
        print("🎯 测试总结:")
        if not chat_input.has_focus:
            print("  ❌ 输入框最终没有焦点")
            print("\n💡 问题分析:")
            print("  - 焦点在消息提交后丢失")
            print("  - 需要在 finally 块中显式恢复焦点")
        elif not text_area.text:
            print("  ⚠️  输入框有焦点但无法输入")
            print("\n💡 问题分析:")
            print("  - 焦点状态正常但输入被阻止")
            print("  - 可能是事件处理或 disabled 状态问题")
        else:
            print("  ✅ 焦点和输入都正常")
        print("="*60)
    
    # 清理
    agent.cleanup()


if __name__ == "__main__":
    asyncio.run(test_focus_tracking())
