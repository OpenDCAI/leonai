"""
测试场景 3: 多个 Tool Call
验证:
1. 第一个 tool call 完成并保存
2. 第二个 tool call 执行中被取消
3. 只有第二个被标记为取消
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
async def task_a(duration: int) -> str:
    """执行任务 A"""
    print(f"[Tool A] 开始执行,耗时 {duration} 秒")
    await asyncio.sleep(duration)
    print("[Tool A] 完成")
    return f"任务 A 完成,耗时 {duration} 秒"


@tool
async def task_b(duration: int) -> str:
    """执行任务 B"""
    print(f"[Tool B] 开始执行,耗时 {duration} 秒")
    await asyncio.sleep(duration)
    print("[Tool B] 完成")
    return f"任务 B 完成,耗时 {duration} 秒"


async def main():
    # 1. 初始化 checkpointer
    db_path = Path("/tmp/test_cancel_multi_tool.db")
    db_path.unlink(missing_ok=True)

    conn = await aiosqlite.connect(str(db_path))
    await conn.execute("PRAGMA journal_mode=WAL")
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()

    # 2. 创建 agent with tools
    model = init_chat_model("claude-sonnet-4-5-20250929")
    agent = create_agent(
        model=model,
        tools=[task_a, task_b],
        checkpointer=checkpointer,
    )

    # 3. 启动流式执行
    config = {"configurable": {"thread_id": "test-multi-tool-cancel"}}

    print("=== 开始流式执行 ===")
    print("提示: 等任务 A 完成后,在任务 B 执行时按 Ctrl+C 取消\n")

    task = None
    pending_tool_calls = {}
    emitted_tool_call_ids = set()
    completed_tool_calls = []

    try:

        async def run_stream():
            async for chunk in agent.astream(
                {"messages": [HumanMessage(content="请先执行 task_a(duration=2),然后执行 task_b(duration=10)")]},
                config=config,
                stream_mode=["messages", "updates"],
            ):
                yield chunk

        stream_gen = run_stream()
        task = asyncio.create_task(stream_gen.__anext__())

        while True:
            try:
                chunk = await task
                task = asyncio.create_task(stream_gen.__anext__())

                if isinstance(chunk, tuple) and len(chunk) == 2:
                    mode, data = chunk

                    # 处理 messages 模式
                    if mode == "messages":
                        msg_chunk, _ = data
                        if hasattr(msg_chunk, "content") and msg_chunk.content:
                            print(msg_chunk.content, end="", flush=True)

                    # 处理 updates 模式
                    elif mode == "updates":
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
                                                    print(f"\n[Tool Call] {tc.get('name')} - ID: {tc_id}")

                                        # 移除已完成的 tool call
                                        elif msg_class == "ToolMessage":
                                            tc_id = getattr(msg, "tool_call_id", None)
                                            if tc_id in pending_tool_calls:
                                                tool_info = pending_tool_calls.pop(tc_id)
                                                completed_tool_calls.append(
                                                    {
                                                        "id": tc_id,
                                                        "name": tool_info["name"],
                                                        "result": str(msg.content)[:50],
                                                    }
                                                )
                                                print(f"\n[Tool Result] {tool_info['name']} - ID: {tc_id}")

            except StopAsyncIteration:
                break

    except asyncio.CancelledError:
        print("\n\n=== 收到取消信号 ===")
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # 显示已完成的 tool call
        if completed_tool_calls:
            print(f"\n已完成的 tool call: {len(completed_tool_calls)}")
            for tc in completed_tool_calls:
                print(f"  ✓ {tc['name']} (ID: {tc['id']})")

        # 处理未完成的 tool call
        if pending_tool_calls:
            print(f"\n未完成的 tool call: {len(pending_tool_calls)}")

            # 获取当前 checkpoint
            current_state = await checkpointer.aget(config)

            if current_state:
                print("正在写入取消状态...")

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
                    print(f"  ✗ {tc_info['name']} (ID: {tc_id}) - 标记为取消")

                # 更新 checkpoint
                updated_values = current_state.values.copy()
                updated_values["messages"].extend(cancel_messages)

                await checkpointer.aput(
                    config,
                    {
                        "values": updated_values,
                        "next": (),
                    },
                    {},
                    current_state.config,
                )
                print("✓ 取消状态已写入 checkpoint")

    # 4. 检查 checkpointer 状态
    print("\n=== 检查 Checkpointer 状态 ===")

    checkpoint = await checkpointer.aget(config)
    if checkpoint:
        messages = checkpoint.values.get("messages", [])
        print("✓ Checkpoint 存在")
        print(f"✓ 保存的消息数: {len(messages)}")

        tool_call_count = 0
        tool_result_count = 0
        cancelled_count = 0

        for i, msg in enumerate(messages):
            msg_type = msg.__class__.__name__

            if msg_type == "AIMessage" and hasattr(msg, "tool_calls"):
                for tc in msg.tool_calls:
                    tool_call_count += 1
                    print(f"  [{i}] Tool Call: {tc.get('name')} (ID: {tc.get('id')})")

            elif msg_type == "ToolMessage":
                tool_result_count += 1
                content = str(msg.content)
                tc_id = getattr(msg, "tool_call_id", "N/A")
                name = getattr(msg, "name", "N/A")

                if "取消" in content:
                    cancelled_count += 1
                    print(f"  [{i}] Tool Result (CANCELLED): {name} (ID: {tc_id})")
                else:
                    print(f"  [{i}] Tool Result: {name} (ID: {tc_id}) - {content[:30]}...")

        print("\n统计:")
        print(f"  - Tool Call 总数: {tool_call_count}")
        print(f"  - Tool Result 总数: {tool_result_count}")
        print(f"  - 被取消的: {cancelled_count}")
        print(f"  - 成功完成的: {tool_result_count - cancelled_count}")

    else:
        print("✗ Checkpoint 不存在")

    # 5. 测试恢复
    print("\n=== 测试恢复 ===")
    print("发送新消息: '继续执行被取消的任务'\n")

    async for chunk in agent.astream(
        {"messages": [HumanMessage(content="继续执行被取消的任务")]},
        config=config,
        stream_mode=["messages"],
    ):
        if isinstance(chunk, tuple) and len(chunk) == 2:
            mode, data = chunk
            if mode == "messages":
                msg_chunk, _ = data
                if hasattr(msg_chunk, "content") and msg_chunk.content:
                    print(msg_chunk.content, end="", flush=True)

    print("\n\n=== 测试完成 ===")
    await conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
