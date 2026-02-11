#!/usr/bin/env python3
"""
Check checkpoint for cancellation markers.
"""

import asyncio

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


async def check_checkpoint():
    thread_id = "test_cancel_1770786177"

    import os

    db_path = os.path.expanduser("~/.leon/leon.db")
    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = await checkpointer.aget(config)

        if not checkpoint:
            print(f"❌ No checkpoint found for thread_id: {thread_id}")
            return

        messages = checkpoint["channel_values"]["messages"]
        print(f"✓ Found checkpoint with {len(messages)} messages")

        print("\nLast 5 messages:")
        for i, msg in enumerate(messages[-5:], 1):
            msg_class = msg.__class__.__name__
            print(f"\n{i}. {msg_class}")
            if msg_class == "ToolMessage":
                print(f"   tool_call_id: {msg.tool_call_id}")
                print(f"   name: {msg.name}")
                print(f"   content: {msg.content[:100]}")
            elif msg_class == "AIMessage":
                tool_calls = getattr(msg, "tool_calls", [])
                if tool_calls:
                    print(f"   tool_calls: {len(tool_calls)}")
                    for tc in tool_calls:
                        print(f"     - {tc.get('name')} (id: {tc.get('id')[:20]}...)")

        # Find cancellation markers
        cancel_messages = [
            msg for msg in messages if msg.__class__.__name__ == "ToolMessage" and "取消" in str(msg.content)
        ]

        print(f"\n{'=' * 60}")
        if cancel_messages:
            print(f"✅ SUCCESS: Found {len(cancel_messages)} cancellation marker(s)")
            for msg in cancel_messages:
                print(f"\n   Tool call ID: {msg.tool_call_id}")
                print(f"   Name: {msg.name}")
                print(f"   Content: {msg.content}")
        else:
            print("❌ FAILED: No cancellation markers found")


if __name__ == "__main__":
    asyncio.run(check_checkpoint())
