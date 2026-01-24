#!/usr/bin/env python3
"""
自动化测试：验证输入框在 AI 生成时是否被禁用
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from textual.pilot import Pilot
from tui.app import LeonApp
from agent import create_leon_agent


async def test_input_state_during_generation():
    """测试 AI 生成时输入框状态"""
    print("🧪 开始测试输入框状态...")
    
    # 创建 agent
    agent = create_leon_agent()
    app = LeonApp(agent, agent.workspace_root, "test-thread")
    
    async with app.run_test() as pilot:
        # 等待 app 挂载
        await pilot.pause(0.5)
        
        # 获取输入框
        chat_input = app.query_one("#chat-input")
        
        # 初始状态检查
        print(f"\n📊 初始状态:")
        print(f"  - 输入框禁用: {chat_input.disabled}")
        print(f"  - 输入框可聚焦: {chat_input.can_focus}")
        
        assert not chat_input.disabled, "❌ 初始状态：输入框不应该被禁用"
        print("  ✅ 初始状态正常")
        
        # 模拟发送消息
        print(f"\n📤 发送测试消息...")
        await pilot.click("#chat-input")
        await pilot.press("h", "i")
        await pilot.press("enter")
        
        # 立即检查状态（消息提交后）
        await pilot.pause(0.1)
        print(f"\n📊 消息提交后 (100ms):")
        print(f"  - 输入框禁用: {chat_input.disabled}")
        print(f"  - 输入框可聚焦: {chat_input.can_focus}")
        
        if chat_input.disabled:
            print("  ⚠️  输入框被禁用了！")
        else:
            print("  ✅ 输入框仍然可用")
        
        # 等待 AI 开始生成（500ms）
        await pilot.pause(0.5)
        print(f"\n📊 AI 生成中 (500ms):")
        print(f"  - 输入框禁用: {chat_input.disabled}")
        
        if chat_input.disabled:
            print("  ❌ 问题确认：输入框在 AI 生成时被禁用")
        else:
            print("  ✅ 输入框在 AI 生成时仍然可用")
        
        # 等待 AI 完成（最多 5 秒）
        for i in range(10):
            await pilot.pause(0.5)
            if not chat_input.disabled:
                print(f"\n📊 AI 完成后 ({(i+1)*500}ms):")
                print(f"  - 输入框禁用: {chat_input.disabled}")
                print("  ✅ 输入框已恢复")
                break
        else:
            print(f"\n⚠️  等待 5 秒后输入框仍被禁用")
        
        # 最终状态
        print(f"\n📊 最终状态:")
        print(f"  - 输入框禁用: {chat_input.disabled}")
        print(f"  - 输入框可聚焦: {chat_input.can_focus}")
        
        # 总结
        print(f"\n" + "="*60)
        print("🎯 测试总结:")
        if chat_input.disabled:
            print("  ❌ 输入框最终仍被禁用 - 问题存在")
            print("\n💡 问题分析:")
            print("  - 输入框在消息提交后被设置为 disabled=True")
            print("  - 在 finally 块中应该恢复，但可能没有执行")
            print("  - 需要检查异常处理和 finally 块")
        else:
            print("  ✅ 输入框状态正常")
        print("="*60)
    
    # 清理
    agent.cleanup()


if __name__ == "__main__":
    asyncio.run(test_input_state_during_generation())
