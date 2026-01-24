#!/usr/bin/env python3
"""
真实场景测试：模拟用户在 AI 完成后立即输入
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from textual.pilot import Pilot
from tui.app import LeonApp
from agent import create_leon_agent


async def test_real_scenario():
    """模拟真实使用场景"""
    print("🧪 真实场景测试：AI 完成后立即输入")
    
    agent = create_leon_agent()
    app = LeonApp(agent, agent.workspace_root, "test-thread")
    
    async with app.run_test() as pilot:
        await pilot.pause(0.5)
        
        chat_input = app.query_one("#chat-input")
        text_area = chat_input.query_one("ChatTextArea")
        
        print(f"\n第一轮：发送消息并等待完成")
        print("="*60)
        
        # 第一次交互
        await pilot.click("#chat-input")
        await pilot.press("h", "i")
        await pilot.press("enter")
        
        # 等待 AI 完成（最多 10 秒）
        for i in range(20):
            await pilot.pause(0.5)
            # 检查是否有 AssistantMessage
            assistant_msgs = app.query("AssistantMessage")
            if assistant_msgs:
                print(f"  ✅ AI 响应完成 ({(i+1)*500}ms)")
                break
        
        # AI 完成后立即尝试输入
        await pilot.pause(0.2)
        print(f"\n📝 AI 完成后立即输入...")
        print(f"  - 当前焦点: {app.focused}")
        print(f"  - TextArea 有焦点: {text_area.has_focus}")
        
        # 清空输入框（模拟用户看到空输入框）
        print(f"  - 输入框当前内容: '{text_area.text}'")
        
        # 尝试输入新消息
        await pilot.press("t", "e", "s", "t", " ", "2")
        await pilot.pause(0.1)
        
        print(f"  - 输入后内容: '{text_area.text}'")
        
        if "test 2" in text_area.text:
            print(f"  ✅ 可以正常输入")
        else:
            print(f"  ❌ 无法输入！")
            print(f"  - 焦点可能丢失或被阻止")
        
        # 第二轮：再次发送
        print(f"\n第二轮：发送第二条消息")
        print("="*60)
        
        await pilot.press("enter")
        await pilot.pause(0.5)
        
        # 在生成过程中尝试输入
        print(f"\n📝 AI 生成中尝试输入...")
        await pilot.press("a", "b", "c")
        await pilot.pause(0.1)
        
        print(f"  - 输入框内容: '{text_area.text}'")
        if text_area.text:
            print(f"  ✅ 生成时可以输入")
        else:
            print(f"  ❌ 生成时无法输入")
        
        # 等待完成
        for i in range(20):
            await pilot.pause(0.5)
            assistant_msgs = app.query("AssistantMessage")
            if len(assistant_msgs) >= 2:
                print(f"  ✅ 第二次响应完成")
                break
        
        # 最终检查
        await pilot.pause(0.2)
        print(f"\n📊 最终状态:")
        print(f"  - 当前焦点: {app.focused}")
        print(f"  - 输入框内容: '{text_area.text}'")
        
        # 再次尝试输入
        await pilot.press("f", "i", "n", "a", "l")
        await pilot.pause(0.1)
        print(f"  - 输入 'final' 后: '{text_area.text}'")
        
        if "final" in text_area.text:
            print(f"  ✅ 最终可以输入")
        else:
            print(f"  ❌ 最终无法输入")
        
        print(f"\n" + "="*60)
        print("🎯 结论:")
        print("  如果测试通过但实际使用失败，可能原因：")
        print("  1. 测试环境与真实环境的事件循环差异")
        print("  2. 真实环境中有其他组件抢占焦点")
        print("  3. 终端模拟器的键盘事件处理差异")
        print("="*60)
    
    agent.cleanup()


if __name__ == "__main__":
    asyncio.run(test_real_scenario())
