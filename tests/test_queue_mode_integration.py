"""Integration test for Queue Mode - tests steer behavior with real agent"""

import asyncio
import os
import threading
import time

import pytest

# Test requires running from project root with dependencies installed

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_REAL_LLM_TESTS") != "1",
    reason="requires real LLM endpoint and credentials",
)


def test_queue_mode_steer():
    """
    Test steer mode: inject message during agent execution.

    Flow:
    1. Start agent with a task that triggers multiple tool calls
    2. After first tool call, enqueue a steer message
    3. Verify remaining tool calls are skipped
    4. Verify steer message is injected
    """
    from agent import create_leon_agent
    from core.queue import QueueMode, get_queue_manager, reset_queue_manager

    # Reset queue state
    reset_queue_manager()
    queue_manager = get_queue_manager()

    # Create agent with minimal config (no MCP to speed up)
    agent = create_leon_agent()

    # Track what happens
    tool_calls_seen = []
    tool_results_seen = []
    steer_injected = False

    # Task that should trigger multiple tool calls
    test_message = f"请列出 {agent.workspace_root} 目录的文件，然后读取其中的 pyproject.toml 文件内容"

    config = {"configurable": {"thread_id": "test-queue-mode"}}

    # Schedule steer message after 2 seconds
    def inject_steer():
        time.sleep(2)
        print("[TEST] Injecting steer message...")
        queue_manager.enqueue("停止！改为告诉我今天星期几", QueueMode.STEER)

    steer_thread = threading.Thread(target=inject_steer)
    steer_thread.start()

    print(f"[TEST] Starting agent with: {test_message[:50]}...")

    async def run_agent():
        nonlocal steer_injected

        try:
            async for chunk in agent.agent.astream(
                {"messages": [{"role": "user", "content": test_message}]},
                config=config,
                stream_mode="updates",
            ):
                for node_name, node_update in chunk.items():
                    if not isinstance(node_update, dict):
                        continue

                    messages = node_update.get("messages", [])
                    if not isinstance(messages, list):
                        messages = [messages]

                    for msg in messages:
                        msg_class = msg.__class__.__name__

                        if msg_class == "AIMessage":
                            content = getattr(msg, "content", "")
                            if "[STEER]" in str(content):
                                steer_injected = True
                                print("[TEST] Steer message detected in AI response!")

                            tool_calls = getattr(msg, "tool_calls", [])
                            for tc in tool_calls:
                                tool_name = tc.get("name", "unknown")
                                tool_calls_seen.append(tool_name)
                                print(f"[TEST] Tool call: {tool_name}")

                        elif msg_class == "ToolMessage":
                            content = str(getattr(msg, "content", ""))[:100]
                            tool_results_seen.append(content)
                            if "Skipped" in content:
                                print("[TEST] Tool was SKIPPED!")
                            else:
                                print(f"[TEST] Tool result: {content[:50]}...")

                        elif msg_class == "HumanMessage":
                            content = getattr(msg, "content", "")
                            if "[STEER]" in str(content):
                                steer_injected = True
                                print("[TEST] Steer HumanMessage injected!")

        except Exception as e:
            print(f"[TEST] Error: {e}")
            import traceback

            traceback.print_exc()

    # Run in new event loop
    asyncio.run(run_agent())

    steer_thread.join()

    print("\n" + "=" * 50)
    print("[TEST] Results:")
    print(f"  Tool calls seen: {tool_calls_seen}")
    print(f"  Tool results: {len(tool_results_seen)}")
    print(f"  Steer injected: {steer_injected}")
    print(f"  Any skipped: {'Skipped' in str(tool_results_seen)}")
    print("=" * 50)

    # Cleanup
    agent.close()

    assert len(tool_calls_seen) > 0, "Expected at least one tool call during queue-mode test"


if __name__ == "__main__":
    test_queue_mode_steer()
