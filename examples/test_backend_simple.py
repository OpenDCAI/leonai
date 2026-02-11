#!/usr/bin/env python3
"""
Direct test of backend streaming API.
"""

import json
import time

import requests


def test_streaming():
    base_url = "http://localhost:8001"
    thread_id = f"test_cancel_{int(time.time())}"

    print(f"Testing with thread_id: {thread_id}")
    print("=" * 60)

    # Start streaming request
    print("\n1. Starting streaming request...")
    url = f"{base_url}/api/threads/{thread_id}/runs"

    try:
        response = requests.post(
            url, json={"message": "请执行以下命令：echo 'step 1' && sleep 5 && echo 'step 2'"}, stream=True, timeout=30
        )

        print(f"   Response status: {response.status_code}")
        print(f"   Response headers: {dict(response.headers)}")

        if response.status_code != 200:
            print(f"   Error: {response.text}")
            return

        # Read events
        tool_calls = []
        event_type = None

        for line in response.iter_lines():
            if not line:
                continue

            line = line.decode("utf-8")
            print(f"   Raw line: {line[:100]}")

            if line.startswith("event:"):
                event_type = line.split(":", 1)[1].strip()
                print(f"   -> Event type: {event_type}")

            elif line.startswith("data:"):
                data_str = line.split(":", 1)[1].strip()
                try:
                    data = json.loads(data_str)
                    print(f"   -> Data: {json.dumps(data, ensure_ascii=False)[:100]}")

                    if event_type == "tool_call":
                        tool_calls.append(data["id"])
                        print(f"   ✓ Tool call received: {data['name']}")

                        # Cancel after first tool call
                        if len(tool_calls) == 1:
                            print("\n2. Sending cancel request...")
                            cancel_resp = requests.post(f"{base_url}/api/threads/{thread_id}/runs/cancel")
                            print(f"   Cancel response: {cancel_resp.json()}")

                    elif event_type == "cancelled":
                        print("\n3. ✓ Received cancelled event!")
                        print(f"   Cancelled IDs: {data.get('cancelled_tool_call_ids', [])}")
                        break

                    elif event_type == "done":
                        print("\n   Task completed (unexpected)")
                        break

                except json.JSONDecodeError as e:
                    print(f"   JSON decode error: {e}")

    except requests.exceptions.RequestException as e:
        print(f"\n   Request error: {e}")

    print("\n" + "=" * 60)
    print("Test completed")


if __name__ == "__main__":
    test_streaming()
