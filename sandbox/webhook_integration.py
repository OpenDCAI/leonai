"""Provider webhook integration primitives.

Business boundary:
- This module only handles provider webhook control-plane calls and local integration records.
- Tunnel/bootstrap transport stays outside business logic.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import sqlite3
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sandbox.db import DEFAULT_DB_PATH


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _to_json(data: dict[str, Any] | None) -> str:
    return json.dumps(data or {})


def _from_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _now_iso() -> str:
    return datetime.now().isoformat()


@dataclass
class WebhookIntegrationRecord:
    provider_name: str
    webhook_id: str | None
    callback_url: str
    signature_secret: str | None
    status: str
    last_error: str | None
    metadata: dict[str, Any]
    created_at: str
    updated_at: str


class WebhookIntegrationStore:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._ensure_table()

    def _ensure_table(self) -> None:
        with _connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS webhook_integrations (
                    provider_name TEXT PRIMARY KEY,
                    webhook_id TEXT,
                    callback_url TEXT NOT NULL,
                    signature_secret TEXT,
                    status TEXT NOT NULL,
                    last_error TEXT,
                    metadata_json TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
                """
            )
            conn.commit()

    def upsert(
        self,
        *,
        provider_name: str,
        callback_url: str,
        webhook_id: str | None,
        signature_secret: str | None,
        status: str,
        last_error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now = _now_iso()
        with _connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO webhook_integrations (
                    provider_name, webhook_id, callback_url, signature_secret,
                    status, last_error, metadata_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider_name) DO UPDATE SET
                    webhook_id = excluded.webhook_id,
                    callback_url = excluded.callback_url,
                    signature_secret = excluded.signature_secret,
                    status = excluded.status,
                    last_error = excluded.last_error,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                (
                    provider_name,
                    webhook_id,
                    callback_url,
                    signature_secret,
                    status,
                    last_error,
                    _to_json(metadata),
                    now,
                    now,
                ),
            )
            conn.commit()

    def get(self, provider_name: str) -> WebhookIntegrationRecord | None:
        with _connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT provider_name, webhook_id, callback_url, signature_secret,
                       status, last_error, metadata_json, created_at, updated_at
                FROM webhook_integrations
                WHERE provider_name = ?
                LIMIT 1
                """,
                (provider_name,),
            ).fetchone()
            if not row:
                return None
            return WebhookIntegrationRecord(
                provider_name=row["provider_name"],
                webhook_id=row["webhook_id"],
                callback_url=row["callback_url"],
                signature_secret=row["signature_secret"],
                status=row["status"],
                last_error=row["last_error"],
                metadata=_from_json(row["metadata_json"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def list_all(self) -> list[WebhookIntegrationRecord]:
        with _connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT provider_name, webhook_id, callback_url, signature_secret,
                       status, last_error, metadata_json, created_at, updated_at
                FROM webhook_integrations
                ORDER BY provider_name ASC
                """
            ).fetchall()
            return [
                WebhookIntegrationRecord(
                    provider_name=row["provider_name"],
                    webhook_id=row["webhook_id"],
                    callback_url=row["callback_url"],
                    signature_secret=row["signature_secret"],
                    status=row["status"],
                    last_error=row["last_error"],
                    metadata=_from_json(row["metadata_json"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    def delete(self, provider_name: str) -> None:
        with _connect(self.db_path) as conn:
            conn.execute("DELETE FROM webhook_integrations WHERE provider_name = ?", (provider_name,))
            conn.commit()


def generate_e2b_signature_secret() -> str:
    # E2B requires >=32 chars.
    return secrets.token_hex(24)


def verify_e2b_signature(secret: str, payload: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    expected = hashlib.sha256((secret + payload.decode("utf-8")).encode("utf-8")).digest()
    expected_b64 = base64.b64encode(expected).decode("utf-8").rstrip("=")
    provided = signature.strip()
    return secrets.compare_digest(expected_b64, provided)


class E2BWebhookClient:
    BASE_URL = "https://api.e2b.app"

    def __init__(self, api_key: str):
        if not api_key:
            raise RuntimeError("E2B API key is required for webhook integration")
        self.api_key = api_key

    def _request(
        self,
        *,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            f"{self.BASE_URL}{path}",
            data=data,
            method=method,
            headers={
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return {}
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, (dict, list)) else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"E2B webhook API {method} {path} failed: {exc.code} {detail}") from exc
        except Exception as exc:
            raise RuntimeError(f"E2B webhook API {method} {path} failed: {exc}") from exc

    def list_webhooks(self) -> list[dict[str, Any]]:
        data = self._request(method="GET", path="/events/webhooks")
        if not isinstance(data, list):
            raise RuntimeError("E2B webhook list response is not a list")
        return [row for row in data if isinstance(row, dict)]

    def create_webhook(
        self,
        *,
        name: str,
        url: str,
        events: list[str],
        signature_secret: str,
        enabled: bool,
    ) -> dict[str, Any]:
        data = self._request(
            method="POST",
            path="/events/webhooks",
            body={
                "name": name,
                "url": url,
                "enabled": enabled,
                "events": events,
                "signatureSecret": signature_secret,
            },
        )
        if not isinstance(data, dict):
            raise RuntimeError("E2B webhook create response is not an object")
        return data

    def update_webhook(
        self,
        *,
        webhook_id: str,
        url: str,
        events: list[str],
        enabled: bool,
    ) -> dict[str, Any]:
        data = self._request(
            method="PATCH",
            path=f"/events/webhooks/{webhook_id}",
            body={
                "url": url,
                "enabled": enabled,
                "events": events,
            },
        )
        if not isinstance(data, dict):
            raise RuntimeError("E2B webhook update response is not an object")
        return data

    def delete_webhook(self, webhook_id: str) -> None:
        _ = self._request(method="DELETE", path=f"/events/webhooks/{webhook_id}")

    def ensure_webhook(
        self,
        *,
        name: str,
        url: str,
        events: list[str],
        signature_secret: str,
        enabled: bool = True,
    ) -> dict[str, Any]:
        existing = next((w for w in self.list_webhooks() if w.get("name") == name), None)
        if not existing:
            created = self.create_webhook(
                name=name,
                url=url,
                events=events,
                signature_secret=signature_secret,
                enabled=enabled,
            )
            return {"action": "created", "webhook": created}

        webhook_id = str(existing.get("id") or "")
        if not webhook_id:
            raise RuntimeError("E2B existing webhook missing id")

        same_url = str(existing.get("url") or "") == url
        same_enabled = bool(existing.get("enabled")) == bool(enabled)
        same_events = sorted(str(x) for x in (existing.get("events") or [])) == sorted(events)
        if same_url and same_enabled and same_events:
            return {"action": "noop", "webhook": existing}

        updated = self.update_webhook(
            webhook_id=webhook_id,
            url=url,
            events=events,
            enabled=enabled,
        )
        return {"action": "updated", "webhook": updated}


class DaytonaWebhookClient:
    def __init__(self, *, api_key: str, api_url: str):
        if not api_key:
            raise RuntimeError("Daytona API key is required for webhook integration")
        from daytona_api_client import ApiClient, Configuration
        from daytona_api_client.api.webhooks_api import WebhooksApi

        conf = Configuration(host=api_url)
        client = ApiClient(conf)
        client.default_headers["Authorization"] = f"Bearer {api_key}"
        client.default_headers["X-Daytona-Source"] = "leon-webhook-integration"
        self._webhooks = WebhooksApi(client)

    @staticmethod
    def _obj_to_dict(obj: Any) -> dict[str, Any]:
        if obj is None:
            return {}
        for attr in ("to_dict", "model_dump"):
            if hasattr(obj, attr):
                try:
                    data = getattr(obj, attr)()
                except Exception:
                    continue
                if isinstance(data, dict):
                    return data
        if isinstance(obj, dict):
            return obj
        return {"repr": repr(obj)}

    def get_status(self) -> dict[str, Any]:
        try:
            data = self._webhooks.webhook_controller_get_status()
        except Exception as exc:
            raise RuntimeError(f"Daytona webhook status failed: {exc}") from exc
        return self._obj_to_dict(data)

    def initialize(self, organization_id: str) -> None:
        if not organization_id:
            raise RuntimeError("organization_id is required for Daytona webhook initialization")
        try:
            self._webhooks.webhook_controller_initialize_webhooks(organization_id=organization_id)
        except Exception as exc:
            raise RuntimeError(f"Daytona webhook initialize failed: {exc}") from exc

    def get_initialization_status(self, organization_id: str) -> dict[str, Any]:
        if not organization_id:
            raise RuntimeError("organization_id is required")
        try:
            data = self._webhooks.webhook_controller_get_initialization_status(organization_id=organization_id)
        except Exception as exc:
            raise RuntimeError(f"Daytona webhook initialization status failed: {exc}") from exc
        return self._obj_to_dict(data)

    def get_app_portal_access(self, organization_id: str) -> dict[str, Any]:
        if not organization_id:
            raise RuntimeError("organization_id is required")
        try:
            data = self._webhooks.webhook_controller_get_app_portal_access(organization_id=organization_id)
        except Exception as exc:
            raise RuntimeError(f"Daytona webhook app portal access failed: {exc}") from exc
        return self._obj_to_dict(data)

    def send_test_event(self, *, organization_id: str, event_type: str, payload: dict[str, Any]) -> None:
        if not organization_id:
            raise RuntimeError("organization_id is required")
        from daytona_api_client.models.send_webhook_dto import SendWebhookDto

        dto = SendWebhookDto(event_type=event_type, payload=payload or {})
        try:
            self._webhooks.webhook_controller_send_webhook(organization_id=organization_id, send_webhook_dto=dto)
        except Exception as exc:
            raise RuntimeError(f"Daytona webhook send test failed: {exc}") from exc
