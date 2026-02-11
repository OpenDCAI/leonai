#!/usr/bin/env python3
"""
Simple test to verify cancellation works with existing thread.
"""

import asyncio

import httpx


async def test_cancel():
    base_url = "http://localhost:8001"

    # Use existing thread
    thread_id = "238d6481-9d57-4a77-b750-a5a691559627"

    print(f"Testing with thread: {thread_id}")
    print("\n请在浏览器中打开 http://localhost:5173")
    print("然后发送一个长任务，比如：")
    print("  '请执行 sleep 10 && echo done'")
    print("\n等看到 tool call 后，点击红色停止按钮")
    print("\n按 Enter 继续...")
    input()

    # Just verify the cancel endpoint works
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{base_url}/api/threads/{thread_id}/runs/cancel")
            print(f"\n取消请求响应: {response.json()}")
        except Exception as e:
            print(f"\n取消请求失败: {e}")


if __name__ == "__main__":
    asyncio.run(test_cancel())
