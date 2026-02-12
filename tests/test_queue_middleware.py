"""Tests for Queue Mode middleware"""

import threading
import time
from pathlib import Path

import pytest

# Read source files directly without importing middleware package
project_root = Path(__file__).parent.parent

# Load types module in isolated namespace
types_code = (project_root / "middleware/queue/types.py").read_text()
types_ns = {}
exec(compile(types_code, "types.py", "exec"), types_ns)
QueueMode = types_ns["QueueMode"]
QueueMessage = types_ns["QueueMessage"]

# Load manager module - need to inject types
manager_code = (project_root / "middleware/queue/manager.py").read_text()
# Replace relative import with injected values
manager_code = manager_code.replace(
    "from .types import QueueMessage, QueueMode",
    "",  # Remove import, we'll inject
)
manager_ns = {
    "QueueMessage": QueueMessage,
    "QueueMode": QueueMode,
    "threading": threading,
    "deque": __import__("collections").deque,
    "Optional": __import__("typing").Optional,
}
exec(compile(manager_code, "manager.py", "exec"), manager_ns)
MessageQueueManager = manager_ns["MessageQueueManager"]
get_queue_manager = manager_ns["get_queue_manager"]
reset_queue_manager = manager_ns["reset_queue_manager"]


# Mock HumanMessage for middleware test (avoid langchain dependency)
class MockHumanMessage:
    def __init__(self, content):
        self.content = content


# Mock ToolMessage
class MockToolMessage:
    def __init__(self, content, tool_call_id=""):
        self.content = content
        self.tool_call_id = tool_call_id


# Mock AgentMiddleware base class
class MockAgentMiddleware:
    @property
    def name(self):
        return self.__class__.__name__


# Load middleware module
middleware_code = (project_root / "middleware/queue/middleware.py").read_text()
# Remove imports we'll inject
middleware_code = middleware_code.replace("from langchain_core.messages import HumanMessage, ToolMessage", "")
middleware_code = middleware_code.replace("from .manager import get_queue_manager", "")
# Replace the try/except import block
import_block = """try:
    from langchain.agents.middleware.types import (
        AgentMiddleware,
        ModelCallResult,
        ModelRequest,
        ModelResponse,
        ToolCallRequest,
    )
except ImportError:
    # Fallback for environments without langchain
    class AgentMiddleware:
        pass
    ModelRequest = Any
    ModelResponse = Any
    ModelCallResult = Any
    ToolCallRequest = Any"""
middleware_code = middleware_code.replace(import_block, "")

from collections.abc import Awaitable, Callable

middleware_ns = {
    "get_queue_manager": get_queue_manager,
    "HumanMessage": MockHumanMessage,
    "ToolMessage": MockToolMessage,
    "AgentMiddleware": MockAgentMiddleware,
    "ModelRequest": object,
    "ModelResponse": object,
    "ModelCallResult": object,
    "ToolCallRequest": object,
    "Any": __import__("typing").Any,
    "Callable": Callable,
    "Awaitable": Awaitable,
}
exec(compile(middleware_code, "middleware.py", "exec"), middleware_ns)
SteeringMiddleware = middleware_ns["SteeringMiddleware"]


@pytest.fixture(autouse=True)
def reset_manager():
    """Reset global manager before each test"""
    reset_queue_manager()
    yield
    reset_queue_manager()


class TestQueueMode:
    def test_enum_values(self):
        assert QueueMode.STEER.value == "steer"
        assert QueueMode.FOLLOWUP.value == "followup"
        assert QueueMode.COLLECT.value == "collect"
        assert QueueMode.STEER_BACKLOG.value == "steer_backlog"
        assert QueueMode.INTERRUPT.value == "interrupt"


class TestQueueMessage:
    def test_creation(self):
        msg = QueueMessage(content="test", mode=QueueMode.STEER)
        assert msg.content == "test"
        assert msg.mode == QueueMode.STEER
        assert msg.timestamp > 0

    def test_timestamp_auto(self):
        t1 = time.time()
        msg = QueueMessage(content="test", mode=QueueMode.STEER)
        t2 = time.time()
        assert t1 <= msg.timestamp <= t2


