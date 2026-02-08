"""Tests for MessageQueue ABC and SQLiteMessageQueue."""

import pytest

from sandbox.sqlite_queue import SQLiteMessageQueue


@pytest.fixture
def queue(tmp_path):
    q = SQLiteMessageQueue(db_path=tmp_path / "test.db")
    yield q
    q.close()


class TestSQLiteMessageQueue:
    def test_enqueue_and_claim(self, queue):
        msg_id = queue.enqueue("test", {"action": "pause", "session_id": "s1"})
        assert msg_id

        msg = queue.claim("test")
        assert msg is not None
        assert msg.id == msg_id
        assert msg.queue == "test"
        assert msg.payload == {"action": "pause", "session_id": "s1"}
        assert msg.status == "claimed"

    def test_claim_empty(self, queue):
        assert queue.claim("test") is None

    def test_claim_fifo(self, queue):
        queue.enqueue("q", {"order": 1})
        queue.enqueue("q", {"order": 2})
        queue.enqueue("q", {"order": 3})

        msg1 = queue.claim("q")
        msg2 = queue.claim("q")
        msg3 = queue.claim("q")
        assert msg1.payload["order"] == 1
        assert msg2.payload["order"] == 2
        assert msg3.payload["order"] == 3

    def test_claim_no_double(self, queue):
        queue.enqueue("q", {"x": 1})
        msg = queue.claim("q")
        assert msg is not None
        # Second claim should return None (already claimed)
        assert queue.claim("q") is None

    def test_complete(self, queue):
        msg_id = queue.enqueue("q", {"x": 1})
        msg = queue.claim("q")
        queue.complete(msg.id)
        # Completed messages are not claimable
        assert queue.claim("q") is None

    def test_fail(self, queue):
        msg_id = queue.enqueue("q", {"x": 1})
        msg = queue.claim("q")
        queue.fail(msg.id, error="timeout")
        # Failed messages are not claimable
        assert queue.claim("q") is None

    def test_peek(self, queue):
        queue.enqueue("q", {"a": 1})
        queue.enqueue("q", {"b": 2})
        msgs = queue.peek("q")
        assert len(msgs) == 2
        assert msgs[0].payload == {"a": 1}
        assert msgs[1].payload == {"b": 2}
        # Peek doesn't consume
        assert len(queue.peek("q")) == 2

    def test_peek_limit(self, queue):
        for i in range(5):
            queue.enqueue("q", {"i": i})
        msgs = queue.peek("q", limit=2)
        assert len(msgs) == 2

    def test_queue_isolation(self, queue):
        queue.enqueue("q1", {"from": "q1"})
        queue.enqueue("q2", {"from": "q2"})
        msg = queue.claim("q1")
        assert msg.payload["from"] == "q1"
        msg = queue.claim("q2")
        assert msg.payload["from"] == "q2"
        assert queue.claim("q1") is None

    def test_close_idempotent(self, queue):
        queue.close()
        queue.close()
