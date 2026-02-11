#!/usr/bin/env python3
"""
Automated test using backend API directly.
"""

import asyncio
import json
import os
import pickle
import sqlite3
import time

import httpx


async def test_cancel_via_api():
    """Test cancellation through backend API."""
    base_url = "http://localhost:8001"
    thread_id = f"test_cancel_{int(time.time())}"

    print(f"Testing cancellation with thread_id: {thread_id}")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Start a long-running task
        print("\n1. Starting long-running task...")
        url = f"{base_url}/api/threads/{thread_id}/runs"

        received_tool_calls = []
        received_tool_results = []
        cancelled_ids = []
        cancel_sent = False

        try:
            async with client.stream(
                "POST",
                url,
                json={
                    "message": "请执行以下命令：echo 'step 1' && sleep 5 && echo 'step 2' && sleep 5 && echo 'step 3'"
                },
            ) as response:
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    # Parse SSE format
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
                            print(f"   ✓ Tool call: {data['name']} (id: {data['id'][:8]}...)")
                            received_tool_calls.append(data["id"])

                        elif event_type == "tool_result":
                            print(f"   ✓ Tool result: {data['name']}")
                            received_tool_results.append(data["tool_call_id"])

                        elif event_type == "text":
                            content = data.get("content", "")
                            if content.strip():
                                print(f"   ✓ Text: {content[:50]}...")

                        # Cancel after receiving first tool call but before result
                        if len(received_tool_calls) > 0 and len(received_tool_results) == 0 and not cancel_sent:
                            print("\n2. Sending cancellation request...")
                            await asyncio.sleep(0.5)  # Give it a moment to start executing

                            cancel_response = await client.post(f"{base_url}/api/threads/{thread_id}/runs/cancel")
                            print(f"   ✓ Cancel response: {cancel_response.json()}")
                            cancel_sent = True

                        if event_type == "cancelled":
                            print("\n3. ✓ Received cancelled event")
                            cancelled_ids = data.get("cancelled_tool_call_ids", [])
                            print(f"   Cancelled tool call IDs: {[id[:8] + '...' for id in cancelled_ids]}")
                            break

                        if event_type == "done":
                            print("\n   Task completed normally (unexpected)")
                            break

                        if event_type == "error":
                            print(f"\n   Error: {data}")
                            break

        except httpx.ReadTimeout:
            print("\n   Request timed out (expected if cancel didn't work)")
        except Exception as e:
            print(f"\n   Exception: {e}")

        print("\n4. Summary:")
        print(f"   Total tool calls: {len(received_tool_calls)}")
        print(f"   Completed tool results: {len(received_tool_results)}")
        print(f"   Cancelled tool calls: {len(cancelled_ids)}")

        # Verify checkpoint contains cancellation markers
        print("\n5. Verifying checkpoint...")
        await asyncio.sleep(1)  # Give checkpoint time to write

        db_path = os.path.expanduser("~/.leon/checkpoints.db")
        if not os.path.exists(db_path):
            print(f"   ❌ Checkpoint database not found: {db_path}")
            return

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
                print(f"   - Tool call ID: {msg.tool_call_id[:8]}...")
                print(f"     Name: {msg.name}")
                print(f"     Content: {msg.content}")

            if len(cancel_messages) == len(cancelled_ids):
                print("\n   ✅ SUCCESS: Cancellation markers correctly written to checkpoint")
            else:
                print(f"\n   ❌ FAILED: Expected {len(cancelled_ids)} markers, found {len(cancel_messages)}")
        else:
            print("   ❌ No checkpoint found")

        conn.close()

        # Test resume
        print("\n6. Testing resume...")
        try:
            async with client.stream(
                "POST",
                url,
                json={"message": "继续"},
            ) as response:
                resume_text = []
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
                            content = data.get("content", "")
                            if content.strip():
                                resume_text.append(content)
                                print(f"   ✓ Resume text: {content[:80]}...")

                        if event_type == "done":
                            print("\n   ✅ Resume completed successfully")
                            break

                        if event_type == "error":
                            print(f"\n   ❌ Resume error: {data}")
                            break

                if resume_text:
                    full_text = "".join(resume_text)
                    if "取消" in full_text or "cancelled" in full_text.lower():
                        print("   ✅ Agent acknowledged cancellation")
                    else:
                        print("   ⚠️  Agent may not have seen cancellation marker")

        except Exception as e:
            print(f"   ❌ Resume failed: {e}")

        print("\n" + "=" * 60)
        print("Test completed!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_cancel_via_api())
