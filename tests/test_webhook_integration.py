import base64
import hashlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from sandbox.webhook_integration import WebhookIntegrationStore

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.web import main as web_main


def _e2b_signature(secret: str, payload: bytes) -> str:
    digest = hashlib.sha256((secret + payload.decode("utf-8")).encode("utf-8")).digest()
    return base64.b64encode(digest).decode("utf-8").rstrip("=")


def test_extract_webhook_instance_id_handles_camel_case():
    payload = {"type": "sandbox.lifecycle.updated", "sandboxId": "sbx-top-level"}
    assert web_main._extract_webhook_instance_id(payload) == "sbx-top-level"

    nested = {"type": "sandbox.lifecycle.updated", "eventData": {"sandboxId": "sbx-event-data"}}
    assert web_main._extract_webhook_instance_id(nested) == "sbx-event-data"


def test_infer_state_maps_killed_to_detached():
    payload = {"type": "sandbox.lifecycle.killed"}
    assert web_main._infer_observed_state_from_webhook(payload) == "detached"


def test_e2b_signature_verification_enforced_when_secret_exists(tmp_path, monkeypatch):
    db_path = tmp_path / "sandbox.db"
    monkeypatch.setattr(web_main, "SANDBOX_DB_PATH", db_path)
    store = WebhookIntegrationStore(db_path=db_path)
    store.upsert(
        provider_name="e2b",
        webhook_id="wh_1",
        callback_url="https://example.test/api/webhooks/e2b",
        signature_secret="x" * 32,
        status="active",
        metadata={"events": ["sandbox.lifecycle.updated"]},
    )

    body = b'{"type":"sandbox.lifecycle.updated","sandboxId":"sbx-1"}'
    with TestClient(web_main.app) as client:
        bad = client.post(
            "/api/webhooks/e2b",
            content=body,
            headers={"content-type": "application/json", "e2b-signature": "invalid"},
        )
        assert bad.status_code == 401

        good_sig = _e2b_signature("x" * 32, body)
        good = client.post(
            "/api/webhooks/e2b",
            content=body,
            headers={"content-type": "application/json", "e2b-signature": good_sig},
        )
        assert good.status_code == 200
        assert good.json()["matched"] is False
