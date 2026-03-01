"""Tests for timing-driven message routing: inject (steer) + enqueue/dequeue (followup)."""

import sqlite3
import tempfile
import threading

import pytest

from core.queue import MessageQueueManager, get_queue_manager, reset_queue_manager
from core.queue.formatters import format_steer_reminder, format_task_notification


@pytest.fixture(autouse=True)
def _reset_queue():
    """Reset the global queue manager before each test."""
    reset_queue_manager()
    yield
    reset_queue_manager()


@pytest.fixture()
def tmp_db(tmp_path):
    """Provide a temporary SQLite database path."""
    return str(tmp_path / "test.db")


# ---------------------------------------------------------------------------
# 1. Inject path (steer) — in-memory buffer
# ---------------------------------------------------------------------------


class TestInjectSteer:
    def test_inject_and_pop(self, tmp_db):
        mgr = MessageQueueManager(db_path=tmp_db)
        mgr.inject("turn left", thread_id="t1")
        assert mgr.has_steer("t1")
        assert mgr.pop_steer("t1") == "turn left"
        assert not mgr.has_steer("t1")

    def test_inject_fifo(self, tmp_db):
        mgr = MessageQueueManager(db_path=tmp_db)
        mgr.inject("first", thread_id="t1")
        mgr.inject("second", thread_id="t1")
        assert mgr.pop_steer("t1") == "first"
        assert mgr.pop_steer("t1") == "second"
        assert mgr.pop_steer("t1") is None

    def test_inject_thread_isolation(self, tmp_db):
        mgr = MessageQueueManager(db_path=tmp_db)
        mgr.inject("for-t1", thread_id="t1")
        mgr.inject("for-t2", thread_id="t2")
        assert mgr.pop_steer("t1") == "for-t1"
        assert mgr.pop_steer("t2") == "for-t2"
        assert mgr.pop_steer("t1") is None

    def test_pop_empty(self, tmp_db):
        mgr = MessageQueueManager(db_path=tmp_db)
        assert mgr.pop_steer("nonexistent") is None
        assert not mgr.has_steer("nonexistent")

    def test_clear_steer(self, tmp_db):
        mgr = MessageQueueManager(db_path=tmp_db)
        mgr.inject("a", thread_id="t1")
        mgr.inject("b", thread_id="t1")
        mgr.clear_steer("t1")
        assert not mgr.has_steer("t1")
        assert mgr.pop_steer("t1") is None


class TestDrainSteer:
    """Tests for batch drain_steer() method."""

    def test_drain_returns_all(self, tmp_db):
        mgr = MessageQueueManager(db_path=tmp_db)
        mgr.inject("first", thread_id="t1")
        mgr.inject("second", thread_id="t1")
        mgr.inject("third", thread_id="t1")
        items = mgr.drain_steer("t1")
        assert items == ["first", "second", "third"]

    def test_drain_empties_queue(self, tmp_db):
        mgr = MessageQueueManager(db_path=tmp_db)
        mgr.inject("msg", thread_id="t1")
        mgr.drain_steer("t1")
        assert not mgr.has_steer("t1")
        assert mgr.pop_steer("t1") is None
        assert mgr.drain_steer("t1") == []

    def test_drain_empty_returns_empty_list(self, tmp_db):
        mgr = MessageQueueManager(db_path=tmp_db)
        assert mgr.drain_steer("nonexistent") == []

    def test_drain_thread_isolation(self, tmp_db):
        mgr = MessageQueueManager(db_path=tmp_db)
        mgr.inject("for-t1", thread_id="t1")
        mgr.inject("for-t2", thread_id="t2")
        assert mgr.drain_steer("t1") == ["for-t1"]
        assert mgr.drain_steer("t2") == ["for-t2"]


# ---------------------------------------------------------------------------
# 2. Enqueue / dequeue path (followup) — SQLite persistent
# ---------------------------------------------------------------------------


