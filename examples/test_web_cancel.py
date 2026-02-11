#!/usr/bin/env python3
"""
Test script to verify web backend pause/resume functionality.
Tests that cancellation properly writes ToolMessage markers to checkpoint.
"""

import asyncio
import json
import time

import httpx


async def test_web_cancel():
    """Test cancellation through web API."""
    base_url = "http://localhost:8001"
    thread_id = f"test_cancel_{int(time.time())}"

    print(f"Testing cancellation with thread_id: {thread_id}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Start a long-running task
        print("\n1. Starting long-running task...")
        url = f"{base_url}/api/threads/{thread_id}/runs/stream"

        received_tool_calls = []
        received_tool_results = []
        cancelled_ids = []

        response = await client.post(
            url,
            json={"message": "请执行以下命令：echo 'step 1' && sleep 2 && echo 'step 2' && sleep 2 && echo 'step 3'"},
            headers={"Accept": "text/event-stream"},
            timeout=None,
        )

        async with response as stream:
            # Read a few events then cancel
            event_count = 0
            async for line in response.aiter_lines():
                if not line.strip():
                    continue

                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                    continue

                if line.startswith("data:"):
                    data_str = line.split(":", 1)[1].strip()
                    try:
                        data = json.loads(data_str)
                    except:
                        continue

                    if event_type == "tool_call":
                        print(f"   Tool call: {data['name']} (id: {data['id']})")
                        received_tool_calls.append(data["id"])

                    elif event_type == "tool_result":
                        print(f"   Tool result: {data['name']}")
                        received_tool_results.append(data["tool_call_id"])

                    elif event_type == "text":
                        print(f"   Text: {data['content'][:50]}...")

                    event_count += 1

                    # Cancel after receiving first tool call
                    if len(received_tool_calls) > 0 and len(received_tool_results) == 0:
                        print("\n2. Cancelling run...")
                        cancel_response = await client.post(f"{base_url}/api/threads/{thread_id}/runs/cancel")
                        print(f"   Cancel response: {cancel_response.json()}")
                        # Continue reading to get cancelled event
                        continue

                    if event_type == "cancelled":
                        print("\n3. Received cancelled event")
                        cancelled_ids = data.get("cancelled_tool_call_ids", [])
                        print(f"   Cancelled tool call IDs: {cancelled_ids}")
                        break

                    if event_type == "done":
                        print("\n   Task completed (should not reach here)")
                        break

        print("\n4. Summary:")
        print(f"   Total tool calls: {len(received_tool_calls)}")
        print(f"   Completed tool results: {len(received_tool_results)}")
        print(f"   Cancelled tool calls: {len(cancelled_ids)}")

        # Verify checkpoint contains cancellation markers
        print("\n5. Verifying checkpoint...")
        import pickle
        import sqlite3

        db_path = f"{os.path.expanduser('~')}/.leon/checkpoints.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT checkpoint FROM checkpoints WHERE thread_id = ? ORDER BY checkpoint_id DESC LIMIT 1",
            (thread_id,),
        )
        row = cursor.fetchone()

        if row:
            checkpoint = pickle.loads(row[0])
            messages = checkpoint["channel_values"]["messages"]

            # Find ToolMessages with cancellation content
            cancel_messages = [
                msg for msg in messages if msg.__class__.__name__ == "ToolMessage" and "取消" in str(msg.content)
            ]

            print(f"   Found {len(cancel_messages)} cancellation markers in checkpoint")
            for msg in cancel_messages:
                print(f"   - Tool call ID: {msg.tool_call_id}, Content: {msg.content}")

            if len(cancel_messages) == len(cancelled_ids):
                print("\n✅ SUCCESS: Cancellation markers correctly written to checkpoint")
            else:
                print(f"\n❌ FAILED: Expected {len(cancelled_ids)} markers, found {len(cancel_messages)}")
        else:
            print("   ❌ No checkpoint found")

        conn.close()

        # Test resume
        print("\n6. Testing resume...")
        async with client.stream(
            "POST",
            url,
            json={"message": "继续"},
        ) as response:
            async for line in response.aiter_lines():
                if not line.strip():
                    continue

                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                    continue

                if line.startswith("data:"):
                    data_str = line.split(":", 1)[1].strip()
                    try:
                        data = json.loads(data_str)
                    except:
                        continue

                    if event_type == "text":
                        print(f"   Resume text: {data['content'][:100]}...")

                    if event_type == "done":
                        print("\n✅ Resume completed successfully")
                        break


if __name__ == "__main__":
    import os

    asyncio.run(test_web_cancel())
