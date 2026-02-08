"""Unit tests for SandboxLease and LeaseStore."""

import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sandbox.lease import (
    LeaseStore,
    SandboxInstance,
    SandboxLease,
    SQLiteLease,
)
from sandbox.provider import SessionInfo


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    db_path.unlink(missing_ok=True)


@pytest.fixture
def store(temp_db):
    """Create LeaseStore with temp database."""
    return LeaseStore(db_path=temp_db)


@pytest.fixture
def mock_provider():
    """Create mock SandboxProvider."""
    provider = MagicMock()
    provider.name = "test-provider"
    return provider


class TestSandboxInstance:
    """Test SandboxInstance dataclass."""

    def test_create_instance(self):
        """Test creating SandboxInstance."""
        now = datetime.now()
        instance = SandboxInstance(
            instance_id="inst-123",
            provider_name="e2b",
            status="running",
            created_at=now,
        )

        assert instance.instance_id == "inst-123"
        assert instance.provider_name == "e2b"
        assert instance.status == "running"
        assert instance.created_at == now


class TestLeaseStore:
    """Test LeaseStore CRUD operations."""

    def test_ensure_tables(self, temp_db):
        """Test table creation."""
        store = LeaseStore(db_path=temp_db)

        # Verify table exists
        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sandbox_leases'"
            )
            assert cursor.fetchone() is not None

    def test_create_lease(self, store):
        """Test creating a new lease."""
        lease = store.create(lease_id="lease-123", provider_name="e2b")

        assert lease.lease_id == "lease-123"
        assert lease.provider_name == "e2b"
        assert lease.get_instance() is None

    def test_get_lease(self, store):
        """Test retrieving lease by lease_id."""
        store.create(lease_id="lease-123", provider_name="e2b")

        lease = store.get("lease-123")
        assert lease is not None
        assert lease.lease_id == "lease-123"
        assert lease.provider_name == "e2b"

    def test_get_nonexistent_lease(self, store):
        """Test retrieving non-existent lease returns None."""
        lease = store.get("nonexistent-lease")
        assert lease is None

    def test_delete_lease(self, store):
        """Test deleting a lease."""
        store.create(lease_id="lease-123", provider_name="e2b")

        # Verify exists
        assert store.get("lease-123") is not None

        # Delete
        store.delete("lease-123")

        # Verify deleted
        assert store.get("lease-123") is None

    def test_list_all_leases(self, store):
        """Test listing all leases."""
        import time

        store.create("lease-1", "e2b")
        time.sleep(0.01)
        store.create("lease-2", "agentbay")
        time.sleep(0.01)
        store.create("lease-3", "e2b")

        leases = store.list_all()
        assert len(leases) == 3

        # Should be ordered by created_at DESC
        assert leases[0]["lease_id"] == "lease-3"
        assert leases[1]["lease_id"] == "lease-2"
        assert leases[2]["lease_id"] == "lease-1"

    def test_list_by_provider(self, store):
        """Test listing leases by provider."""
        store.create("lease-1", "e2b")
        store.create("lease-2", "agentbay")
        store.create("lease-3", "e2b")

        e2b_leases = store.list_by_provider("e2b")
        assert len(e2b_leases) == 2
        assert all(l["provider_name"] == "e2b" for l in e2b_leases)

        agentbay_leases = store.list_by_provider("agentbay")
        assert len(agentbay_leases) == 1
        assert agentbay_leases[0]["provider_name"] == "agentbay"


