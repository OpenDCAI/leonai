"""Tests for provider webhook -> lease state convergence."""

from datetime import datetime
from pathlib import Path
import tempfile
import uuid

from sandbox.lease import LeaseStore
from sandbox.provider import Metrics, ProviderExecResult, SandboxProvider, SessionInfo
from sandbox.webhook import parse_provider_webhook


class FakeProvider(SandboxProvider):
    name = "fake"

    def __init__(self):
        self._statuses: dict[str, str] = {}

    def create_session(self, context_id: str | None = None) -> SessionInfo:
        sid = f"s-{uuid.uuid4().hex[:8]}"
        self._statuses[sid] = "running"
        return SessionInfo(session_id=sid, provider=self.name, status="running")

    def destroy_session(self, session_id: str, sync: bool = True) -> bool:
        self._statuses.pop(session_id, None)
        return True

    def pause_session(self, session_id: str) -> bool:
        if session_id in self._statuses:
            self._statuses[session_id] = "paused"
            return True
        return False

    def resume_session(self, session_id: str) -> bool:
        if session_id in self._statuses:
            self._statuses[session_id] = "running"
            return True
        return False

    def get_session_status(self, session_id: str) -> str:
        return self._statuses.get(session_id, "deleted")

    def execute(
        self,
        session_id: str,
        command: str,
        timeout_ms: int = 30000,
        cwd: str | None = None,
    ) -> ProviderExecResult:
        return ProviderExecResult(output="", exit_code=0, error=None)

    def read_file(self, session_id: str, path: str) -> str:
        return ""

    def write_file(self, session_id: str, path: str, content: str) -> str:
        return "ok"

    def list_dir(self, session_id: str, path: str) -> list[dict]:
        return []

    def get_metrics(self, session_id: str) -> Metrics | None:
        return None

    def list_provider_sessions(self) -> list[SessionInfo]:
        return [
            SessionInfo(session_id=sid, provider=self.name, status=status) for sid, status in self._statuses.items()
        ]


def _temp_db() -> Path:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return Path(f.name)


def test_parse_e2b_webhook_paused() -> None:
    obs = parse_provider_webhook(
        "e2b",
        {
            "type": "sandbox.lifecycle.paused",
            "sandboxId": "sbx-123",
            "timestamp": "2026-02-09T12:00:00Z",
        },
    )
    assert obs.provider_name == "e2b"
    assert obs.provider_instance_id == "sbx-123"
    assert obs.status == "paused"
    assert obs.observed_at is not None


def test_parse_daytona_webhook_state_updated() -> None:
    obs = parse_provider_webhook(
        "daytona",
        {
            "event": "sandbox.state.updated",
            "timestamp": "2026-02-09T12:00:00Z",
            "data": {"sandboxId": "dt-1", "state": "running"},
        },
    )
    assert obs.provider_name == "daytona"
    assert obs.provider_instance_id == "dt-1"
    assert obs.status == "running"


def test_apply_provider_observation_updates_lease() -> None:
    db = _temp_db()
    try:
        provider = FakeProvider()
        store = LeaseStore(db_path=db)
        lease = store.create("lease-1", "e2b")
        instance = lease.ensure_active_instance(provider)

        updated = store.apply_provider_observation(
            provider_name="e2b",
            provider_instance_id=instance.instance_id,
            status="paused",
            observed_at=datetime.now(),
        )
        assert updated

        refreshed = store.get("lease-1")
        assert refreshed is not None
        assert refreshed.get_instance() is not None
        assert refreshed.get_instance().status == "paused"

        updated_detach = store.apply_provider_observation(
            provider_name="e2b",
            provider_instance_id=instance.instance_id,
            status="detached",
            observed_at=datetime.now(),
        )
        assert updated_detach
        detached = store.get("lease-1")
        assert detached is not None
        assert detached.get_instance() is None
    finally:
        db.unlink(missing_ok=True)


def test_apply_provider_observation_returns_false_for_unknown_instance() -> None:
    db = _temp_db()
    try:
        store = LeaseStore(db_path=db)
        store.create("lease-1", "e2b")
        updated = store.apply_provider_observation(
            provider_name="e2b",
            provider_instance_id="no-such-instance",
            status="running",
        )
        assert updated is False
    finally:
        db.unlink(missing_ok=True)
