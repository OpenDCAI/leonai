"""Tests for SSE reconnection + persistent event log.

Covers:
- EventStore: CRUD operations on run_events table
- serialize_message: msg.id inclusion
- emit() / observe_run_events: message_id injection + after-based filtering
- mapBackendEntries ID stability (via backend serialization)
"""

import json
import sqlite3
import threading
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# EventStore tests (pure SQLite, no server needed)
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_db(tmp_path):
    """Patch EventStore to use a temp DB file."""
    db_path = tmp_path / "test_leon.db"
    with patch("backend.web.services.event_store._DB_PATH", db_path):
        # Reset thread-local connection so it picks up the new path
        import backend.web.services.event_store as es

        es._local = threading.local()
        es.init_event_store()
        yield db_path


class TestEventStore:
    """EventStore CRUD operations."""

    def test_init_creates_table(self, tmp_db):
        conn = sqlite3.connect(str(tmp_db))
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='run_events'").fetchall()
        assert len(tables) == 1

    def test_append_and_read(self, tmp_db):
        from backend.web.services.event_store import append_event, read_events_after

        seq1 = append_event("t1", "r1", {"event": "text", "data": '{"content":"hello"}'}, "msg-1")
        seq2 = append_event("t1", "r1", {"event": "tool_call", "data": '{"id":"tc1"}'}, "msg-1")

        assert seq1 < seq2

        events = read_events_after("t1", "r1", 0)
        assert len(events) == 2
        assert events[0]["event"] == "text"
        assert events[0]["message_id"] == "msg-1"
        assert events[1]["event"] == "tool_call"

    def test_read_after_filters(self, tmp_db):
        from backend.web.services.event_store import append_event, read_events_after

        seq1 = append_event("t1", "r1", {"event": "text", "data": "{}"})
        seq2 = append_event("t1", "r1", {"event": "done", "data": "{}"})

        events = read_events_after("t1", "r1", seq1)
        assert len(events) == 1
        assert events[0]["seq"] == seq2

    def test_get_latest_run_id(self, tmp_db):
        from backend.web.services.event_store import append_event, get_latest_run_id

        assert get_latest_run_id("t1") is None

        append_event("t1", "run-a", {"event": "text", "data": "{}"})
        append_event("t1", "run-b", {"event": "text", "data": "{}"})

        assert get_latest_run_id("t1") == "run-b"

    def test_cleanup_old_runs(self, tmp_db):
        from backend.web.services.event_store import (
            append_event,
            cleanup_old_runs,
            read_events_after,
        )

        # Create 3 runs
        for run in ["r1", "r2", "r3"]:
            append_event("t1", run, {"event": "text", "data": "{}"})
            append_event("t1", run, {"event": "done", "data": ""})

        deleted = cleanup_old_runs("t1", keep_latest=1)
        assert deleted == 4  # r1(2) + r2(2)

        remaining = read_events_after("t1", "r3", 0)
        assert len(remaining) == 2

        # r1 and r2 should be gone
        assert read_events_after("t1", "r1", 0) == []
        assert read_events_after("t1", "r2", 0) == []

    def test_cleanup_thread(self, tmp_db):
        from backend.web.services.event_store import (
            append_event,
            cleanup_thread,
            read_events_after,
        )

        append_event("t1", "r1", {"event": "text", "data": "{}"})
        append_event("t2", "r1", {"event": "text", "data": "{}"})

        deleted = cleanup_thread("t1")
        assert deleted == 1
        assert read_events_after("t1", "r1", 0) == []
        assert len(read_events_after("t2", "r1", 0)) == 1

    def test_cross_thread_isolation(self, tmp_db):
        from backend.web.services.event_store import append_event, read_events_after

        append_event("t1", "r1", {"event": "text", "data": '{"content":"t1"}'})
        append_event("t2", "r1", {"event": "text", "data": '{"content":"t2"}'})

        t1_events = read_events_after("t1", "r1", 0)
        t2_events = read_events_after("t2", "r1", 0)
        assert len(t1_events) == 1
        assert len(t2_events) == 1


# ---------------------------------------------------------------------------
# serialize_message tests
# ---------------------------------------------------------------------------


class TestSerializeMessage:
    """serialize_message includes msg.id."""

    def test_includes_id(self):
        from backend.web.utils.serializers import serialize_message

        class AIMessage:
            id = "msg-uuid-123"
            content = "hello"
            tool_calls = []
            tool_call_id = None

        result = serialize_message(AIMessage())
        assert result["id"] == "msg-uuid-123"
        assert result["type"] == "AIMessage"
        assert result["content"] == "hello"

    def test_missing_id_returns_none(self):
        from backend.web.utils.serializers import serialize_message

        class HumanMessage:
            content = "hi"
            tool_calls = []
            tool_call_id = None

        result = serialize_message(HumanMessage())
        assert result["id"] is None


# ---------------------------------------------------------------------------
# RunEventBuffer + observe_run_events tests
# ---------------------------------------------------------------------------


class TestObserveRunEvents:
    """observe_run_events with after-based filtering."""

    def test_observe_yields_all_events(self):
        import asyncio

        async def _run():
            from backend.web.services.event_buffer import RunEventBuffer
            from backend.web.services.streaming_service import observe_run_events

            buf = RunEventBuffer()
            await buf.put({"event": "text", "data": json.dumps({"content": "hi", "_seq": 1})})
            await buf.put({"event": "done", "data": json.dumps({"thread_id": "t1", "_seq": 2})})
            await buf.mark_done()

            events = []
            async for ev in observe_run_events(buf):
                events.append(ev)
            assert len(events) == 2

        asyncio.run(_run())

    def test_observe_after_skips_old_events(self):
        import asyncio

        async def _run():
            from backend.web.services.event_buffer import RunEventBuffer
            from backend.web.services.streaming_service import observe_run_events

            buf = RunEventBuffer()
            await buf.put({"event": "text", "data": json.dumps({"content": "old", "_seq": 5})})
            await buf.put({"event": "text", "data": json.dumps({"content": "new", "_seq": 10})})
            await buf.put({"event": "done", "data": json.dumps({"thread_id": "t1", "_seq": 11})})
            await buf.mark_done()

            events = []
            async for ev in observe_run_events(buf, after=5):
                events.append(ev)
            assert len(events) == 2
            assert json.loads(events[0]["data"])["content"] == "new"

        asyncio.run(_run())

    def test_buffer_run_id_field(self):
        from backend.web.services.event_buffer import RunEventBuffer

        buf = RunEventBuffer()
        assert buf.run_id == ""
        buf.run_id = "test-run-123"
        assert buf.run_id == "test-run-123"
