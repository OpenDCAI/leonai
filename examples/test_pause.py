"""
暂停机制测试: 执行长程任务,中途暂停,验证状态保存
场景:
1. Agent 开始顺序执行 10 个命令
2. 执行到第 3-4 个命令时用户点击暂停
3. 验证已完成的命令结果被保存
4. 验证未完成的 tool call 被标记为取消
"""

import asyncio
from pathlib import Path

import aiosqlite
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# 记录已执行的命令
executed_commands = []


@tool
async def run_bash_command(command: str) -> str:
    """执行一个 bash 命令"""
    print(f"[Tool] 执行: {command}")
    await asyncio.sleep(0.5)
    executed_commands.append(command)
    result = f"完成: {command}"
    print(f"[Tool] {result}")
    return result


async def write_cancel_state(checkpointer, config, pending_tool_calls):
    """写入取消状态到 checkpoint"""
    if not pending_tool_calls:
        return False

    checkpoint_tuple = await checkpointer.aget_tuple(config)
    if not checkpoint_tuple:
        return False

    checkpoint = checkpoint_tuple.checkpoint
    metadata = checkpoint_tuple.metadata

    # 创建取消消息
    cancel_messages = []
    for tc_id, tc_info in pending_tool_calls.items():
        cancel_messages.append(
            ToolMessage(
                content="任务被用户取消",
                tool_call_id=tc_id,
                name=tc_info["name"],
            )
        )
        print(f"  - {tc_info['name']}({tc_info['args']}) → 取消")

    # 更新 checkpoint
    updated_channel_values = checkpoint["channel_values"].copy()
    updated_channel_values["messages"].extend(cancel_messages)

    await checkpointer.aput(
        checkpoint_tuple.config,
        {
            "v": checkpoint["v"],
            "ts": checkpoint["ts"],
            "id": checkpoint["id"],
            "channel_values": updated_channel_values,
            "channel_versions": checkpoint["channel_versions"],
            "versions_seen": checkpoint["versions_seen"],
            "updated_channels": checkpoint.get("updated_channels"),
        },
        metadata,
        checkpoint,
    )
    return True


async def main():
    print("=== 暂停机制测试 ===\n")

    # 初始化
    db_path = Path("/tmp/test_pause.db")
    db_path.unlink(missing_ok=True)

    conn = await aiosqlite.connect(str(db_path))
    await conn.execute("PRAGMA journal_mode=WAL")
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()

    model = init_chat_model("claude-sonnet-4-5-20250929")
    agent = create_agent(
        model=model,
        tools=[run_bash_command],
        checkpointer=checkpointer,
    )

    config = {"configurable": {"thread_id": "test-pause"}}

    # 开始执行任务
    print("开始执行 10 个命令 (顺序执行,每个 0.5 秒)")
    print("6 秒后自动暂停\n")

    pending_tool_calls = {}
    emitted_tool_call_ids = set()

    async def run_agent():
        async for chunk in agent.astream(
            {
                "messages": [
                    HumanMessage(
                        content="""立即开始执行以下 10 个命令。

重要要求:
1. 执行每个命令前,先输出一条消息说明你要执行什么
2. 然后执行命令
3. 执行完后,输出一条消息说明执行结果
4. 然后继续下一个命令

命令列表:
1. echo "命令 1"
2. echo "命令 2"
3. echo "命令 3"
4. echo "命令 4"
5. echo "命令 5"
6. echo "命令 6"
7. echo "命令 7"
8. echo "命令 8"
9. echo "命令 9"
10. echo "命令 10"

按顺序执行,一次执行一个。使用 run_bash_command 工具。"""
                    )
                ]
            },
            config=config,
            stream_mode=["messages", "updates"],
        ):
            if isinstance(chunk, tuple) and len(chunk) == 2:
                mode, data = chunk

                if mode == "messages":
                    msg_chunk, _ = data
                    if hasattr(msg_chunk, "content") and msg_chunk.content:
                        if isinstance(msg_chunk.content, str):
                            print(msg_chunk.content, end="", flush=True)

                if mode == "updates":
                    if isinstance(data, dict):
                        for node_name, node_update in data.items():
                            if isinstance(node_update, dict):
                                messages = node_update.get("messages", [])
                                if not isinstance(messages, list):
                                    messages = [messages]

                                for msg in messages:
                                    msg_class = msg.__class__.__name__

                                    if msg_class == "AIMessage":
                                        for tc in getattr(msg, "tool_calls", []):
                                            tc_id = tc.get("id")
                                            if tc_id and tc_id not in emitted_tool_call_ids:
                                                emitted_tool_call_ids.add(tc_id)
                                                pending_tool_calls[tc_id] = {
                                                    "name": tc.get("name"),
                                                    "args": tc.get("args", {}),
                                                }

                                    elif msg_class == "ToolMessage":
                                        tc_id = getattr(msg, "tool_call_id", None)
                                        if tc_id in pending_tool_calls:
                                            pending_tool_calls.pop(tc_id)

    task = asyncio.create_task(run_agent())

    try:
        await asyncio.sleep(6)
        print("\n\n" + "=" * 60)
        print("⚠️  用户点击暂停")
        print("=" * 60)
        task.cancel()
        await task
    except asyncio.CancelledError:
        print("✓ 任务已停止\n")

        # 写入取消状态
        if pending_tool_calls:
            print(f"未完成的 tool call ({len(pending_tool_calls)} 个):")
            await write_cancel_state(checkpointer, config, pending_tool_calls)
            print("✓ 取消状态已保存\n")

    # 查看结果
    print("=" * 60)
    print("执行结果")
    print("=" * 60)
    print(f"已完成命令数: {len(executed_commands)}")
    for i, cmd in enumerate(executed_commands, 1):
        print(f"  {i}. {cmd}")

    # 查看 checkpoint
    print("\n" + "=" * 60)
    print("Checkpoint 状态")
    print("=" * 60)

    checkpoint_tuple = await checkpointer.aget_tuple(config)
    if checkpoint_tuple:
        messages = checkpoint_tuple.checkpoint["channel_values"]["messages"]
        print(f"消息总数: {len(messages)}\n")

        completed = 0
        cancelled = 0

        for msg in messages:
            if msg.__class__.__name__ == "ToolMessage":
                if "取消" in str(msg.content):
                    cancelled += 1
                else:
                    completed += 1

        print(f"已完成: {completed}")
        print(f"已取消: {cancelled}")

    # 验证
    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)

    if len(executed_commands) >= 2 and len(executed_commands) <= 5:
        print("✅ 测试成功:")
        print(f"  - 暂停前完成了 {len(executed_commands)} 个命令")
        print("  - 暂停机制正常工作")
        print("  - 已完成的工作已保存到 checkpoint")
        if cancelled > 0:
            print(f"  - 未完成的 {cancelled} 个 tool call 已标记为取消")
    else:
        print("❌ 测试失败:")
        print(f"  - 完成了 {len(executed_commands)} 个命令 (预期 2-5 个)")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
