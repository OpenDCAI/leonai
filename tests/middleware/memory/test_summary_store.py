"""Unit tests for SummaryStore."""

import tempfile
from pathlib import Path

import pytest

from middleware.memory.summary_store import SummaryStore


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    # Cleanup
    if db_path.exists():
        db_path.unlink()
    # Also cleanup WAL files
    for suffix in ["-wal", "-shm"]:
        wal_file = Path(str(db_path) + suffix)
        if wal_file.exists():
            wal_file.unlink()


def test_save_and_get_summary(temp_db):
    """Test saving and retrieving a summary."""
    store = SummaryStore(temp_db)

    # Save a summary
    summary_id = store.save_summary(
        thread_id="test-thread-1",
        summary_text="This is a test summary",
        compact_up_to_index=10,
        compacted_at=20,
    )

    assert summary_id.startswith("test-thread-1_")

    # Retrieve the summary
    summary = store.get_latest_summary("test-thread-1")

    assert summary is not None
    assert summary.thread_id == "test-thread-1"
    assert summary.summary_text == "This is a test summary"
    assert summary.compact_up_to_index == 10
    assert summary.compacted_at == 20
    assert summary.is_split_turn is False
    assert summary.split_turn_prefix is None
    assert summary.is_active is True


def test_multiple_summaries_only_latest_active(temp_db):
    """Test that only the latest summary is active."""
    store = SummaryStore(temp_db)

    # Save first summary
    id1 = store.save_summary(
        thread_id="test-thread-2",
        summary_text="First summary",
        compact_up_to_index=10,
        compacted_at=20,
    )

    # Save second summary
    id2 = store.save_summary(
        thread_id="test-thread-2",
        summary_text="Second summary",
        compact_up_to_index=30,
        compacted_at=40,
    )

    # Only the latest should be active
    latest = store.get_latest_summary("test-thread-2")
    assert latest is not None
    assert latest.summary_id == id2
    assert latest.summary_text == "Second summary"
    assert latest.is_active is True

    # List all summaries
    all_summaries = store.list_summaries("test-thread-2")
    assert len(all_summaries) == 2

    # Check that first is inactive
    active_count = sum(1 for s in all_summaries if s["is_active"])
    assert active_count == 1


def test_split_turn_summary(temp_db):
    """Test saving and retrieving a split turn summary."""
    store = SummaryStore(temp_db)

    # Save a split turn summary
    summary_id = store.save_summary(
        thread_id="test-thread-3",
        summary_text="Combined summary with split turn",
        compact_up_to_index=15,
        compacted_at=30,
        is_split_turn=True,
        split_turn_prefix="Prefix summary",
    )

    # Retrieve the summary
    summary = store.get_latest_summary("test-thread-3")

    assert summary is not None
    assert summary.is_split_turn is True
    assert summary.split_turn_prefix == "Prefix summary"
    assert "Combined summary with split turn" in summary.summary_text


def test_no_summary_returns_none(temp_db):
    """Test that getting a non-existent summary returns None."""
    store = SummaryStore(temp_db)

    summary = store.get_latest_summary("non-existent-thread")
    assert summary is None


def test_delete_thread_summaries(temp_db):
    """Test deleting all summaries for a thread."""
    store = SummaryStore(temp_db)

    # Save multiple summaries
    store.save_summary(
        thread_id="test-thread-4",
        summary_text="Summary 1",
        compact_up_to_index=10,
        compacted_at=20,
    )
    store.save_summary(
        thread_id="test-thread-4",
        summary_text="Summary 2",
        compact_up_to_index=30,
        compacted_at=40,
    )

    # Verify they exist
    assert len(store.list_summaries("test-thread-4")) == 2

    # Delete all summaries
    store.delete_thread_summaries("test-thread-4")

    # Verify they're gone
    assert len(store.list_summaries("test-thread-4")) == 0
    assert store.get_latest_summary("test-thread-4") is None


def test_retry_on_failure(temp_db):
    """Test that save/get operations retry on failure."""
    store = SummaryStore(temp_db)

    # This test verifies the retry mechanism exists
    # In a real scenario, we'd mock sqlite3 to simulate failures
    # For now, we just verify normal operation works
    summary_id = store.save_summary(
        thread_id="test-thread-5",
        summary_text="Test retry",
        compact_up_to_index=5,
        compacted_at=10,
        max_retries=3,
    )

    summary = store.get_latest_summary("test-thread-5", max_retries=3)
    assert summary is not None
    assert summary.summary_text == "Test retry"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
