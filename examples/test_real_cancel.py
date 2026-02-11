"""
真实场景测试: 模拟用户在 tool 执行过程中暂停
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
async def long_running_task(duration: int) -> str:
    """执行一个耗时任务"""
    print(f"[Tool] 开始执行,预计耗时 {duration} 秒")
    await asyncio.sleep(duration)
    print("[Tool] 完成")
    return f"任务完成,耗时 {duration} 秒"


async def main():
    print("=== 真实场景测试: 暂停正在执行的 Tool Call ===\n")

    # 1. 初始化
    db_path = Path("/tmp/test_real_cancel.db")
    db_path.unlink(missing_ok=True)

    conn = await aiosqlite.connect(str(db_path))
    await conn.execute("PRAGMA journal_mode=WAL")
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()

    model = init_chat_model("claude-sonnet-4-5-20250929")
    agent = create_agent(
        model=model,
        tools=[long_running_task],
        checkpointer=checkpointer,
    )

    config = {"configurable": {"thread_id": "test-real-cancel"}}

    # 2. 启动 agent,模拟流式执行
    print("步骤 1: 启动 agent,调用耗时 tool")
    print("提示: 检测到 tool call 后 2 秒自动取消\n")

    pending_tool_calls = {}
    emitted_tool_call_ids = set()
    tool_call_detected = asyncio.Event()

    async def run_agent():
        """模拟 main.py 的流式执行"""
        async for chunk in agent.astream(
            {"messages": [HumanMessage(content="请执行 long_running_task,duration=10")]},
            config=config,
            stream_mode=["messages", "updates"],
        ):
            if isinstance(chunk, tuple) and len(chunk) == 2:
                mode, data = chunk

                # 处理 updates 模式,追踪 tool call
                if mode == "updates":
                    if isinstance(data, dict):
                        for node_name, node_update in data.items():
                            if isinstance(node_update, dict):
                                messages = node_update.get("messages", [])
                                if not isinstance(messages, list):
                                    messages = [messages]

                                for msg in messages:
                                    msg_class = msg.__class__.__name__

                                    # 追踪 tool call
                                    if msg_class == "AIMessage":
                                        for tc in getattr(msg, "tool_calls", []):
                                            tc_id = tc.get("id")
                                            if tc_id and tc_id not in emitted_tool_call_ids:
                                                emitted_tool_call_ids.add(tc_id)
                                                pending_tool_calls[tc_id] = {
                                                    "name": tc.get("name"),
                                                    "args": tc.get("args", {}),
                                                }
                                                print(f"✓ Tool Call 开始: {tc.get('name')} (ID: {tc_id})")
                                                tool_call_detected.set()  # 通知检测到 tool call

                                    # 移除已完成的 tool call
                                    elif msg_class == "ToolMessage":
                                        tc_id = getattr(msg, "tool_call_id", None)
                                        if tc_id in pending_tool_calls:
                                            pending_tool_calls.pop(tc_id)
                                            print(f"✓ Tool Call 完成: ID: {tc_id}")

    # 3. 创建任务,等待 tool call 开始后再取消
    task = asyncio.create_task(run_agent())

    try:
        # 等待检测到 tool call
        await asyncio.wait_for(tool_call_detected.wait(), timeout=10)
        print("✓ 检测到 tool call,等待 2 秒后取消...\n")

        # 等待 2 秒让 tool 开始执行
        await asyncio.sleep(2)

        print("⚠️  模拟用户点击暂停,取消任务...\n")
        task.cancel()
        await task
    except TimeoutError:
        print("✗ 超时:未检测到 tool call")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    except asyncio.CancelledError:
        print("✓ 任务已取消\n")

        # 4. 检查是否有未完成的 tool call
        if pending_tool_calls:
            print(f"步骤 2: 发现 {len(pending_tool_calls)} 个未完成的 tool call")

            # 获取当前 checkpoint
            checkpoint_tuple = await checkpointer.aget_tuple(config)

            if checkpoint_tuple:
                checkpoint = checkpoint_tuple.checkpoint
                print(f"✓ 当前 checkpoint 消息数: {len(checkpoint['channel_values']['messages'])}")

                # 为每个未完成的 tool call 创建取消消息
                cancel_messages = []
                for tc_id, tc_info in pending_tool_calls.items():
                    cancel_messages.append(
                        ToolMessage(
                            content="任务被用户取消",
                            tool_call_id=tc_id,
                            name=tc_info["name"],
                        )
                    )
                    print(f"  - 为 {tc_info['name']} (ID: {tc_id}) 创建取消消息")

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
                    {},
                    checkpoint,
                )
                print("✓ 取消状态已写入 checkpoint\n")

        else:
            print("⚠️  没有未完成的 tool call (可能取消太晚)\n")

    # 5. 验证 checkpoint
    print("步骤 3: 验证 checkpoint 状态")
    checkpoint_tuple = await checkpointer.aget_tuple(config)
    if checkpoint_tuple:
        checkpoint = checkpoint_tuple.checkpoint
        messages = checkpoint["channel_values"]["messages"]
        print(f"✓ 最终消息数: {len(messages)}\n")

        # 显示所有消息
        for i, msg in enumerate(messages):
            msg_class = msg.__class__.__name__
            if msg_class == "AIMessage" and hasattr(msg, "tool_calls"):
                for tc in msg.tool_calls:
                    print(f"  [{i}] AIMessage.tool_call: {tc.get('name')} (ID: {tc.get('id')})")
            elif msg_class == "ToolMessage":
                content = str(msg.content)
                tc_id = getattr(msg, "tool_call_id", "N/A")
                name = getattr(msg, "name", "N/A")
                status = "CANCELLED" if "取消" in content else "COMPLETED"
                print(f"  [{i}] ToolMessage ({status}): {name} (ID: {tc_id})")
            else:
                content_preview = str(getattr(msg, "content", ""))[:50]
                print(f"  [{i}] {msg_class}: {content_preview}...")

        # 检查是否有取消消息
        has_cancel = any(isinstance(msg, ToolMessage) and "取消" in msg.content for msg in messages)

        if has_cancel:
            print("\n✅ 测试成功: 取消状态已正确保存到 checkpoint")
        else:
            print("\n❌ 测试失败: 未找到取消消息")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
