import sys
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from sandbox.lease import LeaseStore
from sandbox.provider import SessionInfo
from sandbox.provider_events import ProviderEventStore

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.web import main as web_main


def _seed_lease_with_instance(db_path: Path, provider_name: str, instance_id: str) -> None:
    store = LeaseStore(db_path=db_path)
    lease = store.create("lease-1", provider_name)

    provider = MagicMock()
    provider.create_session.return_value = SessionInfo(
        session_id=instance_id,
        provider=provider_name,
        status="running",
    )
    lease.ensure_active_instance(provider)


def test_webhook_marks_lease_needs_refresh(tmp_path, monkeypatch):
    db_path = tmp_path / "sandbox.db"
    monkeypatch.setattr(web_main, "SANDBOX_DB_PATH", db_path)
    _seed_lease_with_instance(db_path, "e2b", "inst-123")

    with TestClient(web_main.app) as client:
        resp = client.post("/api/webhooks/e2b", json={"session_id": "inst-123", "event": "pause"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["matched"] is True
        assert body["lease_id"] == "lease-1"

    reloaded = LeaseStore(db_path=db_path).get("lease-1")
    assert reloaded is not None
    assert reloaded.needs_refresh is True
    assert reloaded.refresh_hint_at is not None

    events = ProviderEventStore(db_path=db_path).list_recent(limit=10)
    assert len(events) == 1
    assert events[0]["provider_name"] == "e2b"
    assert events[0]["instance_id"] == "inst-123"
    assert events[0]["matched_lease_id"] == "lease-1"
    assert events[0]["event_type"] == "pause"


def test_webhook_unknown_instance_returns_matched_false(tmp_path, monkeypatch):
    db_path = tmp_path / "sandbox.db"
    monkeypatch.setattr(web_main, "SANDBOX_DB_PATH", db_path)
    LeaseStore(db_path=db_path)

    with TestClient(web_main.app) as client:
        resp = client.post("/api/webhooks/e2b", json={"session_id": "inst-404"})
        assert resp.status_code == 200
        assert resp.json()["matched"] is False

    events = ProviderEventStore(db_path=db_path).list_recent(limit=10)
    assert len(events) == 1
    assert events[0]["instance_id"] == "inst-404"
    assert events[0]["matched_lease_id"] is None
    assert events[0]["event_type"] == "unknown"


def test_webhook_missing_instance_id_returns_400(tmp_path, monkeypatch):
    db_path = tmp_path / "sandbox.db"
    monkeypatch.setattr(web_main, "SANDBOX_DB_PATH", db_path)
    LeaseStore(db_path=db_path)

    with TestClient(web_main.app) as client:
        resp = client.post("/api/webhooks/daytona", json={"event": "sandbox.lifecycle.paused"})
        assert resp.status_code == 400
        assert "missing instance/session id" in resp.json()["detail"].lower()


def test_webhook_events_endpoint_lists_recent(tmp_path, monkeypatch):
    db_path = tmp_path / "sandbox.db"
    monkeypatch.setattr(web_main, "SANDBOX_DB_PATH", db_path)
    _seed_lease_with_instance(db_path, "daytona", "inst-abc")

    with TestClient(web_main.app) as client:
        r1 = client.post(
            "/api/webhooks/daytona", json={"data": {"id": "inst-abc"}, "event": "sandbox.lifecycle.paused"}
        )
        assert r1.status_code == 200

        r2 = client.get("/api/webhooks/events?limit=5")
        assert r2.status_code == 200
        body = r2.json()
        assert body["count"] >= 1
        assert isinstance(body["items"], list)
        assert body["items"][0]["provider_name"] == "daytona"
