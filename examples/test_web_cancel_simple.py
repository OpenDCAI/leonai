#!/usr/bin/env python3
"""
Simple test to verify cancellation writes to checkpoint.
"""

import asyncio
import os
import pickle
import sqlite3


async def test_checkpoint_after_cancel():
    """Check if checkpoint contains cancellation markers after manual cancel."""

    # Wait for user to manually test in browser
    print("=" * 60)
    print("手动测试步骤：")
    print("=" * 60)
    print()
    print("1. 在浏览器中访问 http://localhost:5173")
    print()
    print("2. 发送消息：")
    print("   请执行以下命令：echo 'step 1' && sleep 3 && echo 'step 2' && sleep 3 && echo 'step 3'")
    print()
    print("3. 等待第一个 tool call 出现后，立即点击停止按钮（红色方块）")
    print()
    print("4. 观察前端显示：")
    print("   - 已完成的 tool calls 显示 'Done'")
    print("   - 被取消的 tool calls 显示 'Cancelled' 标记（灰色）")
    print()
    print("5. 记下 thread_id（在浏览器 URL 中，格式：/threads/{thread_id}）")
    print()
    print("=" * 60)

    thread_id = input("\n请输入 thread_id（或按回车跳过检查）: ").strip()

    if not thread_id:
        print("\n跳过 checkpoint 检查")
        return

    print(f"\n检查 thread_id: {thread_id} 的 checkpoint...")

    db_path = os.path.expanduser("~/.leon/checkpoints.db")
    if not os.path.exists(db_path):
        print(f"❌ Checkpoint 数据库不存在: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT checkpoint FROM checkpoints WHERE thread_id = ? ORDER BY checkpoint_id DESC LIMIT 1",
        (thread_id,),
    )
    row = cursor.fetchone()

    if not row:
        print(f"❌ 未找到 thread_id={thread_id} 的 checkpoint")
        conn.close()
        return

    checkpoint = pickle.loads(row[0])
    messages = checkpoint["channel_values"]["messages"]

    print(f"\n找到 {len(messages)} 条消息")

    # Find ToolMessages with cancellation content
    cancel_messages = [
        msg for msg in messages if msg.__class__.__name__ == "ToolMessage" and "取消" in str(msg.content)
    ]

    print(f"\n✅ 找到 {len(cancel_messages)} 个取消标记：")
    for i, msg in enumerate(cancel_messages, 1):
        print(f"   {i}. Tool call ID: {msg.tool_call_id}")
        print(f"      Name: {msg.name}")
        print(f"      Content: {msg.content}")

    if cancel_messages:
        print("\n✅ 成功：Checkpoint 中包含取消标记")
    else:
        print("\n❌ 失败：Checkpoint 中没有取消标记")

    conn.close()

    # Test resume
    print("\n" + "=" * 60)
    print("继续测试恢复功能：")
    print("=" * 60)
    print()
    print("6. 在浏览器中发送消息：继续")
    print()
    print("7. 观察 Agent 是否：")
    print("   - 识别到之前的任务被取消")
    print("   - 从中断点继续执行")
    print()


if __name__ == "__main__":
    asyncio.run(test_checkpoint_after_cancel())
