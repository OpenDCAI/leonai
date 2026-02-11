"""
测试场景 1: 取消 LLM 生成
验证: checkpointer 是否保存了取消前已完成的 node
"""

import asyncio
from pathlib import Path

import aiosqlite
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


async def main():
    # 1. 初始化 checkpointer
    db_path = Path("/tmp/test_cancel_llm.db")
    db_path.unlink(missing_ok=True)

    conn = await aiosqlite.connect(str(db_path))
    await conn.execute("PRAGMA journal_mode=WAL")
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()

    # 2. 创建简单 agent (无 tools)
    model = init_chat_model("claude-sonnet-4-5-20250929")
    agent = create_agent(
        model=model,
        tools=[],
        checkpointer=checkpointer,
    )

    # 3. 启动流式执行
    config = {"configurable": {"thread_id": "test-llm-cancel"}}

    print("=== 开始流式执行 ===")
    print("提示: 看到输出后按 Ctrl+C 取消\n")

    task = None
    try:

        async def run_stream():
            async for chunk in agent.astream(
                {"messages": [HumanMessage(content="请写一篇关于 Python 异步编程的长文章,至少 500 字")]},
                config=config,
                stream_mode=["messages", "updates"],
            ):
                yield chunk

        stream_gen = run_stream()
        task = asyncio.create_task(stream_gen.__anext__())

        chunk_count = 0
        while True:
            try:
                chunk = await task
                task = asyncio.create_task(stream_gen.__anext__())

                # 打印 token
                if isinstance(chunk, tuple) and len(chunk) == 2:
                    mode, data = chunk
                    if mode == "messages":
                        msg_chunk, _ = data
                        if hasattr(msg_chunk, "content") and msg_chunk.content:
                            print(msg_chunk.content, end="", flush=True)
                            chunk_count += 1

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

    # 4. 检查 checkpointer 状态
    print("\n=== 检查 Checkpointer 状态 ===")

    checkpoint = await checkpointer.aget(config)
    if checkpoint:
        messages = checkpoint.values.get("messages", [])
        print("✓ Checkpoint 存在")
        print(f"✓ 保存的消息数: {len(messages)}")

        for i, msg in enumerate(messages):
            msg_type = msg.__class__.__name__
            content_preview = str(msg.content)[:100] if hasattr(msg, "content") else ""
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
