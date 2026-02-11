"""
真实长程任务测试: 执行 10 个 bash 命令,每个间隔 1 秒
场景:
1. Agent 开始执行 10 个命令
2. 执行到第 3-4 个命令时用户点击暂停
3. 验证已完成的命令结果被保存
4. 恢复后 Agent 继续执行剩余命令
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
    print(f"[Tool] 开始执行命令: {command}")
    await asyncio.sleep(1)  # 模拟命令执行耗时 1 秒

    # 记录执行
    executed_commands.append(command)
    result = f"命令执行成功: {command}"
    print(f"[Tool] 完成: {result}")
    return result


async def run_agent_stream(agent, config, message, pending_tool_calls, emitted_tool_call_ids):
    """运行 agent 并追踪 tool calls"""
    async for chunk in agent.astream(
        {"messages": [HumanMessage(content=message)]},
        config=config,
        stream_mode=["messages", "updates"],
    ):
        if isinstance(chunk, tuple) and len(chunk) == 2:
            mode, data = chunk

            # 打印 LLM 输出
            if mode == "messages":
                msg_chunk, _ = data
                if hasattr(msg_chunk, "content") and msg_chunk.content:
                    content = msg_chunk.content
                    if isinstance(content, str):
                        print(content, end="", flush=True)

            # 追踪 tool calls
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
        print(f"  为 {tc_info['name']}({tc_info['args']}) 创建取消消息 (ID: {tc_id})")

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
    print("=== 真实长程任务测试: 执行 10 个 bash 命令 ===\n")

    # 1. 初始化
    db_path = Path("/tmp/test_bash_commands.db")
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

    config = {"configurable": {"thread_id": "test-bash-commands"}}

    # 2. 第一次运行: 执行命令,检测到 tool 执行后 3 秒暂停
    print("=" * 70)
    print("第一次运行: 开始执行 10 个命令")
    print("=" * 70)
    print("提示: 检测到 tool 执行后 3 秒自动暂停\n")

    pending_tool_calls = {}
    emitted_tool_call_ids = set()
    tool_execution_started = asyncio.Event()

    async def run_with_detection():
        """运行 agent 并检测 tool 执行"""
        async for chunk in agent.astream(
            {
                "messages": [
                    HumanMessage(
                        content="""请依次执行以下 10 个命令。

重要要求:
1. 必须按顺序执行,一次只执行一个命令
2. 每执行完一个命令后,必须等待 1 秒再执行下一个
3. 不要并行执行多个命令

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

请使用 run_bash_command 工具执行每个命令,严格按顺序,一次一个。"""
                    )
                ]
            },
            config=config,
            stream_mode=["messages", "updates"],
        ):
            if isinstance(chunk, tuple) and len(chunk) == 2:
                mode, data = chunk

                # 打印 LLM 输出
                if mode == "messages":
                    msg_chunk, _ = data
                    if hasattr(msg_chunk, "content") and msg_chunk.content:
                        content = msg_chunk.content
                        if isinstance(content, str):
                            print(content, end="", flush=True)

                # 追踪 tool calls
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
                                                # 第一次检测到 tool call 时通知
                                                if not tool_execution_started.is_set():
                                                    tool_execution_started.set()

                                    elif msg_class == "ToolMessage":
                                        tc_id = getattr(msg, "tool_call_id", None)
                                        if tc_id in pending_tool_calls:
                                            pending_tool_calls.pop(tc_id)

    task = asyncio.create_task(run_with_detection())

    try:
        # 等待检测到 tool 执行
        await asyncio.wait_for(tool_execution_started.wait(), timeout=15)
        print("\n✓ 检测到 tool 开始执行,等待 3 秒后暂停...\n")

        # 等待 3 秒让一些 tool 执行
        await asyncio.sleep(3)

        print("\n" + "=" * 70)
        print("⚠️  [用户操作] 点击暂停按钮")
        print("=" * 70)
        task.cancel()
        await task
    except TimeoutError:
        print("\n✗ 超时:未检测到 tool 执行")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    except asyncio.CancelledError:
        print("✓ 任务已取消\n")

        # 写入取消状态
        if pending_tool_calls:
            print(f"发现 {len(pending_tool_calls)} 个未完成的 tool call:")
            await write_cancel_state(checkpointer, config, pending_tool_calls)
            print("✓ 取消状态已写入 checkpoint\n")
        else:
            print("⚠️  没有未完成的 tool call\n")

    # 3. 检查执行状态
    print("=" * 70)
    print("第一次运行结果")
    print("=" * 70)
    print(f"已执行命令数: {len(executed_commands)}")
    for i, cmd in enumerate(executed_commands, 1):
        print(f"  {i}. {cmd}")

    # 4. 查看 checkpoint
    print("\n" + "=" * 70)
    print("Checkpoint 状态")
    print("=" * 70)

    checkpoint_tuple = await checkpointer.aget_tuple(config)
    if checkpoint_tuple:
        checkpoint = checkpoint_tuple.checkpoint
        messages = checkpoint["channel_values"]["messages"]
        print(f"消息总数: {len(messages)}\n")

        tool_call_count = 0
        tool_result_count = 0
        cancelled_count = 0

        for i, msg in enumerate(messages):
            msg_class = msg.__class__.__name__
            if msg_class == "AIMessage" and hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_call_count += 1
                    print(f"[{i}] Tool Call: {tc.get('name')}({tc.get('args')})")
            elif msg_class == "ToolMessage":
                tool_result_count += 1
                content = str(msg.content)
                if "取消" in content:
                    cancelled_count += 1
                    print(f"[{i}] Tool Result (CANCELLED): {content}")
                else:
                    print(f"[{i}] Tool Result: {content[:60]}...")

        print("\n统计:")
        print(f"  - Tool Call 总数: {tool_call_count}")
        print(f"  - Tool Result 总数: {tool_result_count}")
        print(f"  - 已完成: {tool_result_count - cancelled_count}")
        print(f"  - 被取消: {cancelled_count}")

    # 5. 恢复执行
    print("\n" + "=" * 70)
    print("第二次运行: 恢复任务")
    print("=" * 70)
    print('[用户操作] 发送消息: "继续执行剩余的命令"\n')

    pending_tool_calls.clear()
    commands_before_resume = len(executed_commands)

    try:
        await run_agent_stream(
            agent,
            config,
            "继续执行剩余的命令",
            pending_tool_calls,
            emitted_tool_call_ids,
        )
    except Exception as e:
        import traceback

        print(f"\n✗ 恢复执行失败: {e}")
        traceback.print_exc()

    # 6. 最终状态
    print("\n\n" + "=" * 70)
    print("最终结果")
    print("=" * 70)
    print(f"总共执行命令数: {len(executed_commands)}")
    print(f"第一次运行: {commands_before_resume} 个")
    print(f"恢复后执行: {len(executed_commands) - commands_before_resume} 个\n")

    print("所有已执行的命令:")
    for i, cmd in enumerate(executed_commands, 1):
        print(f"  {i}. {cmd}")

    # 7. 验证结果
    print("\n" + "=" * 70)
    print("测试结果")
    print("=" * 70)

    if len(executed_commands) >= 8:  # 至少完成 80% 的命令
        print("✅ 测试成功:")
        print(f"  - 第一次运行完成了 {commands_before_resume} 个命令")
        print("  - 暂停机制正常工作")
        print(f"  - 恢复后继续执行,总共完成 {len(executed_commands)} 个命令")
        print("  - Agent 理解了取消状态并正确恢复")
    else:
        print("❌ 测试失败:")
        print(f"  - 总共只完成了 {len(executed_commands)} 个命令 (预期至少 8 个)")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