class TestSQLiteLease:
    """Test SQLiteLease instance management."""

    def test_ensure_active_instance_creates_new(self, store, mock_provider):
        """Test ensure_active_instance creates new instance when none exists."""
        lease = store.create("lease-1", "test-provider")

        # Mock provider to return new session
        mock_provider.create_session.return_value = SessionInfo(
            session_id="inst-123",
            provider="test-provider",
            status="running",
        )

        instance = lease.ensure_active_instance(mock_provider)

        assert instance.instance_id == "inst-123"
        assert instance.status == "running"
        assert lease.get_instance() == instance
        mock_provider.create_session.assert_called_once()

    def test_ensure_active_instance_reuses_running(self, store, mock_provider):
        """Test ensure_active_instance reuses running instance."""
        lease = store.create("lease-1", "test-provider")

        # Create initial instance
        mock_provider.create_session.return_value = SessionInfo(
            session_id="inst-123",
            provider="test-provider",
            status="running",
        )
        instance1 = lease.ensure_active_instance(mock_provider)

        # Mock provider to report instance is still running
        mock_provider.get_session_status.return_value = "running"

        # Call again - should reuse
        instance2 = lease.ensure_active_instance(mock_provider)

        assert instance2.instance_id == instance1.instance_id
        assert mock_provider.create_session.call_count == 1  # Only called once

    def test_ensure_active_instance_converges_stale_paused_state(self, store, mock_provider):
        """If DB says paused but provider says running, lease status must converge to running."""
        lease = store.create("lease-1", "test-provider")

        mock_provider.create_session.return_value = SessionInfo(
            session_id="inst-123",
            provider="test-provider",
            status="running",
        )
        lease.ensure_active_instance(mock_provider)

        mock_provider.pause_session.return_value = True
        lease.pause_instance(mock_provider)
        assert lease.get_instance().status == "paused"

        mock_provider.get_session_status.return_value = "running"
        instance = lease.ensure_active_instance(mock_provider)
        assert instance.status == "running"

        reloaded = store.get("lease-1")
        assert reloaded is not None
        assert reloaded.get_instance() is not None
        assert reloaded.get_instance().status == "running"

    def test_ensure_active_instance_raises_when_paused(self, store, mock_provider):
        """Paused instance must be resumed explicitly, not auto-resumed."""
        lease = store.create("lease-1", "test-provider")

        # Create initial instance
        mock_provider.create_session.return_value = SessionInfo(
            session_id="inst-123",
            provider="test-provider",
            status="running",
        )
        lease.ensure_active_instance(mock_provider)

        # Mock provider to report instance is paused
        mock_provider.get_session_status.return_value = "paused"
        with pytest.raises(RuntimeError, match="is paused"):
            lease.ensure_active_instance(mock_provider)
        mock_provider.resume_session.assert_not_called()

    def test_ensure_active_instance_recreates_dead(self, store, mock_provider):
        """Test ensure_active_instance recreates dead instance."""
        lease = store.create("lease-1", "test-provider")

        # Create initial instance
        mock_provider.create_session.return_value = SessionInfo(
            session_id="inst-123",
            provider="test-provider",
            status="running",
        )
        lease.ensure_active_instance(mock_provider)

        # Mock provider to report instance is dead
        mock_provider.get_session_status.side_effect = Exception("Instance not found")
        mock_provider.create_session.return_value = SessionInfo(
            session_id="inst-456",
            provider="test-provider",
            status="running",
        )

        # Call again - should create new instance
        instance = lease.ensure_active_instance(mock_provider)

        assert instance.instance_id == "inst-456"
        assert mock_provider.create_session.call_count == 2

    def test_destroy_instance(self, store, mock_provider):
        """Test destroying instance."""
        lease = store.create("lease-1", "test-provider")

        # Create instance
        mock_provider.create_session.return_value = SessionInfo(
            session_id="inst-123",
            provider="test-provider",
            status="running",
        )
        lease.ensure_active_instance(mock_provider)

        # Destroy
        lease.destroy_instance(mock_provider)

        assert lease.get_instance() is None
        mock_provider.destroy_session.assert_called_once_with("inst-123")

    def test_pause_instance(self, store, mock_provider):
        """Test pausing instance."""
        lease = store.create("lease-1", "test-provider")

        # Create instance
        mock_provider.create_session.return_value = SessionInfo(
            session_id="inst-123",
            provider="test-provider",
            status="running",
        )
        lease.ensure_active_instance(mock_provider)

        # Pause
        mock_provider.pause_session.return_value = True
        result = lease.pause_instance(mock_provider)

        assert result is True
        assert lease.get_instance().status == "paused"
        mock_provider.pause_session.assert_called_once_with("inst-123")

    def test_resume_instance(self, store, mock_provider):
        """Test resuming instance."""
        lease = store.create("lease-1", "test-provider")

        # Create and pause instance
        mock_provider.create_session.return_value = SessionInfo(
            session_id="inst-123",
            provider="test-provider",
            status="running",
        )
        lease.ensure_active_instance(mock_provider)
        mock_provider.pause_session.return_value = True
        lease.pause_instance(mock_provider)

        # Resume
        mock_provider.resume_session.return_value = True
        result = lease.resume_instance(mock_provider)

        assert result is True
        assert lease.get_instance().status == "running"
        mock_provider.resume_session.assert_called_once_with("inst-123")

    def test_instance_persists_to_db(self, store, mock_provider, temp_db):
        """Test that instance state persists to database."""
        lease = store.create("lease-1", "test-provider")

        # Create instance
        mock_provider.create_session.return_value = SessionInfo(
            session_id="inst-123",
            provider="test-provider",
            status="running",
        )
        lease.ensure_active_instance(mock_provider)

        # Verify persisted to DB
        with sqlite3.connect(str(temp_db)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT current_instance_id, instance_status FROM sandbox_leases WHERE lease_id = ?",
                ("lease-1",),
            ).fetchone()

            assert row["current_instance_id"] == "inst-123"
            assert row["instance_status"] == "running"

    def test_instance_persists_across_retrieval(self, store, mock_provider):
        """Test that instance persists when lease is retrieved again."""
        lease = store.create("lease-1", "test-provider")

        # Create instance
        mock_provider.create_session.return_value = SessionInfo(
            session_id="inst-123",
            provider="test-provider",
            status="running",
        )
        lease.ensure_active_instance(mock_provider)

        # Retrieve lease again
        lease2 = store.get("lease-1")
        assert lease2 is not None
        instance = lease2.get_instance()
        assert instance is not None
        assert instance.instance_id == "inst-123"
        assert instance.status == "running"


