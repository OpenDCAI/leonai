"""
最简化测试: 验证核心流程
1. Agent 运行并自动保存 checkpoint
2. 手动读取 checkpoint
3. 手动添加取消 ToolMessage
4. 验证能否成功写入
"""

import asyncio
from pathlib import Path

import aiosqlite
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


@tool
def simple_tool(text: str) -> str:
    """一个简单的工具"""
    return f"处理: {text}"


async def main():
    print("=== 最简化测试 ===\n")

    # 1. 初始化
    db_path = Path("/tmp/test_minimal.db")
    db_path.unlink(missing_ok=True)

    conn = await aiosqlite.connect(str(db_path))
    await conn.execute("PRAGMA journal_mode=WAL")
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()

    model = init_chat_model("claude-sonnet-4-5-20250929")
    agent = create_agent(
        model=model,
        tools=[simple_tool],
        checkpointer=checkpointer,
    )

    config = {"configurable": {"thread_id": "test-minimal"}}

    # 2. 运行 agent 一次,让它自动创建 checkpoint
    print("步骤 1: 运行 agent,让它调用 tool")
    tool_call_id = None

    async for chunk in agent.astream(
        {"messages": [HumanMessage(content="请使用 simple_tool 处理文本 'hello'")]},
        config=config,
        stream_mode=["updates"],
    ):
        if isinstance(chunk, dict):
            for node_name, node_update in chunk.items():
                if isinstance(node_update, dict):
                    messages = node_update.get("messages", [])
                    if not isinstance(messages, list):
                        messages = [messages]

                    for msg in messages:
                        if msg.__class__.__name__ == "AIMessage":
                            for tc in getattr(msg, "tool_calls", []):
                                tool_call_id = tc.get("id")
                                print(f"✓ 发现 tool call: {tc.get('name')} (ID: {tool_call_id})")

    print()

    # 3. 读取 checkpoint
    print("步骤 2: 读取 checkpoint")
    checkpoint_tuple = await checkpointer.aget_tuple(config)
    if not checkpoint_tuple:
        print("✗ Checkpoint 不存在")
        return

    checkpoint = checkpoint_tuple.checkpoint
    messages = checkpoint["channel_values"].get("messages", [])
    print(f"✓ Checkpoint 存在,消息数: {len(messages)}\n")

    # 4. 模拟取消场景: 假设有一个未完成的 tool call
    print("步骤 3: 模拟取消,添加取消 ToolMessage")

    # 创建一个新的 tool call (模拟未完成的)
    fake_tool_call_id = "call_cancelled_123"
    cancel_message = ToolMessage(
        content="任务被用户取消",
        tool_call_id=fake_tool_call_id,
        name="simple_tool",
    )

    # 更新 checkpoint
    updated_channel_values = checkpoint["channel_values"].copy()
    updated_channel_values["messages"].append(cancel_message)

    try:
        await checkpointer.aput(
            checkpoint_tuple.config,  # 使用完整的 config
            {
                "v": checkpoint["v"],
                "ts": checkpoint["ts"],
                "id": checkpoint["id"],
                "channel_values": updated_channel_values,
                "channel_versions": checkpoint["channel_versions"],
                "versions_seen": checkpoint["versions_seen"],
                "updated_channels": checkpoint.get("updated_channels"),
            },
            {},
            checkpoint,
        )
        print("✓ 取消状态已写入\n")
    except Exception as e:
        print(f"✗ 写入失败: {e}\n")
        return

    # 5. 验证
    print("步骤 4: 验证取消状态")
    final_checkpoint_tuple = await checkpointer.aget_tuple(config)
    if final_checkpoint_tuple:
        final_checkpoint = final_checkpoint_tuple.checkpoint
        messages = final_checkpoint["channel_values"].get("messages", [])
        print(f"✓ 最终消息数: {len(messages)}")

        # 查找取消消息
        cancel_found = False
        for i, msg in enumerate(messages):
            if isinstance(msg, ToolMessage) and "取消" in msg.content:
                cancel_found = True
                print(f"  [{i}] ToolMessage: {msg.content} (tool_call_id={msg.tool_call_id})")

        if cancel_found:
            print("\n✅ 测试成功: 可以手动写入取消状态到 checkpoint")
        else:
            print("\n❌ 测试失败: 未找到取消消息")
    else:
        print("✗ 读取失败")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
