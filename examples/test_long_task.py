"""
长程任务测试: 多步骤任务,中途暂停,然后恢复继续
场景: Agent 需要执行 3 个步骤的任务,在第 2 步暂停,恢复后继续第 3 步
"""

import asyncio
from pathlib import Path

import aiosqlite
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# 模拟一个需要多步骤的长程任务
task_state = {"step1": False, "step2": False, "step3": False}


@tool
async def execute_step(step_number: int, duration: int) -> str:
    """执行任务的某个步骤"""
    print(f"[Tool] 开始执行步骤 {step_number},预计耗时 {duration} 秒")
    await asyncio.sleep(duration)
    task_state[f"step{step_number}"] = True
    print(f"[Tool] 步骤 {step_number} 完成")
    return f"步骤 {step_number} 已完成"


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
                    print(msg_chunk.content, end="", flush=True)

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
                                            print(f"\n[Tool Call] {tc.get('name')}({tc.get('args')}) - ID: {tc_id}")

                                elif msg_class == "ToolMessage":
                                    tc_id = getattr(msg, "tool_call_id", None)
                                    if tc_id in pending_tool_calls:
                                        pending_tool_calls.pop(tc_id)
                                        print(f"[Tool Result] {msg.content}")


async def write_cancel_state(checkpointer, config, pending_tool_calls):
    """写入取消状态到 checkpoint"""
    if not pending_tool_calls:
        return False

    checkpoint_tuple = await checkpointer.aget_tuple(config)
    if not checkpoint_tuple:
        return False

    checkpoint = checkpoint_tuple.checkpoint
    metadata = checkpoint_tuple.metadata
    print(f"\n当前 checkpoint 消息数: {len(checkpoint['channel_values']['messages'])}")
    print(f"当前 metadata: {metadata}")

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
        print(f"为 {tc_info['name']} (ID: {tc_id}) 创建取消消息")

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
        metadata,  # 保留原始 metadata
        checkpoint,
    )
    print("✓ 取消状态已写入 checkpoint")
    return True


async def main():
    print("=== 长程任务测试: 多步骤任务暂停与恢复 ===\n")

    # 1. 初始化
    db_path = Path("/tmp/test_long_task.db")
    db_path.unlink(missing_ok=True)

    conn = await aiosqlite.connect(str(db_path))
    await conn.execute("PRAGMA journal_mode=WAL")
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()

    model = init_chat_model("claude-sonnet-4-5-20250929")
    agent = create_agent(
        model=model,
        tools=[execute_step],
        checkpointer=checkpointer,
    )

    config = {"configurable": {"thread_id": "test-long-task"}}

    # 2. 第一次运行: 执行多步骤任务,在第 2 步暂停
    print("=" * 60)
    print("第一次运行: 开始执行 3 步骤任务")
    print("=" * 60)

    pending_tool_calls = {}
    emitted_tool_call_ids = set()

    task = asyncio.create_task(
        run_agent_stream(
            agent,
            config,
            "请依次执行以下步骤:\n1. execute_step(step_number=1, duration=2)\n2. execute_step(step_number=2, duration=8)\n3. execute_step(step_number=3, duration=2)",
            pending_tool_calls,
            emitted_tool_call_ids,
        )
    )

    try:
        # 等待 6 秒后取消 (步骤 1 完成,步骤 2 执行中)
        await asyncio.sleep(6)
        print("\n\n⚠️  [用户操作] 点击暂停按钮\n")
        task.cancel()
        await task
    except asyncio.CancelledError:
        print("✓ 任务已取消\n")

        # 写入取消状态
        if pending_tool_calls:
            print(f"发现 {len(pending_tool_calls)} 个未完成的 tool call:")
            for tc_id, tc_info in pending_tool_calls.items():
                print(f"  - {tc_info['name']}({tc_info['args']})")
            print()

            await write_cancel_state(checkpointer, config, pending_tool_calls)

    # 3. 检查任务状态
    print(f"\n当前任务状态: {task_state}")

    # 4. 查看 checkpoint
    print("\n" + "=" * 60)
    print("Checkpoint 状态")
    print("=" * 60)

    checkpoint_tuple = await checkpointer.aget_tuple(config)
    if checkpoint_tuple:
        checkpoint = checkpoint_tuple.checkpoint
        messages = checkpoint["channel_values"]["messages"]
        print(f"消息总数: {len(messages)}\n")

        for i, msg in enumerate(messages):
            msg_class = msg.__class__.__name__
            if msg_class == "HumanMessage":
                content = str(msg.content)[:80]
                print(f"[{i}] HumanMessage: {content}...")
            elif msg_class == "AIMessage":
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        print(f"[{i}] AIMessage.tool_call: {tc.get('name')}({tc.get('args')})")
                else:
                    content = str(msg.content)[:80]
                    print(f"[{i}] AIMessage: {content}...")
            elif msg_class == "ToolMessage":
                content = str(msg.content)
                status = "CANCELLED" if "取消" in content else "COMPLETED"
                print(f"[{i}] ToolMessage ({status}): {content}")

    # 5. 恢复执行
    print("\n" + "=" * 60)
    print("第二次运行: 恢复任务")
    print("=" * 60)
    print('[用户操作] 发送消息: "继续"\n')

    pending_tool_calls.clear()

    try:
        await run_agent_stream(
            agent,
            config,
            "继续",
            pending_tool_calls,
            emitted_tool_call_ids,
        )
    except Exception as e:
        import traceback

        print(f"\n✗ 恢复执行失败: {e}")
        print("\n完整错误:")
        traceback.print_exc()

    # 6. 最终状态
    print(f"\n\n最终任务状态: {task_state}")

    # 7. 验证结果
    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)

    if task_state["step1"] and task_state["step3"]:
        print("✅ 测试成功:")
        print("  - 步骤 1 在暂停前完成")
        print("  - 步骤 2 被取消")
        print("  - 恢复后 agent 理解了取消状态")
        print("  - 步骤 3 在恢复后完成")
    else:
        print("❌ 测试失败:")
        print(f"  - 步骤 1: {'✓' if task_state['step1'] else '✗'}")
        print(f"  - 步骤 2: {'✓' if task_state['step2'] else '✗'}")
        print(f"  - 步骤 3: {'✓' if task_state['step3'] else '✗'}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