class TestLeaseIntegration:
    """Integration tests for lease lifecycle."""

    def test_full_lifecycle(self, store, mock_provider):
        """Test complete lease lifecycle: create → instance → pause → resume → destroy."""
        # Create lease
        lease = store.create("lease-1", "test-provider")
        assert lease.get_instance() is None

        # Create instance
        mock_provider.create_session.return_value = SessionInfo(
            session_id="inst-123",
            provider="test-provider",
            status="running",
        )
        instance = lease.ensure_active_instance(mock_provider)
        assert instance.instance_id == "inst-123"

        # Pause
        mock_provider.pause_session.return_value = True
        lease.pause_instance(mock_provider)
        assert lease.get_instance().status == "paused"

        # Resume
        mock_provider.resume_session.return_value = True
        lease.resume_instance(mock_provider)
        assert lease.get_instance().status == "running"

        # Destroy
        lease.destroy_instance(mock_provider)
        assert lease.get_instance() is None

        # Delete lease
        store.delete("lease-1")
        assert store.get("lease-1") is None

    def test_multiple_leases_different_providers(self, store, mock_provider):
        """Test multiple leases with different providers."""
        lease1 = store.create("lease-1", "e2b")
        lease2 = store.create("lease-2", "agentbay")
        lease3 = store.create("lease-3", "e2b")

        assert lease1.provider_name == "e2b"
        assert lease2.provider_name == "agentbay"
        assert lease3.provider_name == "e2b"

        # Verify all created
        assert store.get("lease-1") is not None
        assert store.get("lease-2") is not None
        assert store.get("lease-3") is not None
