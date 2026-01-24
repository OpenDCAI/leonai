#!/usr/bin/env python3
"""
测试异步阻塞问题：验证在 AI 流式生成时输入框是否响应
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from textual.pilot import Pilot
from tui.app import LeonApp
from agent import create_leon_agent


async def test_async_blocking():
    """测试异步阻塞"""
    print("🧪 测试异步阻塞问题...")
    print("="*60)
    
    agent = create_leon_agent()
    app = LeonApp(agent, agent.workspace_root, "test-thread")
    
    async with app.run_test() as pilot:
        await pilot.pause(0.5)
        
        chat_input = app.query_one("#chat-input")
        text_area = chat_input.query_one("ChatTextArea")
        
        print("\n📤 发送消息...")
        await pilot.click("#chat-input")
        await pilot.press("h", "i")
        await pilot.press("enter")
        
        # 在 AI 开始处理后立即尝试输入
        await pilot.pause(0.1)
        
        print("\n🔥 关键测试：AI 处理中立即输入")
        print("-"*60)
        
        # 尝试多次输入，模拟用户快速打字
        for i in range(5):
            await pilot.pause(0.05)  # 50ms 间隔
            await pilot.press(str(i))
            print(f"  [{i*50}ms] 按下 '{i}' - 当前内容: '{text_area.text}'")
        
        # 检查是否成功输入
        await pilot.pause(0.1)
        final_content = text_area.text
        
        print(f"\n📊 结果:")
        print(f"  - 最终输入框内容: '{final_content}'")
        print(f"  - 预期内容: '01234'")
        
        if "01234" in final_content:
            print(f"  ✅ 成功！在 AI 处理时可以输入")
            print(f"  ✅ 异步阻塞问题已解决")
        elif final_content:
            print(f"  ⚠️  部分成功：输入了 '{final_content}'")
            print(f"  ⚠️  可能有轻微延迟但基本可用")
        else:
            print(f"  ❌ 失败！完全无法输入")
            print(f"  ❌ 异步阻塞问题仍然存在")
        
        # 等待 AI 完成
        print(f"\n⏳ 等待 AI 完成...")
        for i in range(20):
            await pilot.pause(0.5)
            assistant_msgs = app.query("AssistantMessage")
            if assistant_msgs:
                print(f"  ✅ AI 完成 ({(i+1)*500}ms)")
                break
        
        # 完成后再次测试输入
        await pilot.pause(0.2)
        print(f"\n📝 AI 完成后测试输入...")
        
        # 清空并输入新内容
        text_area.text = ""
        await pilot.press("t", "e", "s", "t")
        await pilot.pause(0.1)
        
        print(f"  - 输入 'test' 后内容: '{text_area.text}'")
        
        if "test" in text_area.text:
            print(f"  ✅ AI 完成后可以正常输入")
        else:
            print(f"  ❌ AI 完成后仍无法输入")
        
        print(f"\n" + "="*60)
        print("🎯 总结:")
        
        if "01234" in final_content and "test" in text_area.text:
            print("  ✅✅✅ 完美！异步阻塞问题已完全解决")
            print("  - AI 处理时可以输入")
            print("  - AI 完成后可以输入")
            print("  - 事件循环保持响应")
        elif final_content or "test" in text_area.text:
            print("  ⚠️  部分解决，但仍有改进空间")
        else:
            print("  ❌ 异步阻塞问题未解决")
            print("  💡 需要进一步优化事件循环")
        
        print("="*60)
    
    agent.cleanup()


if __name__ == "__main__":
    asyncio.run(test_async_blocking())
