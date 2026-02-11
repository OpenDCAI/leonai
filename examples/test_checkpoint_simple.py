"""
简化测试: 验证 checkpointer.aput() 能否手动写入取消状态
"""

import asyncio
from pathlib import Path

import aiosqlite
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


async def main():
    print("=== 测试 Checkpointer 手动写入 ===\n")

    # 1. 初始化 checkpointer
    db_path = Path("/tmp/test_checkpoint_simple.db")
    db_path.unlink(missing_ok=True)

    conn = await aiosqlite.connect(str(db_path))
    await conn.execute("PRAGMA journal_mode=WAL")
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()

    config = {"configurable": {"thread_id": "test-thread", "checkpoint_ns": ""}}

    # 2. 写入初始状态
    print("步骤 1: 写入初始状态")
    initial_state = {
        "values": {
            "messages": [
                HumanMessage(content="测试消息"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "call_123",
                            "name": "test_tool",
                            "args": {"param": "value"},
                        }
                    ],
                ),
            ]
        },
        "next": ("tools",),
    }

    await checkpointer.aput(config, initial_state, {}, None)
    print("✓ 初始状态已写入\n")

    # 3. 读取状态
    print("步骤 2: 读取状态")
    checkpoint = await checkpointer.aget(config)
    if checkpoint:
        messages = checkpoint.values.get("messages", [])
        print(f"✓ 读取成功,消息数: {len(messages)}")
        for i, msg in enumerate(messages):
            print(f"  [{i}] {msg.__class__.__name__}")
    else:
        print("✗ 读取失败")
        return

    # 4. 模拟取消: 添加 ToolMessage
    print("\n步骤 3: 模拟取消,添加 ToolMessage")
    cancel_message = ToolMessage(
        content="任务被用户取消",
        tool_call_id="call_123",
        name="test_tool",
    )

    updated_values = checkpoint.values.copy()
    updated_values["messages"].append(cancel_message)

    await checkpointer.aput(
        config,
        {
            "values": updated_values,
            "next": (),  # 标记为完成
        },
        {},
        checkpoint.config,
    )
    print("✓ 取消状态已写入\n")

    # 5. 再次读取验证
    print("步骤 4: 验证取消状态")
    final_checkpoint = await checkpointer.aget(config)
    if final_checkpoint:
        messages = final_checkpoint.values.get("messages", [])
        print(f"✓ 最终消息数: {len(messages)}")
        for i, msg in enumerate(messages):
            msg_type = msg.__class__.__name__
            if msg_type == "ToolMessage":
                print(f"  [{i}] {msg_type}: {msg.content} (tool_call_id={msg.tool_call_id})")
            else:
                print(f"  [{i}] {msg_type}")

        # 检查是否有取消消息
        has_cancel = any(isinstance(msg, ToolMessage) and "取消" in msg.content for msg in messages)
        if has_cancel:
            print("\n✅ 测试成功: 取消状态已正确保存")
        else:
            print("\n❌ 测试失败: 未找到取消消息")
    else:
        print("✗ 读取失败")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
