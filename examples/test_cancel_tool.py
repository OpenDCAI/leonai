"""
测试场景 2: 取消 Tool Call
验证:
1. checkpointer 是否保存了已完成的 tool call
2. 能否为未完成的 tool call 写入取消状态
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
async def slow_task(duration: int) -> str:
    """执行一个耗时任务"""
    print(f"[Tool] 开始执行 slow_task(duration={duration})")
    await asyncio.sleep(duration)
    print("[Tool] slow_task 完成")
    return f"任务完成,耗时 {duration} 秒"


async def main():
    # 1. 初始化 checkpointer
    db_path = Path("/tmp/test_cancel_tool.db")
    db_path.unlink(missing_ok=True)

    conn = await aiosqlite.connect(str(db_path))
    await conn.execute("PRAGMA journal_mode=WAL")
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()

    # 2. 创建 agent with tool
    model = init_chat_model("claude-sonnet-4-5-20250929")
    agent = create_agent(
        model=model,
        tools=[slow_task],
        checkpointer=checkpointer,
    )

    # 3. 启动流式执行
    config = {"configurable": {"thread_id": "test-tool-cancel"}}

    print("=== 开始流式执行 ===")
    print("提示: 看到 tool call 开始后按 Ctrl+C 取消\n")

    task = None
    pending_tool_calls = {}
    emitted_tool_call_ids = set()

    try:

        async def run_stream():
            async for chunk in agent.astream(
                {"messages": [HumanMessage(content="请执行一个耗时 10 秒的任务")]},
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
                                                pending_tool_calls.pop(tc_id)
                                                print(f"\n[Tool Result] ID: {tc_id}")

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

        # 处理未完成的 tool call
        if pending_tool_calls:
            print(f"发现 {len(pending_tool_calls)} 个未完成的 tool call")

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
                    print(f"  - Tool Call {tc_id} ({tc_info['name']}) 标记为取消")

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

        for i, msg in enumerate(messages):
            msg_type = msg.__class__.__name__
            if msg_type == "ToolMessage":
                content = str(msg.content)
                tc_id = getattr(msg, "tool_call_id", "N/A")
                print(f"  [{i}] {msg_type}: tool_call_id={tc_id}, content={content}")
            else:
                content_preview = str(getattr(msg, "content", ""))[:50]
                print(f"  [{i}] {msg_type}: {content_preview}...")
    else:
        print("✗ Checkpoint 不存在")

    # 5. 测试恢复
    print("\n=== 测试恢复 ===")
    print("发送新消息: '继续'\n")

    async for chunk in agent.astream(
        {"messages": [HumanMessage(content="继续")]},
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