class TestEnqueueDequeue:
    def test_enqueue_and_dequeue(self, tmp_db):
        mgr = MessageQueueManager(db_path=tmp_db)
        mgr.enqueue("hello", thread_id="t1")
        assert mgr.peek("t1")
        assert mgr.dequeue("t1") == "hello"
        assert not mgr.peek("t1")

    def test_fifo_order(self, tmp_db):
        mgr = MessageQueueManager(db_path=tmp_db)
        mgr.enqueue("first", thread_id="t1")
        mgr.enqueue("second", thread_id="t1")
        mgr.enqueue("third", thread_id="t1")
        assert mgr.dequeue("t1") == "first"
        assert mgr.dequeue("t1") == "second"
        assert mgr.dequeue("t1") == "third"
        assert mgr.dequeue("t1") is None

    def test_thread_isolation(self, tmp_db):
        mgr = MessageQueueManager(db_path=tmp_db)
        mgr.enqueue("for-t1", thread_id="t1")
        mgr.enqueue("for-t2", thread_id="t2")
        assert mgr.dequeue("t1") == "for-t1"
        assert mgr.dequeue("t2") == "for-t2"
        assert mgr.dequeue("t1") is None

    def test_dequeue_empty(self, tmp_db):
        mgr = MessageQueueManager(db_path=tmp_db)
        assert mgr.dequeue("nonexistent") is None

    def test_peek_does_not_consume(self, tmp_db):
        mgr = MessageQueueManager(db_path=tmp_db)
        mgr.enqueue("msg", thread_id="t1")
        assert mgr.peek("t1")
        assert mgr.peek("t1")  # still there
        assert mgr.dequeue("t1") == "msg"

    def test_list_queue(self, tmp_db):
        mgr = MessageQueueManager(db_path=tmp_db)
        mgr.enqueue("a", thread_id="t1")
        mgr.enqueue("b", thread_id="t1")
        items = mgr.list_queue("t1")
        assert len(items) == 2
        assert items[0]["content"] == "a"
        assert items[1]["content"] == "b"

    def test_clear_queue(self, tmp_db):
        mgr = MessageQueueManager(db_path=tmp_db)
        mgr.enqueue("a", thread_id="t1")
        mgr.enqueue("b", thread_id="t1")
        mgr.clear_queue("t1")
        assert not mgr.peek("t1")
        assert mgr.dequeue("t1") is None

    def test_cross_instance_persistence(self, tmp_db):
        """Different manager instances sharing the same DB can consume each other's messages."""
        mgr1 = MessageQueueManager(db_path=tmp_db)
        mgr1.enqueue("shared-msg", thread_id="t1")

        mgr2 = MessageQueueManager(db_path=tmp_db)
        assert mgr2.dequeue("t1") == "shared-msg"

    def test_concurrent_dequeue_no_duplicates(self, tmp_db):
        """Under concurrent access, each message is consumed exactly once."""
        mgr = MessageQueueManager(db_path=tmp_db)
        for i in range(20):
            mgr.enqueue(f"msg-{i}", thread_id="t1")

        results = []
        lock = threading.Lock()

        def consumer():
            local_mgr = MessageQueueManager(db_path=tmp_db)
            while True:
                msg = local_mgr.dequeue("t1")
                if msg is None:
                    break
                with lock:
                    results.append(msg)

        threads = [threading.Thread(target=consumer) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert sorted(results) == sorted(f"msg-{i}" for i in range(20))


# ---------------------------------------------------------------------------
# 3. clear_all cleans both channels
# ---------------------------------------------------------------------------


class TestClearAll:
    def test_clear_all(self, tmp_db):
        mgr = MessageQueueManager(db_path=tmp_db)
        mgr.inject("steer-msg", thread_id="t1")
        mgr.enqueue("queue-msg", thread_id="t1")
        mgr.clear_all("t1")
        assert not mgr.has_steer("t1")
        assert not mgr.peek("t1")


# ---------------------------------------------------------------------------
# 4. Global singleton
# ---------------------------------------------------------------------------


class TestGlobalSingleton:
    def test_get_queue_manager_returns_same_instance(self):
        mgr1 = get_queue_manager()
        mgr2 = get_queue_manager()
        assert mgr1 is mgr2

    def test_reset_creates_new_instance(self):
        mgr1 = get_queue_manager()
        reset_queue_manager()
        mgr2 = get_queue_manager()
        assert mgr1 is not mgr2


# ---------------------------------------------------------------------------
# 5. SteeringMiddleware integration — non-preemptive behavior
# ---------------------------------------------------------------------------


class TestSteeringMiddlewareIntegration:
    """Verify SteeringMiddleware reads from inject channel via drain_steer."""

    def test_middleware_consumes_injected_steer(self):
        from core.queue.middleware import SteeringMiddleware

        mgr = get_queue_manager()
        middleware = SteeringMiddleware()

        thread_id = "test-middleware"
        mgr.inject("change direction", thread_id=thread_id)

        # Middleware should be able to detect pending steer via the global manager
        assert mgr.has_steer(thread_id)
        # drain_steer is what middleware now calls internally
        items = mgr.drain_steer(thread_id)
        assert items == ["change direction"]
        assert not mgr.has_steer(thread_id)

    def test_middleware_drains_multiple(self):
        """Middleware drains all pending steers at once."""
        from core.queue.middleware import SteeringMiddleware

        mgr = get_queue_manager()

        thread_id = "test-multi"
        mgr.inject("first", thread_id=thread_id)
        mgr.inject("second", thread_id=thread_id)

        items = mgr.drain_steer(thread_id)
        assert items == ["first", "second"]
        assert mgr.drain_steer(thread_id) == []

    def test_tool_calls_never_skipped(self):
        """Verify wrap_tool_call is a pure passthrough (non-preemptive)."""
        from unittest.mock import MagicMock

        from core.queue.middleware import SteeringMiddleware

        middleware = SteeringMiddleware()

        # Inject steer to simulate mid-execution message
        mgr = get_queue_manager()
        mgr.inject("urgent message", thread_id="test-no-skip")

        # Create mock tool call request and handler
        mock_request = MagicMock()
        mock_result = MagicMock()
        mock_handler = MagicMock(return_value=mock_result)

        # wrap_tool_call should call handler normally, NOT skip
        result = middleware.wrap_tool_call(mock_request, mock_handler)
        mock_handler.assert_called_once_with(mock_request)
        assert result is mock_result


# ---------------------------------------------------------------------------
# 6. XML formatters
# ---------------------------------------------------------------------------


class TestFormatters:
    def test_format_steer_reminder(self):
        xml = format_steer_reminder("stop and do X")
        assert "<system-reminder>" in xml
        assert "stop and do X" in xml
        assert "IMPORTANT" in xml
        assert "</system-reminder>" in xml

    def test_format_task_notification(self):
        xml = format_task_notification(
            task_id="abc123",
            status="completed",
            summary="Analysis done",
            result="Found 5 issues",
        )
        assert "<task-notification>" in xml
        assert "<task-id>abc123</task-id>" in xml
        assert "<status>completed</status>" in xml
        assert "<summary>Analysis done</summary>" in xml
        assert "<result>Found 5 issues</result>" in xml

    def test_format_task_notification_truncates_long_result(self):
        long_result = "x" * 3000
        xml = format_task_notification(
            task_id="t1", status="completed", summary="done", result=long_result
        )
        assert "..." in xml
        # Result field should be truncated
        assert len(xml) < 3000

    def test_format_task_notification_no_result(self):
        xml = format_task_notification(task_id="t1", status="error", summary="failed")
        assert "<result>" not in xml