class TestMessageQueueManager:
    def test_singleton(self):
        mgr1 = get_queue_manager()
        mgr2 = get_queue_manager()
        assert mgr1 is mgr2

    def test_steer_enqueue_dequeue(self):
        mgr = get_queue_manager()
        mgr.enqueue("message1", QueueMode.STEER)
        mgr.enqueue("message2", QueueMode.STEER)

        assert mgr.has_steer()
        assert mgr.get_steer() == "message1"
        assert mgr.get_steer() == "message2"
        assert mgr.get_steer() is None
        assert not mgr.has_steer()

    def test_followup_enqueue_dequeue(self):
        mgr = get_queue_manager()
        mgr.enqueue("followup1", QueueMode.FOLLOWUP)
        mgr.enqueue("followup2", QueueMode.FOLLOWUP)

        assert mgr.has_followup()
        assert mgr.get_followup() == "followup1"
        assert mgr.get_followup() == "followup2"
        assert mgr.get_followup() is None
        assert not mgr.has_followup()

    def test_steer_backlog_both_queues(self):
        mgr = get_queue_manager()
        mgr.enqueue("both", QueueMode.STEER_BACKLOG)

        assert mgr.has_steer()
        assert mgr.has_followup()
        assert mgr.get_steer() == "both"
        assert mgr.get_followup() == "both"

    def test_collect_and_flush(self):
        mgr = get_queue_manager()
        mgr.enqueue("part1", QueueMode.COLLECT)
        mgr.enqueue("part2", QueueMode.COLLECT)
        mgr.enqueue("part3", QueueMode.COLLECT)

        merged = mgr.flush_collect()
        assert merged == "part1\n\npart2\n\npart3"
        assert mgr.flush_collect() is None

    def test_mode_setting(self):
        mgr = get_queue_manager()
        assert mgr.get_mode() == QueueMode.STEER  # default

        mgr.set_mode(QueueMode.STEER)
        assert mgr.get_mode() == QueueMode.STEER

    def test_enqueue_uses_current_mode(self):
        mgr = get_queue_manager()
        mgr.set_mode(QueueMode.STEER)
        mgr.enqueue("auto-steer")  # no mode specified

        assert mgr.has_steer()
        assert mgr.get_steer() == "auto-steer"

    def test_clear_all(self):
        mgr = get_queue_manager()
        mgr.enqueue("s", QueueMode.STEER)
        mgr.enqueue("f", QueueMode.FOLLOWUP)
        mgr.enqueue("c", QueueMode.COLLECT)

        mgr.clear_all()

        assert not mgr.has_steer()
        assert not mgr.has_followup()
        assert mgr.flush_collect() is None

    def test_queue_sizes(self):
        mgr = get_queue_manager()
        mgr.enqueue("s1", QueueMode.STEER)
        mgr.enqueue("s2", QueueMode.STEER)
        mgr.enqueue("f1", QueueMode.FOLLOWUP)
        mgr.enqueue("c1", QueueMode.COLLECT)

        sizes = mgr.queue_sizes()
        assert sizes["steer"] == 2
        assert sizes["followup"] == 1
        assert sizes["collect"] == 1

    def test_thread_safety(self):
        """Test concurrent access from multiple threads"""
        mgr = get_queue_manager()
        results = []
        errors = []

        def producer():
            try:
                for i in range(100):
                    mgr.enqueue(f"msg-{i}", QueueMode.STEER)
            except Exception as e:
                errors.append(e)

        def consumer():
            try:
                count = 0
                for _ in range(200):
                    msg = mgr.get_steer()
                    if msg:
                        count += 1
                    time.sleep(0.001)
                results.append(count)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=producer),
            threading.Thread(target=producer),
            threading.Thread(target=consumer),
            threading.Thread(target=consumer),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        # All 200 messages should be consumed
        assert sum(results) == 200


class TestSteeringMiddleware:
    def test_tool_call_no_steer(self):
        """When no steer message, tool call executes normally"""
        middleware = SteeringMiddleware()

        class MockToolCall:
            def get(self, key, default=""):
                return {"id": "tool-1", "name": "test_tool"}.get(key, default)

        class MockRequest:
            def __init__(self):
                self.tool_call = MockToolCall()

        request = MockRequest()
        expected_result = MockHumanMessage("tool result")

        def mock_handler(req):
            return expected_result

        result = middleware.wrap_tool_call(request, mock_handler)
        assert result == expected_result

    def test_tool_call_skipped_when_steer_pending(self):
        """When steer is pending, subsequent tool calls are skipped"""
        middleware = SteeringMiddleware()
        mgr = get_queue_manager()

        class MockToolCall:
            def get(self, key, default=""):
                return {"id": "tool-1", "name": "test_tool"}.get(key, default)

        class MockRequest:
            def __init__(self):
                self.tool_call = MockToolCall()

        request = MockRequest()

        # First tool call - executes and checks queue
        def mock_handler(req):
            return MockHumanMessage("first result")

        result1 = middleware.wrap_tool_call(request, mock_handler)
        assert result1.content == "first result"

        # Now enqueue a steer message
        mgr.enqueue("change direction!", QueueMode.STEER)

        # Second tool call - executes, then finds steer message
        result2 = middleware.wrap_tool_call(request, mock_handler)
        assert result2.content == "first result"  # Still executes

        # Third tool call - should be skipped because steer is pending
        result3 = middleware.wrap_tool_call(request, mock_handler)
        assert "Skipped" in result3.content

    def test_before_model_injects_steer(self):
        """before_model injects pending steer message"""
        middleware = SteeringMiddleware()
        mgr = get_queue_manager()

        # Simulate: tool call found steer message
        mgr.enqueue("change direction!", QueueMode.STEER)

        class MockToolCall:
            def get(self, key, default=""):
                return {"id": "tool-1"}.get(key, default)

        class MockRequest:
            def __init__(self):
                self.tool_call = MockToolCall()

        # Tool call picks up the steer
        middleware.wrap_tool_call(MockRequest(), lambda r: MockHumanMessage("result"))

        # Now before_model should inject it
        state_update = middleware.before_model({}, None)

        assert state_update is not None
        assert "messages" in state_update
        assert len(state_update["messages"]) == 1
        assert "[STEER]" in state_update["messages"][0].content
        assert "change direction!" in state_update["messages"][0].content

        # Second call should return None (steer consumed)
        assert middleware.before_model({}, None) is None
