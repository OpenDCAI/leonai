"""E2E tests for RemoteSessionStore/RemoteMessageQueue → Docker SQLite service.

Requires the SQLite service running at localhost:8100:
    docker compose -f services/sqlite-service/docker-compose.yml up -d
"""

import pytest

from sandbox.provider import SessionInfo
from sandbox.remote_store import RemoteMessageQueue, RemoteSessionStore

SERVICE_URL = "http://localhost:8100"


def _service_available():
    try:
        import httpx
        r = httpx.get(f"{SERVICE_URL}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _service_available(),
    reason="SQLite service not running at localhost:8100",
)


@pytest.fixture
def store():
    s = RemoteSessionStore(SERVICE_URL)
    yield s
    s.close()


@pytest.fixture
def queue():
    q = RemoteMessageQueue(SERVICE_URL)
    yield q
    q.close()


class TestRemoteSessionStore:
    def test_save_get_delete(self, store):
        tid = "e2e-test-session-1"
        info = SessionInfo(session_id="s-e2e-1", provider="docker", status="running")
        store.save(tid, info, context_id="ctx-1")

        row = store.get(tid)
        assert row is not None
        assert row["session_id"] == "s-e2e-1"
        assert row["provider"] == "docker"

        store.delete(tid)
        assert store.get(tid) is None

    def test_get_missing(self, store):
        assert store.get("nonexistent-thread-xyz") is None

    def test_update_status(self, store):
        tid = "e2e-test-session-2"
        info = SessionInfo(session_id="s-e2e-2", provider="e2b", status="running")
        store.save(tid, info, context_id=None)

        store.update_status(tid, "paused")
        row = store.get(tid)
        assert row["status"] == "paused"

        store.delete(tid)

    def test_touch(self, store):
        tid = "e2e-test-session-3"
        info = SessionInfo(session_id="s-e2e-3", provider="docker", status="running")
        store.save(tid, info, context_id=None)

        old = store.get(tid)["last_active"]
        store.touch(tid)
        new = store.get(tid)["last_active"]
        assert new >= old

        store.delete(tid)


class TestRemoteMessageQueue:
    def test_enqueue_claim_complete(self, queue):
        msg_id = queue.enqueue("e2e.test", {"action": "pause"})
        assert msg_id

        msg = queue.claim("e2e.test")
        assert msg is not None
        assert msg.id == msg_id
        assert msg.payload == {"action": "pause"}
        assert msg.status == "claimed"

        queue.complete(msg.id)
        assert queue.claim("e2e.test") is None

    def test_claim_empty(self, queue):
        assert queue.claim("e2e.empty.queue") is None

    def test_fail(self, queue):
        msg_id = queue.enqueue("e2e.fail", {"x": 1})
        msg = queue.claim("e2e.fail")
        queue.fail(msg.id, error="test error")
        assert queue.claim("e2e.fail") is None

    def test_peek(self, queue):
        q = "e2e.peek"
        queue.enqueue(q, {"a": 1})
        queue.enqueue(q, {"b": 2})
        msgs = queue.peek(q)
        assert len(msgs) >= 2
        # Peek doesn't consume
        msgs2 = queue.peek(q)
        assert len(msgs2) >= 2
        # Clean up
        while msg := queue.claim(q):
            queue.complete(msg.id)
